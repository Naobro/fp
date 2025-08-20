# pages/修繕積立金_収益性.py
# 結論ファースト：①現在の㎡単価と国交省基準・将来値上げ予想 ②収益性（周辺家賃×専有×12 ÷ 購入価格）
# その下に（仮）長期修繕計画（35年・万円横テーブル）
#
# デフォルト（指示どおり）
# ・住戸月額 15,000 円、専有 70㎡ → 現状 214 円/㎡・月（psqm直入力が0なら自動計算）
# ・延べ床 8,000㎡、戸数 100、築年 2000、階数 10、EV 1、機械式 0
# ・周辺家賃（㎡単価） 4,000 円/㎡・月
# ・購入価格 7,000 万円（万円入力）
#
# ルール：整数表示（円/万円/％）。％は四捨五入の整数。

import math
import datetime as dt
import pandas as pd
import streamlit as st

# =====================
# 内部固定パラメータ
# =====================
INFL = 0.03         # 長期表のインフレ年3%（複利）
TAX = 0.10          # 消費税10%
OH = 0.10           # 諸経費（工事費小計の10%）
PRIVATE_RATIO_BUILDING = 0.75  # 延床→総専有（代表値）
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
    """円→万円（整数）"""
    man = int(round(n_yen / 10_000))
    return f"{man:,}"

def int_fmt(n) -> str:
    try:
        return f"{int(n):,}"
    except:
        return "0"

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
    """機械式の加算：円/㎡・月（＝台当たり月額×台数÷総専有㎡）"""
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

def predict_next_major_year(built_year:int, cycle:int=12)->int:
    """築年から12年周期の『次回年』を自動推定（直近未来年）"""
    if built_year <= 0:
        return 0
    today = dt.date.today().year
    y = built_year
    while y <= today:
        y += cycle
    return y

# ==========
# 画面
# ==========
st.set_page_config(page_title="修繕積立｜結論ファースト＋収益性＋（仮）長期計画", layout="wide")
st.title("修繕積立｜妥当性・将来逆算・収益性（＋長期計画）")

with st.sidebar:
    st.header("入力（整数・デフォルト込み）")

    # 現状の積立：psqmを主入力。0なら「住戸月額÷専有」で自動計算。
    my_monthly_now   = st.number_input("あなたの修繕積立金（月額・円）", min_value=0, value=15000, step=1000)
    my_private_area  = st.number_input("専有面積（㎡）", min_value=0, value=70, step=1)
    current_psqm_in  = st.number_input("現状の修繕積立金（円/㎡・月）※未入力=0で自動計算", min_value=0, value=0, step=1)

    # 建物条件
    total_floor_area = st.number_input("延べ床面積（㎡）", min_value=0, value=8000, step=100)
    units            = st.number_input("戸数（戸）", min_value=0, value=100, step=1)
    built_year       = st.number_input("築年（西暦）", min_value=0, max_value=9999, value=2000, step=1)
    floors           = st.number_input("階数（階）", min_value=0, value=10, step=1)
    ev_count         = st.number_input("EV台数（基）", min_value=0, value=1, step=1)
    mech_park_slots  = st.number_input("機械式駐車場の区画数（基）", min_value=0, value=0, step=1)
    mech_park_type   = st.selectbox("機械式駐車場の形式", list(MECH_PARK_UNIT_YEN.keys()), index=0)

    # 収益性（周辺家賃・購入価格）
    rent_psqm        = st.number_input("周辺家賃相場（円/㎡・月）", min_value=0, value=4000, step=1000)
    price_million    = st.number_input("購入価格（万円）", min_value=0, value=7000, step=100)

    st.divider()
    # 次回大規模修繕（逆算）：年は築年から自動推定を初期値に
    next_year_default = predict_next_major_year(int(built_year), 12)
    next_major_year   = st.number_input("次回大規模修繕の年（YYYY）", min_value=0, value=next_year_default, step=1)
    base_cost_today   = st.number_input("（任意）今日の必要費（円）※未入力=0は自動推計", min_value=0, value=0, step=100000)
    infl_rate_pct     = st.number_input("（任意）インフレ率（年％・整数）", min_value=0, value=0, step=1)
    current_balance   = st.number_input("（任意）現在の修繕積立金 残高（全体・円）", min_value=0, value=0, step=100000)

# 年レンジ（長期表）
start_year = dt.date.today().year
horizon    = 35
end_year   = start_year + horizon - 1
years      = list(range(start_year, end_year + 1))

# 総専有面積（推計）
total_private_area = int(total_floor_area * PRIVATE_RATIO_BUILDING) if total_floor_area else 0

# 現状の円/㎡・月
if current_psqm_in > 0:
    current_psqm = int(current_psqm_in)
elif my_private_area > 0:
    current_psqm = int(round(my_monthly_now / my_private_area)) if my_monthly_now > 0 else 0
