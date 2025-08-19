# pages/修繕積立金_収益性.py
# 目的：
# 1) 「現状の修繕積立金」を『円/㎡・月』を主入力に、任意で『全体（月額・円）』も受け付ける
# 2) 国交省ガイドライン（R6.6.7改定）の平均＆幅と比較し、判定（不足/概ね妥当/過剰）＋乖離率を表示
# 3) 機械式駐車場の加算（台当たり月額×台数÷総専有㎡）をベンチマークへ上乗せ（国交省式）
# 4) EV比率/機械式駐車場比率/高層/小規模の高コスト要因を自動説明
# 5) 35年総支出Aから必要月額（全体/㎡）と不足額を提示
# 6) 初期値は全て0（空欄扱い）。0が混在すれば「未入力」で計算停止
# 7) テーブルは「万円」単位の横持ち（整数・カンマ付き）

import math
import datetime as dt
import pandas as pd
import streamlit as st

# =====================
# 内部固定パラメータ
# =====================
INFL = 0.03         # インフレ年3%（複利）
TAX = 0.10          # 消費税10%
OH = 0.10           # 諸経費（工事費小計の10%）
PRIVATE_RATIO_BUILDING = 0.75  # 延床→総専有の代表比率（推計）
FACADE_COEF = 1.25             # 外壁係数
STEEL_RATIO = 0.10             # 鉄部塗装面積 ≒ 外壁の10%

def floor_factor_by_floors(f:int)->float:
    if f <= 5:   return 1.00
    if f <= 10:  return 1.10
    if f <= 20:  return 1.25
    return 1.40

# 工事項目（カテゴリ, 名称, 周期(年), 単価タイプ, 単価（円/単位））
# 単価タイプ：'sqm'（㎡単価×推定面積）/'lump'（一式）/'per_unit'（戸数×単価）/'ev'（EV台数×単価）
ITEMS = [
    ("建築", "外壁塗装・タイル補修・シーリング", 12, "sqm",    6_000),
    ("建築", "屋上・バルコニー・庇 防水改修",   12, "sqm",    2_800),
    ("建築", "鉄部塗装（手すり・階段・フェンス等）", 12, "sqm", 1_000),
    ("設備", "給水設備（ポンプ・受水槽等）更新", 12, "sqm",    1_200),
    ("設備", "給排水管 更生/更新（㎡按分）",      24, "sqm",    4_400),
    ("設備", "分電盤・配電盤・受変電設備 更新",    24, "sqm",    1_500),
    ("設備", "インターホン更新（モニター化）",     20, "per_unit", 70_000),
    ("設備", "エレベーター更新（本体）",          25, "ev",   20_000_000),
    ("設備", "外構・舗装・植栽 等",               12, "sqm",      800),
    ("足場仮設", "足場仮設（共通）",              12, "sqm",    2_000),
]

# ==========
# ユーティリティ
# ==========
def fmt_man(n_yen: float) -> str:
    man = int(round(n_yen / 10_000))
    return f"{man:,}"

def inflated(base_yen: float, years_from_start: int) -> float:
    return base_yen * ((1.0 + INFL) ** max(0, years_from_start))

def schedule_years(built_year:int, cycle:int, start_year:int, end_year:int):
    years = []
    y = built_year + cycle
    while y <= end_year + cycle*2:
        if start_year <= y <= end_year:
            years.append(y)
        y += cycle
    return years

def any_zero_required(vals) -> bool:
    for v in vals:
        try:
            if v is None or int(v) == 0:
                return True
        except:
            return True
    return False

# 国交省ガイドライン（R6.6.7改定） ㎡単価の目安（機械式除く）
def mlit_benchmark(floors:int, total_floor_area:float):
    if floors >= 20:
        return {"avg": 338, "low": 240, "high": 410, "label": "20階以上"}
    if total_floor_area < 5_000:
        return {"avg": 335, "low": 235, "high": 430, "label": "20階未満・延床<5,000㎡"}
    if total_floor_area < 10_000:
        return {"avg": 252, "low": 170, "high": 320, "label": "20階未満・延床5,000〜10,000㎡"}
    if total_floor_area < 20_000:
        return {"avg": 271, "low": 200, "high": 330, "label": "20階未満・延床10,000〜20,000㎡"}
    return {"avg": 255, "low": 190, "high": 325, "label": "20階未満・延床20,000㎡以上"}

