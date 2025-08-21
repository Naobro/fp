# pages/修繕積立金_収益性.py
# 結論ファースト：
# ① 現状の㎡単価と国交省基準（＋機械式補正）で妥当性判定
# ② 将来の値上げ予想（次回大規模修繕の必要額→逆算）
# ③ 収益性（周辺家賃㎡単価×専有×12 ÷ 購入価格）
# ④ 下段：（仮）長期修繕計画（35年・万円横テーブル）
# ⑤ 追加：短期ターゲット（例：5年後に2億円必要）を“住戸月額”に逆算＋据置可否判定
#
# 重要：表示は整数（円／万円／％）。長期表は“万円”、結論は“円”。

import math
import datetime as dt
import pandas as pd
import streamlit as st

# =====================
# 内部固定パラメータ
# =====================
INFL = 0.03         # 既定インフレ（年3%・複利）
TAX = 0.10          # 消費税（本体+諸経費に課税）
OH = 0.10           # 諸経費（工事費小計の10%）※設計監理・予備費は任意で拡張可
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
    ("建築", "外壁塗装・タイル補修・シーリング", 12, "sqm",      6_000),
    ("建築", "屋上・バルコニー・庇 防水改修",   12, "sqm",      2_800),
    ("建築", "鉄部塗装（手すり・階段・フェンス等）", 12, "sqm",  1_000),
    ("設備", "給水設備（ポンプ・受水槽等）更新", 12, "sqm",      1_200),
    ("設備", "給排水管 更生/更新（㎡按分）",      24, "sqm",      4_400),
    ("設備", "分電盤・配電盤・受変電設備 更新",    24, "sqm",      1_500),
    ("設備", "インターホン更新（モニター化）",     20, "per_unit", 70_000),
    ("設備", "エレベーター更新（本体）",          25, "ev",     20_000_000),
    ("設備", "外構・舗装・植栽 等",               12, "sqm",        800),
    ("足場仮設", "足場仮設（共通）",              12, "sqm",      2_000),
]

# ==========
# ユーティリティ
# ==========
def fmt_man(n_yen: float) -> str:
    """円→万円（整数・カンマ）"""
    man = int(round(n_yen / 10_000))
    return f"{man:,}"

def int_fmt(n) -> str:
    try:
        return f"{int(n):,}"
    except:
        return "0"