else:
    current_psqm = 0

# 全体月額（参考）
monthly_total_now = int(current_psqm * total_private_area) if (current_psqm > 0 and total_private_area > 0) else 0

# ================
# （仮）長期修繕テーブル（万円）
# ================
per_floor_area   = total_floor_area / max(1, floors) if floors else 0
facade_area_est  = per_floor_area * FACADE_COEF
roof_area_est    = per_floor_area
steel_area_est   = facade_area_est * STEEL_RATIO
floor_factor     = floor_factor_by_floors(int(floors)) if floors else 1.0

def area_for(cat, name):
    return area_for_item(cat, name, per_floor_area, facade_area_est, roof_area_est,
                         steel_area_est, floor_factor, total_floor_area)

row_index = []
data = {y: [] for y in years}

for cat, name, cycle, utype, unit_cost in ITEMS:
    row_index.append((cat, name, f"{cycle}年"))
    scheduled = set(schedule_years(int(built_year), int(cycle), start_year, end_year)) if built_year else set()
    for y in years:
        if y in scheduled and total_floor_area > 0:
            t = y - start_year
            if utype == "sqm":
                base = unit_cost * area_for(cat, name)
            elif utype == "per_unit":
                base = unit_cost * units
            elif utype == "ev":
                base = unit_cost * ev_count
            else:
                base = unit_cost
            amt = inflated(base, t)         # 円
            data[y].append(fmt_man(amt))    # 万円（文字列）
        else:
            data[y].append("")

# 工事費小計
row_index.append(("支出集計", "工事費小計", ""))
for y in years:
    subtotal_yen = 0
    for i, _ in enumerate(row_index[:-1]):
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

# 35年総支出A（円）と必要月額（均等）
total_A_yen = sum(int(data[y][-3].replace(",","")) * 10_000 for y in years)
required_monthly_total_35 = math.ceil(total_A_yen / (horizon * 12)) if total_A_yen>0 else 0
required_psqm_35 = int(round(required_monthly_total_35 / total_private_area)) if total_private_area>0 else 0

# ==========
# 妥当性＆将来値上げ（結論ファースト）
# ==========
g = mlit_benchmark(int(floors), float(total_floor_area)) if (floors and total_floor_area) else {"avg":0,"low":0,"high":0,"label":"—"}
mech_add = mech_add_psqm(mech_park_type, int(mech_park_slots), float(total_private_area)) if total_private_area>0 else 0
low, avg, high = g["low"]+mech_add, g["avg"]+mech_add, g["high"]+mech_add

def judge(psqm:int, low:int, high:int):
    if psqm == 0: return "未入力"
    if psqm < low: return "不足（低すぎ）"
    if psqm > high: return "過剰（高すぎ）"
    return "概ね妥当（幅内）"

def pct_diff(a:int, b:int):
    if b == 0: return None
    return (a - b) / b * 100.0

judge_now = judge(current_psqm, low, high)
judge_req = judge(required_psqm_35, low, high)
diff_now_vs_avg = pct_diff(current_psqm, avg)
diff_req_vs_avg = pct_diff(required_psqm_35, avg)

# ===== 結論ブロック =====
st.subheader("結論（妥当性・将来値上げ・収益性）")

# 収益性（先に計算しておく）
rent_monthly = (rent_psqm * my_private_area) if (rent_psqm and my_private_area) else 0
rent_annual  = rent_monthly * 12
price_yen    = price_million * 10_000  # 万円→円
yield_pct    = int(round((rent_annual / price_yen) * 100)) if price_yen>0 else 0

c1, c2, c3 = st.columns([1.05,1.05,1.2])

with c1:
    st.markdown("**現在の修繕積立金**")
    st.metric("現状：円/㎡・月", int_fmt(current_psqm) if current_psqm else "—")
    st.metric("評価（国交省幅ベース）", judge_now)
    if avg>0:
        st.caption(f"国交省（平均/幅/機械式加算込）：{int_fmt(avg)} ／ {int_fmt(low)}〜{int_fmt(high)} 円/㎡・月")

with c2:
    st.markdown("**将来の必要水準（35年均等）**")
    st.metric("必要：円/㎡・月", int_fmt(required_psqm_35) if required_psqm_35 else "—")
    st.metric("必要：月額（全体・円）", int_fmt(required_monthly_total_35) if required_monthly_total_35 else "—")
    if diff_req_vs_avg is not None and avg>0:
        st.caption(f"必要水準は平均比：{diff_req_vs_avg:+.0f}%")

with c3:
    st.markdown("**収益性（周辺相場ベース）**")
    st.metric("想定月額家賃（円）", int_fmt(rent_monthly))
    st.metric("年間家賃（円）", int_fmt(rent_annual))
    st.metric("表面利回り（％）", int_fmt(yield_pct))

