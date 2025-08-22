# pages/修繕積立金_収益性.py
# ─────────────────────────────────────────────────────────
# 目的：結論ファーストPDF（4本柱のみ）＋ 画面下に「長期修繕計画（横テーブル）」を表示
# 4本柱（PDF出力に含む）：
#  ① 現在の修繕積立金の妥当性（円/㎡・月：妥当/安い/高い）…国交省モデル＋機械式加算
#  ② 次回大規模修繕の予想額（インフレ3%＋諸経費10%＋消費税10%）
#  ③ 「安心な修繕積立金（全体）」＝ ② × S%（初期30%）
#  ④ 収益性（家賃見込み・利回り）
# 画面下（PDFには入れない）：
#  ・長期修繕計画（35年・万円：横テーブル｜収入/支出/期首/期末）
#  ・最下行に「もし運用（年5%・積立の30%）」行（情報用。残高へは合算しない）
# 注意：
#  ・「基金」NG。全て「修繕積立金残高」と表記。
#  ・縦表NG。横テーブルのみ。
#  ・内部計算はすべて “円（int）” で保持。表示直前にだけ “万円文字列化”。
#  ・PDFの日本語はIPAexフォント（./fonts/ipaexg.ttf）。無い場合は警告表示。
# ─────────────────────────────────────────────────────────

import io
import math
import datetime as dt
from math import ceil
from pathlib import Path

import pandas as pd
import streamlit as st

# ===== PDF（日本語フォント） =====
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab import rl_config

# =====================
# 内部固定パラメータ
# =====================
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

