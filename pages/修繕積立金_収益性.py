# pages/修繕積立金_収益性.py
# ─────────────────────────────────────────────────────────
# 目的：結論ファーストPDF（4点）＋ 下段に「仮の長期修繕計画」横テーブル
# 表示順（重要度順）：
#  ① 現在の修繕積立金の妥当性（円/㎡・月：妥当/安い/高い）
#  ② 次回大規模の予想額（インフレ3%＋諸経費10%＋消費税10%）
#  ③ 「安心な修繕積立金（全体）」＝◯◯円以上（=②×安全率S%）
#  ④ 収益性（家賃見込み・利回り）
#  下段：仮の長期修繕計画（35年・万円）横テーブル（工事項目×年／工事費小計→諸経費→税→A.支出合計）
# 注意：
#  - 「修繕積立金 残高」不明時は判定しない（“未確認”と明示）
#  - 「基金」という語は使わない（全て「修繕積立金」）
#  - 縦表NG／横表のみ
# ─────────────────────────────────────────────────────────

import io
import math
import datetime as dt
from math import ceil

import pandas as pd
import streamlit as st

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# ========== 内部既定 ==========
INFL = 0.03   # インフレ率（年3%・複利）
OH   = 0.10   # 諸経費（工事費小計の10%）
TAX  = 0.10   # 消費税（小計+諸経費の10%）
PRIVATE_RATIO_BUILDING = 0.75  # 延床→総専有（代表値）
FACADE_COEF   = 1.25
STEEL_RATIO   = 0.10

def floor_factor_by_floors(f:int)->float:
    if f <= 5:   return 1.00
    if f <= 10:  return 1.10
    if f <= 20:  return 1.25
    return 1.40

# ========== 工事項目マスター（省略なし） ==========
# 単価タイプ：'sqm'（㎡按分）/'per_unit'（戸数×単価）/'ev'（EV台数×単価）/'per_slot'（機械式区画×単価）/'lump'（一式）
ITEMS = [
    # 建築系（12年目安）
    ("建築", "外壁塗装・タイル補修・シーリング", 12, "sqm",      6_000),
    ("建築", "屋上・バルコニー・庇 防水改修",     12, "sqm",      2_800),
    ("建築", "鉄部塗装（手すり・階段・フェンス等）", 12, "sqm",  1_000),
    ("建築", "外構・舗装・植栽 等",               12, "sqm",        800),
    ("仮設", "足場仮設（外装工事年）",            12, "sqm",      2_000),

    # 設備系
    ("設備", "給水設備（ポンプ・受水槽等）更新",   12, "sqm",      1_200),
    ("設備", "給排水管 更生/更新（㎡按分）",      24, "sqm",      4_400),
    ("設備", "分電盤・配電盤・受変電設備 更新",    24, "sqm",      1_500),
    ("設備", "インターホン更新（モニター化）",     20, "per_unit", 70_000),
    ("設備", "エレベーター更新（本体）",          25, "ev",   20_000_000),

    # 機械式（ある場合のみ反映）
    ("機械式", "機械式駐車設備 更新（部分）",      12, "per_slot", 1_500_000),
    ("機械式", "機械式駐車設備 更新（全面）",      20, "per_slot", 3_000_000),

    # 毎年（定期保守・点検）
    ("毎年", "エレベーター保守点検（毎年）",        1, "ev",   1_200_000),
    ("毎年", "消防設備点検（毎年）",                1, "lump",    300_000),
    ("毎年", "雑修繕・軽微補修（毎年）",            1, "lump",    500_000),
]

# 機械式の月額（妥当性の円/㎡・月に加算する用）
MECH_PARK_UNIT_YEN = {
    "2段（ピット1段）昇降式":      6_450,
    "2段（ピット2段）昇降式":      5_840,
    "3段（ピット1段）昇降横行式":  7_210,
    "4段（ピット2段）昇降横行式":  6_235,
    "エレベーター式・垂直循環式":   4_645,
    "その他":                       5_235,
}