# 機械式駐車場：国交省の台当たり月額（円/台・月）
MECH_PARK_UNIT_YEN = {
    "2段（ピット1段）昇降式":      6450,
    "2段（ピット2段）昇降式":      5840,
    "3段（ピット1段）昇降横行式":  7210,
    "4段（ピット2段）昇降横行式":  6235,
    "エレベーター式・垂直循環式":   4645,
    "その他":                       5235,
}

def mech_add_psqm(unit_type:str, slots:int, total_private_area:float) -> int:
    """機械式の加算：円/㎡・月（＝台当たり月額×台数÷総専有㎡）を整数化"""
    if total_private_area <= 0 or slots <= 0:
        return 0
    per = MECH_PARK_UNIT_YEN.get(unit_type, 0)
    return int(round(per * slots / total_private_area))

def area_for_item(cat:str, name:str, per_floor_area:float, facade_area_est:float,
                  roof_area_est:float, steel_area_est:float, floor_factor:float,
                  total_floor_area:float) -> float:
    if "外壁塗装" in name:               return facade_area_est * floor_factor
    if "防水" in name:                   return roof_area_est * floor_factor
    if "鉄部塗装" in name:               return steel_area_est * floor_factor
    if "外構・舗装・植栽" in name:        return per_floor_area * 0.5
    if cat == "足場仮設":                 return facade_area_est * floor_factor
    return total_floor_area  # 設備系は㎡按分

# ==========
# 画面
# ==========
st.set_page_config(page_title="修繕積立｜妥当性（㎡単価比較＋理由）", layout="wide")
st.title("修繕積立｜妥当性と将来不足の即時判定（単位：万円）")

with st.sidebar:
    st.header("入力（未入力=0）")
    # 現状：主入力は円/㎡・月。全体月額は任意（補完用）
    current_psqm_input   = st.number_input("現状の修繕積立金（円/㎡・月）", min_value=0, step=10, value=0)
    current_monthly_total= st.number_input("現状の修繕積立金（月額・全体・円）※任意", min_value=0, step=1000, value=0)

    # 建物条件（必須）
    total_floor_area  = st.number_input("延べ床面積（㎡）", min_value=0, step=10, value=0)
    built_year        = st.number_input("築年（西暦）", min_value=0, max_value=9999, step=1, value=0)
    units             = st.number_input("戸数（戸）", min_value=0, step=1, value=0)
    floors            = st.number_input("階数（階）", min_value=0, step=1, value=0)
    ev_count          = st.number_input("EV台数（基）", min_value=0, step=1, value=0)

    # 機械式駐車場（妥当性の加算＆理由に使用）
    mech_park_slots   = st.number_input("機械式駐車場の区画数（基）", min_value=0, step=1, value=0)
    mech_park_type    = st.selectbox("機械式駐車場の形式", list(MECH_PARK_UNIT_YEN.keys()), index=0)

    # 参考（個別住戸）※不要時は0でOK
    my_private_area   = st.number_input("あなたの専有面積（㎡）", min_value=0, step=1, value=0)

# 年レンジ
start_year = dt.date.today().year
horizon    = 35
end_year   = start_year + horizon - 1
years      = list(range(start_year, end_year + 1))

# 必須チェック（工事テーブル）
if any_zero_required([total_floor_area, built_year, units, floors]):
    st.info("【入力不足】『延べ床面積』『築年』『戸数』『階数』は必須です。0の項目を埋めてください。")
    st.stop()

# 総専有面積（推計）
total_private_area = total_floor_area * PRIVATE_RATIO_BUILDING

# 現状の円/㎡・月（主入力優先 → 全体月額から算出 → 未入力）
if current_psqm_input > 0:
    current_psqm = int(current_psqm_input)
elif current_monthly_total > 0 and total_private_area > 0:
    current_psqm = int(round(current_monthly_total / total_private_area))
else:
    current_psqm = 0

# 全体月額（補完）
if current_monthly_total > 0:
    monthly_total_now = int(current_monthly_total)
elif current_psqm > 0 and total_private_area > 0:
    monthly_total_now = int(current_psqm * total_private_area)
else:
    monthly_total_now = 0

# 妥当性判定に最低限必要：current_psqm または monthly_total_now
if current_psqm == 0 and monthly_total_now == 0:
    st.info("【入力不足】『現状の修繕積立金（円/㎡・月 もしくは 全体月額）』のいずれかを入力してください。")
    st.stop()