def man_str_to_yen(s: str) -> int:
    """'1,234'（万円文字列）→ 円"""
    if not s: return 0
    return int(s.replace(",", "")) * 10_000

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
    "2段（ピット1段）昇降式":      6_450,
    "2段（ピット2段）昇降式":      5_840,
    "3段（ピット1段）昇降横行式":  7_210,
    "4段（ピット2段）昇降横行式":  6_235,
    "エレベーター式・垂直循環式":   4_645,
    "その他":                       5_235,
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
    return total_floor_area  # 設備系は㎡按分（粗按分）

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
    my_monthly_now   = st.number_input("あなたの修繕積立金（月額・円）", min_value=0, value=15_000, step=1_000)
    my_private_area  = st.number_input("専有面積（㎡）", min_value=0, value=70, step=1)
    current_psqm_in  = st.number_input("現状の修繕積立金（円/㎡・月）※未入力=0で自動計算", min_value=0, value=0, step=1)

    # 建物条件
    total_floor_area = st.number_input("延べ床面積（㎡）", min_value=0, value=8_000, step=100)
    units            = st.number_input("戸数（戸）", min_value=0, value=100, step=1)
    built_year       = st.number_input("築年（西暦）", min_value=0, max_value=9_999, value=2_000, step=1)
    floors           = st.number_input("階数（階）", min_value=0, value=10, step=1)
    ev_count         = st.number_input("EV台数（基）", min_value=0, value=1, step=1)
    mech_park_slots  = st.number_input("機械式駐車場の区画数（基）", min_value=0, value=0, step=1)
    mech_park_type   = st.selectbox("機械式駐車場の形式", list(MECH_PARK_UNIT_YEN.keys()), index=0)

    # 収益性（周辺家賃・購入価格）
    rent_psqm        = st.number_input("周辺家賃相場（円/㎡・月）", min_value=0, value=4_000, step=1_000)
    price_million    = st.number_input("購入価格（万円）", min_value=0, value=7_000, step=100)

    st.divider()
    # 次回大規模修繕（逆算）：年は築年から自動推定を初期値に
    next_year_default = predict_next_major_year(int(built_year), 12)
    next_major_year   = st.number_input("次回大規模修繕の年（YYYY）", min_value=0, value=next_year_default, step=1)

    # 長期表から拾えない時のバックアップ：国交省モデル（円/㎡・回）
    mlit_unit_per_sqm = st.number_input("（任意）大規模修繕 単価（円/㎡・回）", min_value=0, value=20_000, step=1_000)

    # 今日の必要費を直接入れる場合（使えばこちら最優先）
    base_cost_today   = st.number_input("（任意）今日の必要費（全体・円）※入力時はこれが最優先", min_value=0, value=0, step=100_000)

    # インフレ率（空欄=0なら既定3%）
    infl_rate_pct     = st.number_input("（任意）インフレ率（年％）※未入力=0は内部既定3%", min_value=0, value=0, step=1)

    # 現在の積立残高（全体）
    current_balance   = st.number_input("（任意）現在の修繕積立金 残高（全体・円）", min_value=0, value=0, step=100_000)

    st.divider()
    # 短期ターゲット（住戸逆算）— 例：5年後に2億円必要なら？
    st.subheader("短期ターゲット（住戸逆算）")
    short_years        = st.number_input("目標までの年数（年）", min_value=1, value=5, step=1)
    short_needed_total = st.number_input("目標時点の必要費（全体・円）", min_value=0, value=200_000_000, step=1_000_000)
    use_infl_short     = st.checkbox("インフレ複利を適用（年率は上の設定を使用）", value=True)

# 年レンジ（長期表）
start_year = dt.date.today().year
horizon    = 35
end_year   = start_year + horizon - 1
years      = list(range(start_year, end_year + 1))

# 総専有面積（推計）
total_private_area = int(total_floor_area * PRIVATE_RATIO_BUILDING) if total_floor_area else 0

# 現状の円/㎡・月（psqm直入力優先→無ければ住戸月額÷専有で推計）
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

# 明細行（各工事行：万円で記入）
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
            amt = inflated(base, t)           # 円（将来価格）
            data[y].append(fmt_man(amt))      # 万円（文字列）
        else:
            data[y].append("")

# 位置インデックスを確定して以降の集計で使用（参照のズレ防止）
# 1) 工事費小計
row_index.append(("支出集計", "工事費小計", ""))
idx_subtotal = len(row_index) - 1
for y in years:
    subtotal_yen = 0
    # 明細行のみ集計（= 小計行の直前まで）
    for i in range(idx_subtotal):
        val = data[y][i]
        if val:
            subtotal_yen += man_str_to_yen(val)
    data[y].append(fmt_man(subtotal_yen))

# 2) 諸経費（OH）、3) 消費税、4) A.支出合計（いずれも“工事費小計”を基礎に算出）
row_index.append(("支出集計", "諸経費（10%）", ""))
idx_oh = len(row_index) - 1
for y in years:
    base_yen = man_str_to_yen(data[y][idx_subtotal])
    oh_yen = int(round(base_yen * OH))
    data[y].append(fmt_man(oh_yen))

row_index.append(("支出集計", "消費税（10%）", ""))
idx_tax = len(row_index) - 1
for y in years:
    base_yen = man_str_to_yen(data[y][idx_subtotal])
    oh_yen   = man_str_to_yen(data[y][idx_oh])
    tax_yen  = int(round((base_yen + oh_yen) * TAX))
    data[y].append(fmt_man(tax_yen))