# ========== ユーティリティ ==========
def fmt_man(n_yen:int)->str:
    return f"{int(round(n_yen/10_000)):,}"

def int_fmt(n)->str:
    try:
        return f"{int(n):,}"
    except:
        return "0"

def inflated(base_yen: float, years_from_start: int) -> int:
    return int(round(base_yen * ((1.0 + INFL) ** max(0, years_from_start))))

def schedule_years(built_year:int, cycle:int, start_year:int, end_year:int):
    years = []
    if cycle <= 0:
        return [y for y in range(start_year, end_year+1)]
    y = built_year + cycle
    while y <= end_year + cycle*2:
        if start_year <= y <= end_year:
            years.append(y)
        y += cycle
    return years

def area_for_item(cat:str, name:str, per_floor_area:float, facade_area_est:float,
                  roof_area_est:float, steel_area_est:float, floor_factor:float,
                  total_floor_area:float) -> float:
    if "外壁塗装" in name:               return facade_area_est * floor_factor
    if "防水" in name:                   return roof_area_est * floor_factor
    if "鉄部塗装" in name:               return steel_area_est * floor_factor
    if "外構・舗装・植栽" in name:        return per_floor_area * 0.5
    if "足場仮設" in name:               return facade_area_est * floor_factor
    return total_floor_area  # 設備系は㎡按分

def predict_next_major_year(built_year:int, cycle:int=12)->int:
    if built_year <= 0: return 0
    this = dt.date.today().year
    y = built_year
    while y <= this:
        y += cycle
    return y

def mlit_benchmark(floors:int, total_floor_area:float):
    # R6.6.7改定相当の代表帯（機械式加算は別処理）
    if floors >= 20:
        return {"avg": 338, "low": 240, "high": 410, "label": "20階以上"}
    if total_floor_area < 5_000:
        return {"avg": 335, "low": 235, "high": 430, "label": "20階未満・延床<5,000㎡"}
    if total_floor_area < 10_000:
        return {"avg": 252, "low": 170, "high": 320, "label": "20階未満・延床5,000〜10,000㎡"}
    if total_floor_area < 20_000:
        return {"avg": 271, "low": 200, "high": 330, "label": "20階未満・延床10,000〜20,000㎡"}
    return {"avg": 255, "low": 190, "high": 325, "label": "20階未満・延床20,000㎡以上"}

def mech_add_psqm(unit_type:str, slots:int, total_private_area:float)->int:
    if total_private_area <= 0 or slots <= 0:
        return 0
    per = MECH_PARK_UNIT_YEN.get(unit_type, 0)
    return int(round(per * slots / total_private_area))

# ========== 画面 ==========
st.set_page_config(page_title="修繕積立｜結論PDF＋長期表（横）", layout="wide")
st.title("修繕積立｜妥当性・次回大規模・安心ライン・収益性（＋長期表/横）")

with st.sidebar:
    st.header("入力（整数・デフォルト込み）")

    # 現状の積立：psqmが0なら「住戸月額÷専有」で自動
    my_monthly_now   = st.number_input("あなたの修繕積立金（月額・円）", min_value=0, value=15_000, step=1_000)
    my_private_area  = st.number_input("専有面積（㎡）", min_value=0, value=70, step=1)
    current_psqm_in  = st.number_input("現状の修繕積立金（円/㎡・月）※未入力=0で自動計算", min_value=0, value=0, step=1)

    # 建物条件
    total_floor_area = st.number_input("延べ床面積（㎡）", min_value=0, value=8_000, step=100)
    units            = st.number_input("戸数（戸）", min_value=0, value=100, step=1)
    built_year       = st.number_input("築年（西暦）", min_value=0, max_value=9999, value=2000, step=1)
    floors           = st.number_input("階数（階）", min_value=0, value=10, step=1)
    ev_count         = st.number_input("EV台数（基）", min_value=0, value=1, step=1)

    # 機械式駐車場
    mech_park_slots  = st.number_input("機械式駐車場 区画数（基）", min_value=0, value=0, step=1)
    mech_park_type   = st.selectbox("機械式の形式（妥当性加算）", list(MECH_PARK_UNIT_YEN.keys()), index=0)

    st.divider()
    # 収益性（周辺家賃・購入価格）
    rent_psqm     = st.number_input("周辺家賃相場（円/㎡・月）", min_value=0, value=4_000, step=1_000)
    price_million = st.number_input("購入価格（万円）", min_value=0, value=7_000, step=100)

    st.divider()
    # 安心係数S（直近大規模×S%）
    safe_ratio_pct = st.number_input("安心係数 S（％）", min_value=10, value=40, step=5)