# ==========
# 工事項目マスター（省略なし）
# 単価タイプ：'sqm'（㎡按分）/'per_unit'（戸数×単価）/'ev'（EV台数×単価）/'per_slot'（機械式区画×単価）/'lump'（一式）
# ==========
ITEMS = [
    # 建築（12年）
    ("建築", "外壁塗装・タイル補修・シーリング", 12, "sqm",      6_000),
    ("建築", "屋上・バルコニー・庇 防水改修",     12, "sqm",      2_800),
    ("建築", "鉄部塗装（手すり・階段・フェンス等）", 12, "sqm",  1_000),
    ("建築", "外構・舗装・植栽 等",               12, "sqm",        800),
    ("仮設", "足場仮設（外装工事年）",            12, "sqm",      2_000),

    # 設備
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

# ==========
# ユーティリティ
# ==========
def fmt_man(n_yen:int)->str:
    """円→万円（整数・カンマ文字列）"""
    return f"{int(round(n_yen/10_000)):,}"

def fmt_oku_man(n_yen:int)->str:
    """
    円→「◯億◯◯◯◯万円」表記
    例: 390,000,000 → '3億9000万円' / 12,345,678,901 → '123億4567万円'（万円未満切捨て）
    """
    if n_yen < 10_000:
        return f"{n_yen}円"
    man = n_yen // 10_000
    if man < 10_000:
        return f"{man:,}万円"
    oku = man // 10_000
    man_rem = man % 10_000
    return f"{oku}億{man_rem:04d}万円"

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

def ceil_div(a:int, b:int)->int:
    if b <= 0: return 0
    return (a + b - 1) // b

# ==========
# 画面
# ==========
st.set_page_config(page_title="修繕積立｜結論PDF＋長期表（横）", layout="wide")
st.title("修繕積立｜妥当性・次回大規模・安心ライン・収益性（＋長期表/横）")

with st.sidebar:
    st.header("入力（整数）")

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
    # PDF：安心係数S（次回大規模×S%）
    safe_ratio_pct = st.number_input("安心係数 S（％）", min_value=10, value=30, step=5)

    st.divider()
    # 長期表関連
    current_balance_total = st.number_input("現在の修繕積立金残高（全体・円）", min_value=0, value=0, step=100_000)
    invest_share_pct      = st.number_input("（長期表）運用に回す割合（積立の％）", min_value=0, max_value=100, value=30, step=5)
    invest_rate_pct       = st.number_input("（長期表）運用利回り（年％・複利）", min_value=0, max_value=20, value=5, step=1)

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

# 全体月額（現行）
monthly_total_now = int(current_psqm * total_private_area) if (current_psqm > 0 and total_private_area > 0) else 0
annual_income_now = monthly_total_now * 12  # 円

# ========== ① 妥当性（国交省＋機械式加算） ==========
g = mlit_benchmark(int(floors) if floors else 0, float(total_floor_area) if total_floor_area else 0)
mech_add = mech_add_psqm(mech_park_type, int(mech_park_slots), float(total_private_area)) if total_private_area>0 else 0
low, avg, high = g["low"]+mech_add, g["avg"]+mech_add, g["high"]+mech_add

def judge_price(psqm:int, low:int, high:int):
    if psqm == 0: return "未入力"
    if psqm < low: return "安い"
    if psqm > high: return "高い"
    return "妥当"

judge_now = judge_price(current_psqm, low, high)

# ========== （仮）長期修繕計画（横テーブル：内部は円で保持） ==========
per_floor_area  = total_floor_area / max(1, floors) if floors else 0
facade_area_est = per_floor_area * FACADE_COEF
roof_area_est   = per_floor_area
steel_area_est  = facade_area_est * STEEL_RATIO
floor_factor    = floor_factor_by_floors(int(floors)) if floors else 1.0

def add_row(row_index, data, cat, name, cycle, utype, unit_cost):
    row_index.append((cat, name, f"{cycle}年" if cycle>1 else "毎年"))
    scheduled = set(schedule_years(int(built_year), int(cycle), start_year, end_year)) if built_year else set()
    for y in years:
        put = (cycle == 1 and built_year>0) or (y in scheduled and total_floor_area>0)
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
            amt_yen = inflated(base, t)      # 円
            data[y].append(int(amt_yen))     # 円のまま保持
        else:
            data[y].append(0)                # 円（0）

row_index = []
data = {y: [] for y in years}

for cat, name, cy, utype, unit in ITEMS:
    if "機械式" in cat and mech_park_slots <= 0:
        continue
    add_row(row_index, data, cat, name, cy, utype, unit)

# 支出集計（内部は円で保持）
row_index.append(("支出集計", "工事費小計", ""))
for y in years:
    subtotal_yen = 0
    for i, (c, n, cyc) in enumerate(row_index[:-1]):
        if c == "支出集計":
            continue
        val = data[y][i]
        if isinstance(val, int) and val > 0:
            subtotal_yen += val
    data[y].append(int(subtotal_yen))  # 円

row_index.append(("支出集計", "諸経費（10%）", ""))
for y in years:
    sub_yen = int(data[y][-1])
    data[y].append(int(round(sub_yen * OH)))  # 円

row_index.append(("支出集計", "消費税（10%）", ""))
for y in years:
    sub_yen = int(data[y][-2])
    oh_yen  = int(data[y][-1])
    tax_yen = int(round((sub_yen + oh_yen) * TAX))
    data[y].append(int(tax_yen))  # 円

row_index.append(("支出集計", "A.支出合計", ""))
for y in years:
    sub_yen = int(data[y][-3])
    oh_yen  = int(data[y][-2])
    tax_yen = int(data[y][-1])
    total_yen = sub_yen + oh_yen + tax_yen
    data[y].append(int(total_yen))  # 円

# 収入・残高（現行のまま徴収した場合）— 年額は一定（増やさない）
row_index.append(("収入・残高", "期首残高", ""))
row_index.append(("収入・残高", "修繕積立金収入（年額）", ""))
row_index.append(("収入・残高", "当期収入合計", ""))
row_index.append(("収入・残高", "当期収支（収入合計－A）", ""))
row_index.append(("収入・残高", "期末残高", ""))

for yi, y in enumerate(years):
    beg = int(current_balance_total) if yi == 0 else int(data[years[yi-1]][-1])
    income = int(annual_income_now)
    income_total = beg + income
    a_yen = int(data[y][-3])
    net = income_total - a_yen
    end_bal = net
    data[y].extend([beg, income, income_total, net, end_bal])  # すべて円（int）

# もし運用（年X%・積立のY%）…情報行（残高へは合算しない）
row_index.append(("参考", f"もし運用（年{invest_rate_pct}%・積立の{invest_share_pct}%）", ""))
invest_share = max(0, min(100, int(invest_share_pct))) / 100.0
invest_rate  = max(0, int(invest_rate_pct)) / 100.0
sim_val = 0  # 円
for yi, y in enumerate(years):
    invest_add = int(round(annual_income_now * invest_share))
    sim_val = int(round((sim_val * (1 + invest_rate)) + invest_add))
    data[y].append(sim_val)  # 円（情報表示用）

# 横テーブル：内部は円 → 表示時だけ万円文字列に変換
idx = pd.MultiIndex.from_tuples(row_index, names=["区分","項目","周期"])
df_yen = pd.DataFrame({y: data[y] for y in years}, index=idx)  # 円（int）

def yen_to_man_str(v):
    try:
        v_int = int(v)
        return fmt_man(v_int) if v_int > 0 else ""
    except:
        return ""

df_man = df_yen.applymap(yen_to_man_str)  # 表示用（万円）

# ========== ② 次回大規模の予想額（円） ==========
next_major_year = predict_next_major_year(int(built_year), 12) if built_year else 0
next_major_cost_yen = 0
if next_major_year and (start_year <= next_major_year <= end_year):
    try:
        a_val = df_yen.loc[("支出集計","A.支出合計",""), next_major_year]  # 円（int）
        next_major_cost_yen = int(a_val) if a_val else 0
    except Exception:
        next_major_cost_yen = 0

# ③ 安心ライン（円）＝② × S%
safe_ratio = max(0, safe_ratio_pct) / 100.0
safe_line_yen = int(round(next_major_cost_yen * safe_ratio)) if next_major_cost_yen>0 else 0

# ④ 収益性（家賃・利回り）
rent_monthly = (rent_psqm * my_private_area) if (rent_psqm and my_private_area) else 0
rent_annual  = rent_monthly * 12
price_yen    = price_million * 10_000  # 万円→円
yield_pct    = int(round((rent_annual / price_yen) * 100)) if price_yen>0 else 0

# ========== 画面：4本柱（確認用） ==========
c1, c2, c3, c4 = st.columns([1,1,1,1.2])
with c1:
    st.metric("① 妥当性（円/㎡・月）", f"{int_fmt(current_psqm)} → {judge_now}")
    st.caption(f"基準：{int_fmt(low)}〜{int_fmt(high)} ／ 平均 {int_fmt(avg)}（機械式加算含む）")
with c2:
    st.metric("② 次回大規模 予想額（円）", int_fmt(next_major_cost_yen) if next_major_cost_yen>0 else "—")
    if next_major_year: st.caption(f"対象年：{next_major_year}")
with c3:
    st.metric("③ 安心ライン（全体・円）", int_fmt(safe_line_yen) if safe_line_yen>0 else "—")
    st.caption(f"算式：② × S（{int(safe_ratio*100)}%）")
with c4:
    st.metric("④ 収益性（利回り％）", f"{yield_pct}%")
    st.caption(f"家賃見込み：{int_fmt(rent_monthly)} 円/月・年間 {int_fmt(rent_annual)} 円")

st.divider()
st.subheader(f"（仮）長期修繕計画：横テーブル（{start_year}〜{end_year}・単位：万円）")
st.caption("※ 本表は“仮”。一般的に予想しうる工事項目・周期の概算を年3%複利で表示。PDFには含めません。")
st.dataframe(df_man, use_container_width=True)

# ========== PDF（4本柱のみ） ==========
# フォント用意
FONT_PATH = Path(__file__).resolve().parent.parent / "fonts" / "ipaexg.ttf"
FONT_NAME = "IPAexGothic"
font_ready = False
try:
    if FONT_PATH.exists():
        rl_config.TTFSearchPath.append(str(FONT_PATH.parent))
        pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH.name))
        font_ready = True
    else:
        st.warning("PDF日本語フォント（./fonts/ipaexg.ttf）が見つかりません。日本語が文字化けする場合があります。")