row_index.append(("支出集計", "A.支出合計", ""))
idx_A = len(row_index) - 1
for y in years:
    base_yen = man_str_to_yen(data[y][idx_subtotal])
    oh_yen   = man_str_to_yen(data[y][idx_oh])
    tax_yen  = man_str_to_yen(data[y][idx_tax])
    sum_yen  = base_yen + oh_yen + tax_yen
    data[y].append(fmt_man(sum_yen))

# 収入・残高（現行のまま徴収した場合）
row_index.append(("収入・残高", "期首繰越", ""))
idx_beg = len(row_index) - 1
row_index.append(("収入・残高", "修繕積立金収入（年額）", ""))
idx_income = len(row_index) - 1
row_index.append(("収入・残高", "当期収入合計", ""))
idx_income_total = len(row_index) - 1
row_index.append(("収入・残高", "当期収支（収入合計－A）", ""))
idx_net = len(row_index) - 1
row_index.append(("収入・残高", "期末残高（次期繰越）", ""))
idx_end = len(row_index) - 1

for y_idx, y in enumerate(years):
    if y_idx == 0:
        beg_yen = 0
    else:
        # 前年の“期末残高”を参照
        beg_yen = man_str_to_yen(data[years[y_idx-1]][idx_end])

    income_yen = monthly_total_now * 12
    income_total_yen = beg_yen + income_yen
    a_yen = man_str_to_yen(data[y][idx_A])  # A.支出合計（円）
    net_yen = income_total_yen - a_yen
    end_yen = net_yen  # マイナスもそのまま表示（不足の可視化）

    data[y].extend([
        fmt_man(beg_yen),
        fmt_man(income_yen),
        fmt_man(income_total_yen),
        fmt_man(net_yen),
        fmt_man(end_yen),
    ])

# 35年総支出A（円）と必要月額（均等・全体）→ 円/㎡・月へ正規化
total_A_yen = sum(man_str_to_yen(data[y][idx_A]) for y in years)
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
diff_now_vs_avg = pct_diff(current_psqm, avg)
diff_req_vs_avg = pct_diff(required_psqm_35, avg)

# 収益性（周辺相場ベース）
rent_monthly = (rent_psqm * my_private_area) if (rent_psqm and my_private_area) else 0
rent_annual  = rent_monthly * 12
price_yen    = price_million * 10_000  # 万円→円
yield_pct    = int(round((rent_annual / price_yen) * 100)) if price_yen>0 else 0

# ===== 結論ブロック =====
st.subheader("結論（妥当性・将来値上げ・収益性）")

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

# 1) 長期表から自動取得（該当年が列にある場合）— 万円→円（A.支出合計）
auto_needed_next = 0
if next_major_year and (start_year <= next_major_year <= end_year):
    val = data[next_major_year][idx_A]  # 万円の文字列
    if val:
        auto_needed_next = man_str_to_yen(val)

# 2) 今日の必要費の手入力が最優先
if base_cost_today and base_cost_today > 0:
    model_today = int(base_cost_today)
# 3) 無ければ、国交省モデル（円/㎡・回）で推計（今日時点）
elif mlit_unit_per_sqm and total_floor_area:
    subtotal = mlit_unit_per_sqm * total_floor_area   # ベース（円）
    subtotal_oh = int(round(subtotal * (1 + OH)))     # 諸経費込
    model_today = int(round(subtotal_oh * (1 + TAX))) # 税込
else:
    model_today = 0

# 4) 次回年の必要費（円）
use_infl = (infl_rate_pct/100) if (infl_rate_pct and infl_rate_pct>0) else INFL
if auto_needed_next > 0:
    needed_at_next = int(auto_needed_next)  # 表の値は年次インフレ反映済
else:
    needed_at_next = int(round(model_today * ((1 + use_infl) ** years_to_next))) if model_today>0 else 0

def ceil_div(a:int, b:int)->int:
    if b <= 0: return 0
    return math.ceil(a / b)

required_monthly_total_threshold = ceil_div(max(0, needed_at_next - int(current_balance)), max(1, months_left)) if needed_at_next>0 else 0
required_psqm_threshold = ceil_div(required_monthly_total_threshold, max(1, total_private_area)) if total_private_area>0 else 0
delta_psqm_threshold = max(0, required_psqm_threshold - current_psqm)