# 年レンジ（横展開）
start_year = dt.date.today().year
horizon    = 35
end_year   = start_year + horizon - 1
years      = list(range(start_year, end_year + 1))

# 総専有面積
total_private_area = int(total_floor_area * PRIVATE_RATIO_BUILDING) if total_floor_area else 0

# 現状の円/㎡・月
if current_psqm_in > 0:
    current_psqm = int(current_psqm_in)
elif my_private_area > 0:
    current_psqm = int(round(my_monthly_now / my_private_area)) if my_monthly_now > 0 else 0
else:
    current_psqm = 0

# ========== 妥当性①（国交省＋機械式加算） ==========
g = mlit_benchmark(int(floors) if floors else 0, float(total_floor_area) if total_floor_area else 0)
mech_add = mech_add_psqm(mech_park_type, int(mech_park_slots), float(total_private_area)) if total_private_area>0 else 0
low, avg, high = g["low"]+mech_add, g["avg"]+mech_add, g["high"]+mech_add

def judge_price(psqm:int, low:int, high:int):
    if psqm == 0: return "未入力"
    if psqm < low: return "安い"
    if psqm > high: return "高い"
    return "妥当"

judge_now = judge_price(current_psqm, low, high)

# ========== 仮の長期修繕計画（横テーブル生成：万円文字列） ==========
per_floor_area  = total_floor_area / max(1, floors) if floors else 0
facade_area_est = per_floor_area * FACADE_COEF
roof_area_est   = per_floor_area
steel_area_est  = facade_area_est * STEEL_RATIO
floor_factor    = floor_factor_by_floors(int(floors)) if floors else 1.0

def add_row_to_table(row_index, data, cat, name, cycle, utype, unit_cost):
    row_index.append((cat, name, f"{cycle}年" if cycle>1 else "毎年"))
    scheduled = set(schedule_years(int(built_year), int(cycle), start_year, end_year)) if built_year else set()
    for y in years:
        put = False
        if cycle == 1 and built_year>0:
            put = True
        elif y in scheduled and total_floor_area>0:
            put = True
        if put:
            t = y - start_year
            if utype == "sqm":
                base = unit_cost * area_for_item(cat, name, per_floor_area, facade_area_est, roof_area_est,
                                                 steel_area_est, floor_factor, total_floor_area)
            elif utype == "per_unit":
                base = unit_cost * units
            elif utype == "ev":
                base = unit_cost * ev_count
            elif utype == "per_slot":
                base = unit_cost * mech_park_slots
            else:
                base = unit_cost
            amt_yen = inflated(base, t)
            data[y].append(fmt_man(amt_yen))  # 万円
        else:
            data[y].append("")

row_index = []
data = {y: [] for y in years}

for cat, name, cy, utype, unit in ITEMS:
    if "機械式" in cat and mech_park_slots <= 0:
        continue
    add_row_to_table(row_index, data, cat, name, cy, utype, unit)