except Exception:
    st.warning("日本語フォントの登録に失敗しました。PDFで文字化けする場合があります。")

def build_pdf_4pillars():
    styles = getSampleStyleSheet()
    base_font = FONT_NAME if font_ready else "Helvetica"
    h1 = ParagraphStyle(name="H1", parent=styles["Heading1"], fontName=base_font, fontSize=18)
    h2 = ParagraphStyle(name="H2", parent=styles["Heading2"], fontName=base_font, fontSize=14)
    normal = ParagraphStyle(name="N", parent=styles["Normal"], fontName=base_font, fontSize=11, leading=16)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=20, rightMargin=20, topMargin=18, bottomMargin=18)
    elems = []

    elems.append(Paragraph("🏢 修繕積立レポート（結論ファースト｜4本柱）", h1))
    elems.append(Paragraph(f"作成日：{dt.date.today().isoformat()}", normal))
    elems.append(Spacer(1, 8))

    elems.append(Paragraph("① 現在の修繕積立金の妥当性（円/㎡・月）", h2))
    elems.append(Paragraph(f"{int_fmt(current_psqm)} → <b>{judge_now}</b>（基準：{int_fmt(low)}〜{int_fmt(high)}／平均 {int_fmt(avg)}。機械式加算込み）", normal))
    elems.append(Spacer(1, 4))

    elems.append(Paragraph("② 次回大規模修繕の予想額（年3%・諸経費/消費税込）", h2))
    elems.append(Paragraph(f"{'—' if next_major_cost_yen<=0 else int_fmt(next_major_cost_yen)} 円（対象年：{next_major_year if next_major_year else '—'}）", normal))
    elems.append(Spacer(1, 4))

    elems.append(Paragraph("③ 安心な修繕積立金（全体）＝ 次回大規模 × S％", h2))
    elems.append(Paragraph(f"{'—' if safe_line_yen<=0 else int_fmt(safe_line_yen)} 円（S＝{int(safe_ratio*100)}%）", normal))
    elems.append(Spacer(1, 4))

    elems.append(Paragraph("④ 収益性（家賃見込み・利回り）", h2))
    elems.append(Paragraph(f"月額家賃見込み：{int_fmt(rent_monthly)} 円／年額：{int_fmt(rent_annual)} 円／表面利回り：{yield_pct} %（価格：{int_fmt(price_yen)} 円）", normal))
    elems.append(Spacer(1, 10))

    doc.build(elems)
    buf.seek(0)
    return buf

st.divider()
if st.button("📄 PDFを作成（4本柱のみ）"):
    pdf_buf = build_pdf_4pillars()
    st.download_button("📥 ダウンロード：修繕積立レポート.pdf", data=pdf_buf, file_name="修繕積立レポート.pdf", mime="application/pdf")