c4, c5, c6 = st.columns([1.05,1.05,1.2])
with c4:
    st.markdown("**次回時点の必要額（全体）**")
    st.metric("次回年", int_fmt(next_major_year) if next_major_year else "—")
    st.metric("必要費（円）", int_fmt(needed_at_next) if needed_at_next>0 else "—")
    if auto_needed_next>0:
        st.caption("※ 長期表（A.支出合計・万円）から自動取得 → 円換算済")
    elif model_today>0:
        st.caption(f"※ 国交省モデル：{int_fmt(mlit_unit_per_sqm)} 円/㎡・回 × 延床 → (OH, TAX) → インフレ{int(round(use_infl*100))}%/年×{years_to_next}年 複利")

with c5:
    st.markdown("**閾値（値上げ不要となる最小水準）**")
    st.metric("必要月額（全体・円）", int_fmt(required_monthly_total_threshold) if required_monthly_total_threshold>0 else "—")
    st.metric("必要：円/㎡・月（閾値）", int_fmt(required_psqm_threshold) if required_psqm_threshold>0 else "—")

with c6:
    st.markdown("**現行との差**")
    st.metric("差分：円/㎡・月", int_fmt(delta_psqm_threshold) if delta_psqm_threshold>0 else "0")
    if months_left>0:
        st.caption(f"残月数：{months_left} ヶ月（{today_year}→{next_major_year}）")

st.caption("※ 注意：長期表は『万円』表示、結論・逆算欄は『円』表示。単位混在を防止。")

# ==========================
# 短期ターゲット（住戸逆算）— 例：5年後に2億円必要なら？
# ==========================
st.subheader("短期ターゲット（住戸逆算）")

# 目標額（全体）の将来価値（インフレ任意）
if use_infl_short:
    target_total_future = int(round(short_needed_total * ((1 + use_infl) ** short_years)))
else:
    target_total_future = int(short_needed_total)

# 建物全体の必要“月額”を逆算 → 円/㎡・月 → 住戸月額
short_months = short_years * 12
short_required_monthly_total = ceil_div(max(0, target_total_future - int(current_balance)), max(1, short_months))
short_required_psqm           = ceil_div(short_required_monthly_total, max(1, total_private_area)) if total_private_area>0 else 0
short_required_monthly_unit   = short_required_psqm * my_private_area

# 現行（月額・住戸）と比較（psqm由来 or 直接入力のどちらでも OK）
current_monthly_unit = current_psqm * my_private_area if current_psqm>0 else my_monthly_now
short_delta_unit     = max(0, short_required_monthly_unit - current_monthly_unit)

c7, c8, c9 = st.columns([1.05,1.05,1.2])
with c7:
    st.markdown("**目標の将来価値**")
    st.metric("必要額（全体・円）", int_fmt(target_total_future))
    st.metric("残月数（ヶ月）", int_fmt(short_months))

with c8:
    st.markdown("**据置可否の境界（月額）**")
    st.metric("必要：円/㎡・月", int_fmt(short_required_psqm) if short_required_psqm>0 else "—")
    st.metric("あなたの必要月額（円）", int_fmt(short_required_monthly_unit) if short_required_monthly_unit>0 else "—")

with c9:
    st.markdown("**現行との差（住戸）**")
    st.metric("現在（月額・円）", int_fmt(current_monthly_unit))
    st.metric("追加必要額（円/月）", int_fmt(short_delta_unit))

st.caption("※ 算式：ceil((目標の将来価値 − 現在残高) ÷ 残月数) を円/㎡・月に換算 → 専有㎡で住戸月額へ。")

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
    "※ すべて概算。単価・周期・既定インフレ3%は仮置き。外壁・屋上・鉄部面積は延床と階数から推定。"
    " 国交省ガイドラインと機械式加算は代表値。長期表＝『万円』、結論＝『円』。"
)