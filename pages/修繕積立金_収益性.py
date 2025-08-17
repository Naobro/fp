# pages/修繕積立金_収益性.py
# 入力（8項目）だけで：
# ① 修繕積立金の妥当性（円/㎡・月）→ 基準250円と比較して「高い/安い」
# ② 今後の値上がり予想（インフレ3%・35年計画で、10年後いくら必要か）
# ③ 収益性（表面利回り）→ 4%基準で「高い/低い」
# その根拠として、インフレ3%複利・国交省様式の考え方に沿った「いつ・何を・いくら」の年次表も併記。
# ※ 物件利回りの判定には価格が必須のため、「想定価格（任意）」を入力しない場合は③のみN/A表示。

import math
import datetime as dt
import numpy as np
import pandas as pd
import streamlit as st

# --------------------------
# 内部固定（UI非表示）
# --------------------------
INFL = 0.03  # インフレ率（年3% 複利）
BASE_RATE = 250  # 基準：250円/㎡・月（国交省目安の上側で判定用）
PRIVATE_RATIO_BUILDING = 0.75  # 延床→専有合計（代表値、入力させない）
# 階数補正（外装・仮設系概算）
def floor_factor_by_floors(f:int)->float:
    if f <= 5:   return 1.00
    if f <= 10:  return 1.10
    if f <= 20:  return 1.25
    return 1.40

# 工事項目（名称, 周期(年), 単価(円/㎡) or None=総額項目, グループ）
ITEMS = [
    ("仮設工事（足場・昇降設備 等）",      12,  2000,  "仮設"),
    ("外壁塗装・タイル補修・シーリング",     12,  6000,  "塗装"),
    ("屋上・バルコニー・庇 防水改修",       12,  2800,  "防水"),
    ("鉄部塗装（手すり・階段・フェンス等）", 12,  1000,  "塗装"),
    ("給水設備（ポンプ・受水槽等）更新",     12,  1200,  "設備"),
    ("給排水管 更生/更新（㎡按分）",        24,  4400,  "設備"),
    ("分電盤・配電盤・受変電設備 更新",      24,  1500,  "電気・機械"),
    ("インターホン更新（モニター化）",       20,  1800,  "電気・機械"),
    ("エレベーター更新（本体）",            25,  None,   "EV"),  # 総額項目（EV台数×単価）
    ("外構・舗装・植栽 等",                 12,   800,  "外構・その他"),
]
EV_UNIT_COST = 20_000_000  # 円/基

# --------------------------
# ユーティリティ
# --------------------------
def fmt(n):
    try:
        return f"{int(round(n)):,}"
    except:
        return ""

def inflated(base: float, years_from_start: int, rate: float=INFL) -> float:
    return base * ((1.0 + rate) ** max(0, years_from_start))

def schedule_years(built_year:int, cycle:int, start_year:int, end_year:int):
    hits = []
    y = built_year + cycle
    while y <= end_year + cycle*2:
        if start_year <= y <= end_year:
            hits.append(y)
        y += cycle
    return hits

# --------------------------
# UI：入力（8項目）＋ 任意1項目（価格）
# --------------------------
st.set_page_config(page_title="結論ファースト：修繕積立金の妥当性・将来見込み・収益性", layout="wide")
st.title("結論ファースト：妥当性・将来値上がり・収益性（根拠：長期修繕計画 3%）")

with st.sidebar:
    st.header("入力（必須・整数）")
    monthly_total_now = st.number_input("現在の修繕積立金（月額・マンション全体）", min_value=0, step=1000, value=1_000_000)
    my_private_area   = st.number_input("専有面積（あなたの住戸・㎡）", min_value=1, step=1, value=70)
    total_floor_area  = st.number_input("延べ床面積（㎡）", min_value=100, step=10, value=19_500)
    built_year        = st.number_input("築年（西暦）", min_value=1900, max_value=2100, step=1, value=2000)
    units             = st.number_input("戸数（戸）", min_value=1, step=1, value=300)
    floors            = st.number_input("階数（階）", min_value=1, step=1, value=20)
    ev_count          = st.number_input("EV台数（基）", min_value=0, step=1, value=4)
    rent_psqm         = st.number_input("近隣家賃相場（円/㎡・月）", min_value=0, step=100, value=4000)

    st.markdown("---")
    st.header("任意（価格があれば利回りを判定）")
    price_optional    = st.number_input("想定購入価格（円・任意）", min_value=0, step=1_000_000, value=0)