# 面積推定
per_floor_area   = total_floor_area / max(1, floors)
facade_area_est  = per_floor_area * FACADE_COEF
roof_area_est    = per_floor_area
steel_area_est   = facade_area_est * STEEL_RATIO
floor_factor     = floor_factor_by_floors(int(floors))

# ==========================
# 年別コスト（万円）テーブル生成
# ==========================
row_index = []
data = {y: [] for y in years}

for cat, name, cycle, utype, unit_cost in ITEMS:
    row_index.append((cat, name, f"{cycle}年"))
    scheduled = set(schedule_years(int(built_year), int(cycle), start_year, end_year))
    for y in years:
        if y in scheduled:
            t = y - start_year
            if utype == "sqm":
                base_area = area_for_item(cat, name, per_floor_area, facade_area_est, roof_area_est,
                                          steel_area_est, floor_factor, total_floor_area)
                base = unit_cost * base_area
            elif utype == "per_unit":
                base = unit_cost * units
            elif utype == "ev":
                base = unit_cost * ev_count
            else:
                base = unit_cost
            amt = inflated(base, t)                     # 円
            data[y].append(fmt_man(amt))               # 万円（文字列）
        else:
            data[y].append("")

# 工事費小計
row_index.append(("支出集計", "工事費小計", ""))
for y in years:
    subtotal_yen = 0
    for i, (cat,name,cyc) in enumerate(row_index[:-1]):
        val = data[y][i]
        if val != "":
            subtotal_yen += int(val.replace(",","")) * 10_000
    data[y].append(fmt_man(subtotal_yen))

# 諸経費／消費税／A.支出合計
for label, kind in [("諸経費（10%）","oh"), ("消費税（10%）","tax"), ("A.支出合計","sum")]:
    row_index.append(("支出集計", label, ""))
    for y in years:
        subtotal_yen = int(data[y][-1].replace(",","")) * 10_000
        if kind=="oh":
            v = subtotal_yen * OH
        elif kind=="tax":
            v = (subtotal_yen + subtotal_yen*OH) * TAX
        else:
            v = subtotal_yen + subtotal_yen*OH + (subtotal_yen + subtotal_yen*OH)*TAX
        data[y].append(fmt_man(v))

# 収入・残高（現行のまま徴収した場合）
row_index.append(("収入・残高", "期首繰越", ""))
row_index.append(("収入・残高", "修繕積立金収入（年額）", ""))
row_index.append(("収入・残高", "当期収入合計", ""))
row_index.append(("収入・残高", "当期収支（収入合計－A）", ""))
row_index.append(("収入・残高", "期末残高（次期繰越）", ""))

for y_idx, y in enumerate(years):
    beg_yen = 0 if y_idx == 0 else int(data[years[y_idx-1]][-1].replace(",","")) * 10_000
    income_yen = monthly_total_now * 12
    income_total_yen = beg_yen + income_yen
    a_yen = int(data[y][-3].replace(",","")) * 10_000  # A.支出合計は末尾から3番目
    net_yen = income_total_yen - a_yen
    end_yen = net_yen
    data[y].extend([
        fmt_man(beg_yen),
        fmt_man(income_yen),
        fmt_man(income_total_yen),
        fmt_man(net_yen),
        fmt_man(end_yen),
    ])

# ==========================
# 必要月額（均等）と妥当性判定
# ==========================
# 35年の総支出A（円）
total_A_yen = 0
for y in years:
    total_A_yen += int(data[y][-3].replace(",","")) * 10_000

# 必要月額（全体・円）＝ 総支出 ÷ (35年×12)
required_monthly_yen = math.ceil(total_A_yen / (horizon * 12))
shortfall_yen = max(0, required_monthly_yen - monthly_total_now)

# 必要な円/㎡・月
required_psqm = int(round(required_monthly_yen / total_private_area)) if total_private_area > 0 else 0

# ガイドライン（機械式除くベース）
g = mlit_benchmark(int(floors), float(total_floor_area))
low_base, avg_base, high_base = g["low"], g["avg"], g["high"]

# 機械式駐車場の加算（国交省式）→ ベンチマークへ上乗せ
mech_add = mech_add_psqm(mech_park_type, int(mech_park_slots), float(total_private_area))
low, avg, high = low_base + mech_add, avg_base + mech_add, high_base + mech_add