# ==========================
# 次回大規模修繕｜値上げ予測（逆算）
# ==========================
st.subheader("次回大規模修繕｜値上げ予測（逆算）")

today_year = dt.date.today().year
years_to_next = max(0, int(next_major_year) - today_year) if next_major_year else 0
months_left   = years_to_next * 12

# 自動推計：長期表の「A.支出合計」から次回年の必要費を拾う（base_cost_today=0時）
auto_needed_next = 0
if next_major_year and (start_year <= next_major_year <= end_year):
    a_row_idx = None
    for i, (c,n,cy) in enumerate(row_index):
        if c=="支出集計" and n=="A.支出合計":
            a_row_idx = i
            break
    if a_row_idx is not None:
        val = data[next_major_year][a_row_idx]
        if val != "":
            auto_needed_next = int(val.replace(",","")) * 10_000  # 円

needed_at_next = int(base_cost_today) if base_cost_today>0 else int(auto_needed_next)

def ceil_div(a:int, b:int)->int:
    if b <= 0: return 0
    return math.ceil(a / b)

required_monthly_total_threshold = ceil_div(max(0, needed_at_next - int(current_balance)), max(1, months_left)) if needed_at_next>0 else 0
required_psqm_threshold = ceil_div(required_monthly_total_threshold, max(1, total_private_area)) if total_private_area>0 else 0
delta_psqm_threshold = max(0, required_psqm_threshold - current_psqm)

c4, c5, c6 = st.columns([1.05,1.05,1.2])
with c4:
    st.markdown("**次回時点の必要額**")
    st.metric("次回年", int_fmt(next_major_year) if next_major_year else "—")
    st.metric("必要費（全体・円）", int_fmt(needed_at_next) if needed_at_next>0 else "—")

with c5:
    st.markdown("**閾値（値上げ不要となる最小水準）**")
    st.metric("必要月額（全体・円）", int_fmt(required_monthly_total_threshold) if required_monthly_total_threshold>0 else "—")
    st.metric("必要：円/㎡・月（閾値）", int_fmt(required_psqm_threshold) if required_psqm_threshold>0 else "—")

with c6:
    st.markdown("**現状との差**")
    st.metric("差分：円/㎡・月", int_fmt(delta_psqm_threshold) if delta_psqm_threshold>0 else "0")
    if months_left>0:
        st.caption(f"残月数：{months_left} ヶ月（{today_year}→{next_major_year}）")

st.caption("※ 閾値＝ceil((次回必要費 − 現在残高) ÷ 残月数) を円/㎡・月に換算。必要費が未入力のときは長期表から自動推計。")

# ==========================
# （仮）長期修繕計画（35年・万円横テーブル）
# ==========================
st.subheader(f"（仮）長期修繕計画：横テーブル（{start_year}〜{end_year}・単位：万円）")

idx = pd.MultiIndex.from_tuples(row_index, names=["工事区分","工事項目","周期（目安）"])
df = pd.DataFrame({y: data[y] for y in years}, index=idx)
st.dataframe(df, use_container_width=True)

# 参考情報（35年均等の必要水準）
if required_psqm_35>0:
    st.caption(f"参考：35年均等ベースの必要水準＝{int_fmt(required_psqm_35)} 円/㎡・月（全体：{int_fmt(required_monthly_total_35)} 円/月）")

# 背景要因（ヒント表示）
reasons = []
ev_ratio = (ev_count / units) if units else 0.0
if ev_ratio >= 0.03:
    reasons.append("EV比率が高め（EV台数/戸数 ≥ 3%）→ 更新・保守コスト増の要因")
elif ev_ratio >= 0.02:
    reasons.append("EV比率がやや高い（2〜3%）→ 支出増の要因")
if mech_park_slots > 0 and total_private_area>0:
    add = mech_add_psqm(mech_park_type, int(mech_park_slots), float(total_private_area))
    reasons.append(f"機械式駐車場あり（形式：{mech_park_type}、区画：{int(mech_park_slots)}）→ 修繕費上振れ（加算 {int_fmt(add)} 円/㎡・月）")
if floors >= 15:
    reasons.append("高層（15階以上）→ 足場・外装工事の仮設費が相対的に高い")
if total_floor_area < 5_000 and floors < 20 and total_floor_area>0:
    reasons.append("延床<5,000㎡かつ中低層→ 規模効果が効きづらく単価が上がりやすい")

if reasons:
    st.markdown("**背景要因（参考）**")
    st.markdown("- " + "\n- ".join(reasons))

st.caption(
    "※ すべて概算。単価・周期・インフレ率3%は仮置き。外壁・屋上・鉄部面積は延床と階数から推定。"
    " ガイドラインと機械式駐車場の加算は国交省の代表値を実装。"
)