# 支出集計（万円）
row_index.append(("支出集計", "工事費小計", ""))
for y in years:
    subtotal_yen = 0
    for i, (c, n, cyc) in enumerate(row_index[:-1]):
        if c == "支出集計":  # まだ無い
            continue
        val = data[y][i]
        if val != "":
            subtotal_yen += int(val.replace(",", "")) * 10_000
    data[y].append(fmt_man(subtotal_yen))

row_index.append(("支出集計", "諸経費（10%）", ""))
for y in years:
    sub_yen = int(data[y][-1].replace(",", "")) * 10_000
    data[y].append(fmt_man(int(round(sub_yen * OH))))

row_index.append(("支出集計", "消費税（10%）", ""))
for y in years:
    sub_yen = int(data[y][-2].replace(",", "")) * 10_000
    oh_yen  = int(data[y][-1].replace(",", "")) * 10_000
    tax_yen = int(round((sub_yen + oh_yen) * TAX))
    data[y].append(fmt_man(tax_yen))

row_index.append(("支出集計", "A.支出合計", ""))
for y in years:
    sub_yen = int(data[y][-3].replace(",", "")) * 10_000
    oh_yen  = int(data[y][-2].replace(",", "")) * 10_000
    tax_yen = int(data[y][-1].replace(",", "")) * 10_000
    total_yen = sub_yen + oh_yen + tax_yen
    data[y].append(fmt_man(total_yen))

# 横テーブルDF
idx = pd.MultiIndex.from_tuples(row_index, names=["工事区分","工事項目","周期"])
df_man = pd.DataFrame({y: data[y] for y in years}, index=idx)  # 単位：万円（文字列）

# ========== ② 次回大規模の予想額（円） ==========
next_major_year = predict_next_major_year(int(built_year), 12) if built_year else 0
next_major_cost_yen = 0
if next_major_year and (start_year <= next_major_year <= end_year):
    try:
        a_val = df_man.loc[("支出集計","A.支出合計",""), next_major_year]
        if a_val:
            next_major_cost_yen = int(a_val.replace(",","")) * 10_000
    except Exception:
        next_major_cost_yen = 0

# ③ 安心ライン（円）＝② × S%
safe_ratio = max(0, safe_ratio_pct) / 100.0
safe_line_yen = int(round(next_major_cost_yen * safe_ratio)) if next_major_cost_yen>0 else 0

# ④ 収益性（家賃見込み・利回り）
rent_monthly = (rent_psqm * my_private_area) if (rent_psqm and my_private_area) else 0
rent_annual  = rent_monthly * 12
price_yen    = price_million * 10_000  # 万円→円
yield_pct    = round((rent_annual / price_yen) * 100, 1) if price_yen>0 else 0.0

# ========== 画面の確認表示（簡潔） ==========
c1, c2, c3, c4 = st.columns([1,1,1,1.2])
with c1:
    st.metric("① 妥当性（円/㎡・月）", f"{int_fmt(current_psqm)} → {judge_now}")
    st.caption(f"基準：{int_fmt(low)}〜{int_fmt(high)} ／ 平均 {int_fmt(avg)}（機械式加算含む）")
with c2:
    st.metric("② 次回大規模 予想額（円）", int_fmt(next_major_cost_yen) if next_major_cost_yen>0 else "—")
    if next_major_year: st.caption(f"対象年：{next_major_year}")
with c3:
    st.metric("③ 安心ライン（全体・円）", int_fmt(safe_line_yen) if safe_line_yen>0 else "—")
    st.caption("算式：② × S%")
with c4:
    st.metric("④ 収益性（利回り％）", f"{yield_pct}%")
    st.caption(f"家賃見込み：{int_fmt(rent_monthly)} 円/月・年間 {int_fmt(rent_annual)} 円")

st.divider()
st.subheader(f"（仮）長期修繕計画：横テーブル（{start_year}〜{end_year}・単位：万円）")
st.caption("【注意】本表は“仮”です。一般的に予想しうる工事項目・周期・数量を用いた概算で、年3%（複利）で将来価格を表示。正式計画・見積で必ず確認。")
st.dataframe(df_man, use_container_width=True)