# --------------------------
# 年度レンジ・係数
# --------------------------
start_year = dt.date.today().year           # 現在年から35年
horizon    = 35
end_year   = start_year + horizon - 1
years      = list(range(start_year, end_year + 1))

floor_factor   = floor_factor_by_floors(int(floors))
building_priv  = total_floor_area * PRIVATE_RATIO_BUILDING  # 専有合計㎡（代表値）
share_ratio    = my_private_area / max(1.0, building_priv)  # あなた住戸の専有比率（参考用）

# --------------------------
# 年次計画（マンション全体の「いつ・何を・いくら」）
# --------------------------
year_totals = {y: 0 for y in years}
table = pd.DataFrame(index=[i[0] for i in ITEMS], columns=years, dtype="object")

for name, cycle, unit_or_none, group in ITEMS:
    scheduled = schedule_years(int(built_year), int(cycle), start_year, end_year)
    for y in years:
        if y in scheduled:
            t = y - start_year  # 複利年数
            if name.startswith("エレベーター"):
                base = ev_count * EV_UNIT_COST
            else:
                apply_factor = floor_factor if group in ["仮設", "防水", "塗装", "外構・その他"] else 1.0
                base = (unit_or_none or 0) * total_floor_area * apply_factor
            amt = inflated(base, t, INFL)
            year_totals[y] += amt
            table.at[name, y] = fmt(amt)
        else:
            table.at[name, y] = ""

subtotal = pd.DataFrame([[fmt(year_totals[y]) if year_totals[y] > 0 else "" for y in years]],
                        index=["小計（円）"], columns=years, dtype="object")
table = pd.concat([table, subtotal])

# --------------------------
# 必要単価（専有基準：円/㎡・月）
# --------------------------
required_psqm_per_year = []
for y in years:
    annual_need  = year_totals[y]
    monthly_need = annual_need / 12.0
    psqm_month   = monthly_need / max(1.0, building_priv)
    required_psqm_per_year.append(int(round(psqm_month)))

# 現在の徴収を専有基準に換算（円/㎡・月）
current_psqm = int(round((monthly_total_now / max(1.0, building_priv))))

# 10年後の必要単価（円/㎡・月）
need_in_10 = required_psqm_per_year[10] if len(required_psqm_per_year) > 10 else required_psqm_per_year[-1]
delta_10   = need_in_10 - current_psqm

# --------------------------
# 収益性（表面利回り）※価格未入力ならN/A
# --------------------------
gross_yield = None
if price_optional and price_optional > 0:
    monthly_rent = int(round(rent_psqm * my_private_area))
    annual_rent  = monthly_rent * 12
    gross_yield  = int(round(100 * annual_rent / price_optional))

# --------------------------
# 結論ファースト（3点）
# --------------------------
col1, col2, col3 = st.columns(3)
with col1:
    st.subheader("① 妥当性（修繕積立金）")
    st.metric("現在の単価（円/㎡・月・専有基準）", f"{current_psqm:,}")
    verdict = "高い（≥250）" if current_psqm >= BASE_RATE else "安い（＜250）"
    st.write(f"判定：**{verdict}**（基準：{BASE_RATE}）")

with col2:
    st.subheader("② 今後の値上がり予想")
    st.metric("10年後の必要単価（円/㎡・月）", f"{need_in_10:,}")
    st.write(f"差分（10年後−現在）：**{delta_10:+,} 円/㎡・月**")

with col3:
    st.subheader("③ 収益性（表面利回り）")
    if gross_yield is None:
        st.write("判定：**価格未入力のためN/A**")
        st.caption("※ 想定購入価格を入力すると 4% 基準で判定します。")
    else:
        st.metric("想定・表面利回り（％）", f"{gross_yield}")
        st.write(f"判定：**{'高い（≥4%）' if gross_yield >= 4 else '低い（＜4%）'}**（基準：4%）")

st.markdown("---")

# --------------------------
# 根拠：長期修繕計画（インフレ3%）
# --------------------------
st.subheader(f"根拠：長期修繕計画（{start_year}〜{end_year}・インフレ3%・35年）")
st.caption("※ 雛形の体裁は変えず「いつ・何を・いくら」を年次で表示（小計＝当年の総工事費）。")
st.dataframe(table, use_container_width=True)

# 参考：武蔵小杉の運用事例への導入文（固定テキスト）
st.markdown("""
**不足対策の参考**：大規模物件では修繕積立金の一部を安全運用して不足を抑える取り組みもあります。  
例：パークシティ武蔵小杉ミッドスカイタワーでは、積立金の運用で数億円規模の運用益実績が公表されています。  
""")