def judge(psqm:int, low:int, high:int):
    if psqm == 0:
        return "未入力"
    if psqm < low:
        return "不足（低すぎ）"
    if psqm > high:
        return "過剰（高すぎ）"
    return "概ね妥当（幅内）"

def pct_diff(a:int, b:int):
    if b == 0: return None
    return (a - b) / b * 100.0

judge_now = judge(current_psqm, low, high)
judge_req = judge(required_psqm, low, high)
diff_now_vs_avg = pct_diff(current_psqm, avg)
diff_req_vs_avg = pct_diff(required_psqm, avg)

# 背景要因（ヒューリスティック）
reasons = []
# EV
ev_ratio = (ev_count / units) if units else 0.0
if ev_ratio >= 0.03:
    reasons.append("EV比率が高め（EV台数/戸数 ≥ 3%）→ 更新・保守コスト増の要因")
elif ev_ratio >= 0.02:
    reasons.append("EV比率がやや高い（2〜3%）→ 支出増の要因")

# 機械式駐車場
mech_ratio = (mech_park_slots / units) if units else 0.0
if mech_park_slots > 0:
    reasons.append(f"機械式駐車場あり（形式：{mech_park_type}、区画：{int(mech_park_slots)}）→ 修繕費が上振れ（加算 {mech_add:,} 円/㎡・月）")
elif mech_ratio >= 0.25:
    reasons.append("機械式駐車場の比率が高い（0.25〜0.5）→ 維持更新費が増加")

# 高層・仮設負担
if floors >= 15:
    reasons.append("高層（15階以上）→ 足場・外装工事の仮設費が相対的に高い")

# 規模効果（小規模は割高になりやすい）
if total_floor_area < 5_000 and floors < 20:
    reasons.append("延床<5,000㎡かつ中低層→ 規模効果が効きづらく単価が上がりやすい")

# ===== 結論ブロック =====
st.subheader("結論（妥当性・理由・必要水準）")

if total_private_area <= 0:
    st.warning("総専有面積（延床×0.75）の推計が0です。延べ床面積を入力してください。")
else:
    col1, col2, col3 = st.columns([1.05,1.05,1.3])
    with col1:
        st.markdown("**現状の負担（推計）**")
        st.metric("現状：円/㎡・月", f"{current_psqm:,}" if current_psqm else "—")
        st.metric("現状の評価", judge_now)

    with col2:
        label = f"{g['label']}（機械式加算{'あり' if mech_add>0 else 'なし'}）"
        st.markdown(f"**国交省ガイドライン：{label}**")
        st.metric("平均（円/㎡・月）", f"{avg:,}")
        st.caption(f"幅：{low:,}〜{high:,} 円/㎡・月")
        if diff_now_vs_avg is not None:
            st.caption(f"現状は平均比：{diff_now_vs_avg:+.0f}%")

    with col3:
        st.markdown("**将来を踏まえた必要水準（均等積立）**")
        st.metric("必要：円/㎡・月", f"{required_psqm:,}" if required_psqm else "—")
        st.metric("必要：月額（全体・円）", f"{required_monthly_yen:,}")
        if diff_req_vs_avg is not None:
            st.caption(f"必要水準は平均比：{diff_req_vs_avg:+.0f}%")
        if monthly_total_now > 0:
            st.caption(f"不足（月額・全体）：{shortfall_yen:,} 円")

# 背景要因
st.markdown("**背景要因（参考）**")
if reasons:
    st.markdown("- " + "\n- ".join(reasons))
else:
    st.caption("特筆すべきコスト増要因は検出されていません。")

# ==========================
# 表示テーブル（万円）
# ==========================
idx = pd.MultiIndex.from_tuples(row_index, names=["工事区分","工事項目","周期（目安）"])
df = pd.DataFrame({y: data[y] for y in years}, index=idx)

st.subheader(f"長期修繕 横テーブル（{start_year}〜{end_year}／{len(years)}年、単位：万円）")
st.dataframe(df, use_container_width=True)

st.caption(
    "※ すべて概算。単価・周期・インフレ率3%は内部固定。外壁・屋上・鉄部の面積は延床と階数から推定。"
    " ガイドラインの数値と機械式駐車場の加算式は国土交通省（R6.6.7改定）に基づき実装。"
)