# ========== PDF出力 ==========
def build_pdf():
    styles = getSampleStyleSheet()
    h1 = styles["Heading1"]; h2 = styles["Heading2"]; normal = styles["Normal"]

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=16, rightMargin=16, topMargin=16, bottomMargin=16)
    elems = []

    # タイトル
    elems.append(Paragraph("🏢 修繕積立レポート（結論ファースト＋長期表/横）", h1))
    elems.append(Paragraph(f"作成日：{dt.date.today().isoformat()}", normal))
    elems.append(Spacer(1, 8))

    # 結論ブロック（①→②→③→④の順で強調）
    elems.append(Paragraph("① 現在の修繕積立金の妥当性（円/㎡・月）", h2))
    elems.append(Paragraph(f"{int_fmt(current_psqm)} → <b>{judge_now}</b>（基準：{int_fmt(low)}〜{int_fmt(high)} ／ 平均 {int_fmt(avg)}・機械式加算含む）", normal))
    elems.append(Spacer(1, 4))

    elems.append(Paragraph("② 次回大規模の予想額（インフレ3%・諸経費/消費税込）", h2))
    elems.append(Paragraph(f"{'—' if next_major_cost_yen<=0 else int_fmt(next_major_cost_yen)} 円（対象年：{next_major_year if next_major_year else '—'}）", normal))
    elems.append(Spacer(1, 4))

    elems.append(Paragraph("③ 安心な修繕積立金（全体）＝ ◯◯円以上", h2))
    elems.append(Paragraph(f"{'—' if safe_line_yen<=0 else int_fmt(safe_line_yen)} 円　※算式：② × 安心係数S（{int(safe_ratio*100)}%）", normal))
    elems.append(Spacer(1, 4))

    elems.append(Paragraph("④ 収益性（家賃見込み・利回り）", h2))
    elems.append(Paragraph(f"月額家賃見込み：{int_fmt(rent_monthly)} 円／年額：{int_fmt(rent_annual)} 円／利回り：{yield_pct} %（価格：{int_fmt(price_yen)} 円）", normal))
    elems.append(Spacer(1, 10))

    # 仮の長期修繕計画（横テーブル）
    elems.append(Paragraph(f"（仮）長期修繕計画：横テーブル（{start_year}〜{end_year}・単位：万円）", h2))
    elems.append(Paragraph("【注意】本表は“仮”。一般的に予想しうる工事項目・周期・数量の概算で、年3%（複利）で将来価格。正式計画・見積で必ず確認。", normal))
    elems.append(Spacer(1, 6))

    # 表を年で分割（横幅対策）
    all_years = years
    chunk = 12  # 12年ずつ
    # ヘッダ
    header_fixed = ["工事区分","工事項目","周期"]

    for i in range(0, len(all_years), chunk):
        cols = all_years[i:i+chunk]
        tbl_data = [header_fixed + [str(c) for c in cols]]
        for (cat, name, cyc), row in df_man[cols].iterrows():
            tbl_data.append([cat, name, cyc] + [str(v) for v in row.values.tolist()])
        t = Table(tbl_data, repeatRows=1)
        t.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#efefef")),
            ("ALIGN", (3,1), (-1,-1), "RIGHT"),
            ("FONT", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 7.2),
        ]))
        elems.append(t)
        elems.append(Spacer(1, 8))

    doc.build(elems)
    buf.seek(0)
    return buf

st.divider()
if st.button("📄 PDFを作成（1→2→3→4＋下段：長期表/横）"):
    pdf_buf = build_pdf()
    st.download_button("📥 ダウンロード：修繕積立レポート.pdf", data=pdf_buf, file_name="修繕積立レポート.pdf", mime="application/pdf")