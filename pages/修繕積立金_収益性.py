# pages/修繕積立金_収益性.py
# 目的（結論ファースト・小学生でもわかる）：
# ①いま妥当？（現状の円/㎡・月 vs 国交省モデル）
# ②将来いくら？（次回・その先の大規模修繕：インフレ3%で予測／必要な「いまの最低単価＝安心ライン」）
# ③いま毎月いくら集まってる？（全体の月次収入）と「必要月額（全体）」の比較
# ④収益性（近隣家賃→家賃・利回り）
# ＋証拠：仮の長期修繕計画（35年・12年周期・インフレ3%）
#
# PDF：画面と同じ結論＋「👉 こうだから、こうです」のコメントを出力（reportlab）

import math
import io
import datetime as dt
import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

# =====================
# 固定パラメータ
# =====================
DEFAULT_INFL = 0.03     # 年インフレ（複利）
CYCLE_YEARS  = 12       # 大規模修繕周期（仮）
PRIVATE_RATIO_BUILDING = 0.75  # 延床→総専有の代表換算

# 国交省ガイドライン（R6.6.7改定）円/㎡・月（機械式除く・代表）
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

# 直近未来の「次回年」（築年と周期から）
def predict_next_year(built_year:int, cycle:int=CYCLE_YEARS)->int:
    if built_year <= 0: return 0
    y = built_year
    this = dt.date.today().year
    while y <= this:
        y += cycle
    return y

# 12年ごとの将来年リスト（本年含め35年分の中で）
def future_events(built_year:int, start:int, horizon:int=35, cycle:int=CYCLE_YEARS):
    end = start + horizon - 1
    years = []
    if built_year <= 0: return years
    y = built_year + cycle
    while y <= end + cycle*2:
        if start <= y <= end:
            years.append(y)
        y += cycle
    return years

# 金額表記
def int_fmt(n)->str:
    try:
        return f"{int(n):,}"
    except:
        return "0"

# =====================
# PDF生成
# =====================
def build_pdf(data, events_df):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=28, bottomMargin=28, leftMargin=24, rightMargin=24)
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    h1 = styles["Heading1"]; h2 = styles["Heading2"]
    bullet = ParagraphStyle("bullet", parent=normal, leading=14)

    elems = []
    elems.append(Paragraph("🏢 修繕積立金レポート（結論ファースト）", h1))
    elems.append(Spacer(1, 8))
    elems.append(Paragraph(f"作成日：{dt.date.today().isoformat()}", normal))
    elems.append(Spacer(1, 12))

    # ① 妥当性
    elems.append(Paragraph("① 現在の修繕積立金（妥当性）", h2))
    elems.append(Paragraph(
        f"現在：<b>{int_fmt(data['current_psqm'])}</b> 円/㎡・月 ／ "
        f"国交省モデル：<b>{int_fmt(data['bench_low'])}〜{int_fmt(data['bench_high'])}</b>（平均 {int_fmt(data['bench_avg'])}） 円/㎡・月",
        normal
    ))
    elems.append(Paragraph(f"👉 判定：<b>{data['judge_now']}</b>", bullet))
    elems.append(Spacer(1, 8))

    # ② 将来
    elems.append(Paragraph("② 将来：大規模修繕に間に合う『いまの最低単価（安心ライン）』", h2))
    elems.append(Paragraph(
        f"次回年：<b>{data['next_year']}</b> ／ 残月：<b>{int_fmt(data['months_left'])}</b> ヶ月 ／ "
        f"予想必要費（全体）：<b>{int_fmt(data['next_cost_yen'])}</b> 円", normal))
    elems.append(Paragraph(
        f"いま必要な最低水準＝<b>{int_fmt(data['need_psqm_now'])}</b> 円/㎡・月 "
        f"（全体：{int_fmt(data['need_monthly_total'])} 円/月）", bullet))
    if data["fund_input"] == 0:
        elems.append(Paragraph(
            "※ 現在の積立残高（基金）が不明のため『0円（厳しめ）』で試算。下の感度表で基金がある場合の目安を併記。", normal))

    # 感度表（基金）
    elems.append(Spacer(1, 6))
    fund_table = [["前提：基金（円）", "必要：円/月（全体）", "必要：円/㎡・月"]]
    for row in data["fund_sensitivity"]:
        fund_table.append([int_fmt(row["fund"]), int_fmt(row["need_monthly"]), int_fmt(row["need_psqm"])])
    t = Table(fund_table, colWidths=[90, 120, 100])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#eeeeee")),
        ("BOX", (0,0), (-1,-1), 0.6, colors.grey),
        ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
        ("ALIGN", (1,1), (-1,-1), "RIGHT")
    ]))
    elems.append(t)

    elems.append(Spacer(1, 10))
    # ③ いま毎月
    elems.append(Paragraph("③ 現在の『毎月の収入（全体）』と『必要月額（全体）』", h2))
    elems.append(Paragraph(
        f"現在の収入（全体）：<b>{int_fmt(data['monthly_total_now'])}</b> 円/月 "
        f"＝ 現在psqm×総専有（{int_fmt(data['total_private_area'])}㎡）", normal))
    elems.append(Paragraph(
        f"必要月額（全体）：<b>{int_fmt(data['need_monthly_total'])}</b> 円/月 "
        f"→ 差：<b>{int_fmt(data['gap_monthly_total'])}</b> 円/月", bullet))

    elems.append(Spacer(1, 10))
    # ④ 収益性
    elems.append(Paragraph("④ 収益性（周辺家賃相場）", h2))
    elems.append(Paragraph(
        f"家賃相場：<b>{int_fmt(data['rent_psqm'])}</b> 円/㎡・月 ／ 専有：{int_fmt(data['my_private_area'])}㎡ → "
        f"想定家賃：<b>{int_fmt(data['rent_monthly'])}</b> 円/月（年 {int_fmt(data['rent_annual'])} 円）", normal))
    elems.append(Paragraph(
        f"購入価格：<b>{int_fmt(data['purchase_yen'])}</b> 円 ／ 表面利回り：<b>{data['yield_pct']:.1f}%</b>", bullet))

    elems.append(Spacer(1, 14))
    elems.append(Paragraph("✅ 結論（ひと目で）", h2))
    for line in data["summary_lines"]:
        elems.append(Paragraph(f"・{line}", normal))

    elems.append(Spacer(1, 14))
    elems.append(Paragraph("（証拠）仮の長期修繕計画：12年周期／インフレ3%（単位：万円）", h2))
    # 35年テーブル
    tbl = [ ["年"] + list(events_df.columns) ]
    tbl += [ ["必要費（A.支出合計）"] + list(events_df.loc["A.支出合計（万円）"].values) ]
    tbl_obj = Table(tbl, colWidths=[60] + [48]*len(events_df.columns))
    tbl_obj.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#eeeeee")),
        ("BOX", (0,0), (-1,-1), 0.6, colors.grey),
        ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
        ("ALIGN", (1,1), (-1,-1), "RIGHT")
    ]))
    elems.append(tbl_obj)

    doc.build(elems)
    buf.seek(0)
    return buf

# =====================
# アプリ本体
# =====================
st.set_page_config(page_title="修繕積立｜妥当性・安心ライン・収益性（PDF出力）", layout="wide")
st.title("修繕積立｜妥当性・安心ライン（次回工事）・収益性　→ PDF出力")

with st.sidebar:
    st.header("入力（整数）")
    # 現在のpsqm（住戸月額→psqm換算は不要。psqmが基本）
    current_psqm = st.number_input("現在の修繕積立金（円/㎡・月）", min_value=0, value=214, step=1)

    # 建物条件
    total_floor_area = st.number_input("延べ床面積（㎡・全体）", min_value=0, value=8_000, step=100)
    units            = st.number_input("戸数（戸）", min_value=0, value=100, step=1)
    floors           = st.number_input("階数（階）", min_value=0, value=10, step=1)
    built_year       = st.number_input("築年（西暦）", min_value=0, max_value=9999, value=2000, step=1)

    # 長期修繕の単価モデル（次回や将来の大規模：円/㎡・回）
    mlit_unit_per_sqm = st.number_input("大規模修繕 単価モデル（円/㎡・回）", min_value=0, value=20_000, step=1_000)

    # インフレ
    infl_rate_pct   = st.number_input("インフレ率（年％・複利）", min_value=0, value=3, step=1)

    # 次回大規模年（空欄時は築年から12年周期で自動）
    next_year_default = predict_next_year(int(built_year), CYCLE_YEARS) if built_year>0 else 0
    next_major_year   = st.number_input("次回大規模修繕の年（YYYY）", min_value=0, value=next_year_default, step=1)

    # 現在の基金（不明なら0のままでOK。感度表を自動表示）
    current_fund = st.number_input("現在の積立残高（基金・円）※不明なら0でOK", min_value=0, value=0, step=1_000_000)

    st.divider()
    # 収益性
    my_private_area  = st.number_input("あなたの専有面積（㎡・住戸）", min_value=0, value=70, step=1)
    rent_psqm        = st.number_input("周辺家賃相場（円/㎡・月）", min_value=0, value=4_000, step=1_000)
    purchase_million = st.number_input("購入価格（万円・住戸）", min_value=0, value=7_000, step=100)

# ===== 計算 =====
this_year = dt.date.today().year
start_year = this_year
horizon = 35
infl = (infl_rate_pct/100) if infl_rate_pct>0 else DEFAULT_INFL

# 総専有（代表換算）。実データがあれば差し替え。
total_private_area = int(total_floor_area * PRIVATE_RATIO_BUILDING) if total_floor_area>0 else 0

# 国交省モデル
bench = mlit_benchmark(int(floors), float(total_floor_area)) if (floors and total_floor_area) else {"avg":0,"low":0,"high":0}
bench_avg, bench_low, bench_high = bench["avg"], bench["low"], bench["high"]

def judge(psqm:int, low:int, high:int)->str:
    if psqm == 0: return "未入力"
    if low and psqm < low: return "不足（低すぎ）"
    if high and psqm > high: return "過剰（高すぎ）"
    return "概ね妥当（幅内）"

judge_now = judge(current_psqm, bench_low, bench_high)

# 将来イベント年（12年周期）
event_years = future_events(int(built_year), start_year, horizon=horizon, cycle=CYCLE_YEARS) if built_year>0 else []

# イベントの必要費をインフレ付きで推計（円）
def event_cost_yen_at_year(year:int)->int:
    if year <= 0 or total_floor_area <= 0 or mlit_unit_per_sqm <= 0:
        return 0
    t = max(0, year - this_year)  # 今年からの年差で将来価格へ
    base = mlit_unit_per_sqm * total_floor_area          # 円
    # 諸経費や税は意見が分かれるため、ここでは「モデル単価に込み」とみなす簡略版
    return int(round(base * ((1 + infl) ** t)))

# 表示用：次回コストと残月
if next_major_year and (next_major_year >= this_year):
    next_cost_yen = event_cost_yen_at_year(int(next_major_year))
    months_left = (int(next_major_year) - this_year) * 12
else:
    next_cost_yen = 0
    months_left = 0

def ceil_div(a:int, b:int)->int:
    if b <= 0: return 0
    return math.ceil(a / b)

# 安心ライン（いま必要な最小一定額）→ 全体月額 → 円/㎡・月
if next_cost_yen > 0 and months_left > 0 and total_private_area > 0:
    gap_total = max(0, next_cost_yen - int(current_fund))  # 基金を控除
    need_monthly_total = ceil_div(gap_total, months_left)
    need_psqm_now = ceil_div(need_monthly_total, total_private_area)
else:
    need_monthly_total = 0
    need_psqm_now = 0

# 現在の「全体」収入（円/月）
monthly_total_now = current_psqm * total_private_area if (current_psqm>0 and total_private_area>0) else 0
gap_monthly_total = max(0, need_monthly_total - monthly_total_now)

# 基金感度表（基金が不明or 0なら参考として提示）
fund_sensitivity = []
if next_cost_yen > 0 and months_left > 0 and total_private_area > 0:
    # 0円（厳しめ）、次回費用の25%・50%・75%・100%を基準に5点
    for f in [0, int(next_cost_yen*0.25), int(next_cost_yen*0.5), int(next_cost_yen*0.75), int(next_cost_yen*1.0)]:
        gap = max(0, next_cost_yen - f)
        nm = ceil_div(gap, months_left)
        np = ceil_div(nm, total_private_area)
        fund_sensitivity.append({"fund": f, "need_monthly": nm, "need_psqm": np})

# 収益性
purchase_yen = purchase_million * 10_000
rent_monthly = rent_psqm * my_private_area
rent_annual = rent_monthly * 12
yield_pct = (rent_annual / purchase_yen * 100) if purchase_yen>0 else 0.0

# 将来イベント一覧（証拠）：35年・12年周期（万円表示）
cols = []
vals = []
for y in range(start_year, start_year + horizon):
    cols.append(str(y))
    c = event_cost_yen_at_year(y)
    vals.append(int(round(c/10_000)))
events_df = pd.DataFrame([vals], index=["A.支出合計（万円）"], columns=cols)

# ===== 画面（結論ファースト） =====
st.subheader("① 現在の修繕積立金（妥当性）")
c1, c2, c3 = st.columns([1,1,1.2])
with c1:
    st.metric("現在：円/㎡・月", int_fmt(current_psqm) if current_psqm else "—")
with c2:
    st.metric("国交省モデル（平均）", int_fmt(bench_avg) if bench_avg else "—")
    st.caption(f"幅：{int_fmt(bench_low)}〜{int_fmt(bench_high)} 円/㎡・月")
with c3:
    st.metric("評価", judge_now)

st.subheader("② 将来：次回・その先の大規模修繕（インフレ3%）")
c4, c5, c6 = st.columns([1,1,1.2])
with c4:
    st.metric("次回年", int_fmt(next_major_year) if next_major_year else "—")
    st.metric("残月（今→次回）", int_fmt(months_left) if months_left>0 else "—")
with c5:
    st.metric("次回必要費（全体）", int_fmt(next_cost_yen) if next_cost_yen>0 else "—")
with c6:
    st.metric("安心ライン：円/㎡・月", int_fmt(need_psqm_now) if need_psqm_now>0 else "—")
    st.caption("＝ ceil((次回必要費 − 基金) ÷ 残月) ÷ 総専有㎡")

if fund_sensitivity:
    st.write("基　金　感　度（目安）：基金がある場合の必要水準")
    fs_df = pd.DataFrame(
        [{"基金(円)": f["fund"], "必要(月・全体円)": f["need_monthly"], "必要(円/㎡・月)": f["need_psqm"]}
         for f in fund_sensitivity]
    )
    st.dataframe(fs_df, use_container_width=True)

st.subheader("③ 現在の『全体の月次収入』と『必要月額（全体）』")
c7, c8, c9 = st.columns([1,1,1.2])
with c7:
    st.metric("総専有（推定）", int_fmt(total_private_area))
with c8:
    st.metric("現在の収入（全体・円/月）", int_fmt(monthly_total_now) if monthly_total_now else "—")
with c9:
    st.metric("必要月額（全体・円/月）", int_fmt(need_monthly_total) if need_monthly_total>0 else "—")
    st.caption(f"差（必要 − 現在）＝ {int_fmt(gap_monthly_total)} 円/月")

st.subheader("④ 収益性（周辺家賃相場）")
d1, d2, d3 = st.columns([1,1,1.2])
with d1:
    st.metric("家賃相場（円/㎡・月）", int_fmt(rent_psqm))
with d2:
    st.metric("想定家賃（円/月）", int_fmt(rent_monthly))
    st.metric("年間家賃（円/年）", int_fmt(rent_annual))
with d3:
    st.metric("表面利回り（％）", f"{yield_pct:.1f}")

st.subheader("（証拠）仮の長期修繕計画：35年（単位：万円）")
st.dataframe(events_df, use_container_width=True)

# ===== PDFデータ作成 =====
data_for_pdf = {
    "current_psqm": current_psqm,
    "bench_avg": bench_avg,
    "bench_low": bench_low,
    "bench_high": bench_high,
    "judge_now": judge_now,
    "next_year": next_major_year if next_major_year else "—",
    "months_left": months_left,
    "next_cost_yen": next_cost_yen,
    "need_monthly_total": need_monthly_total,
    "need_psqm_now": need_psqm_now,
    "fund_input": current_fund,
    "fund_sensitivity": fund_sensitivity,
    "monthly_total_now": monthly_total_now,
    "gap_monthly_total": gap_monthly_total,
    "total_private_area": total_private_area,
    "rent_psqm": rent_psqm,
    "my_private_area": my_private_area,
    "rent_monthly": rent_monthly,
    "rent_annual": rent_annual,
    "purchase_yen": purchase_yen,
    "yield_pct": yield_pct,
    "summary_lines": [
        f"現在の単価は国交省モデルの{('範囲内' if judge_now!='不足（低すぎ）' and judge_now!='過剰（高すぎ）' else '範囲外')}（評価：{judge_now}）。",
        f"次回大規模（{next_major_year}年）までに必要なのは {int_fmt(need_psqm_now)} 円/㎡・月（全体 {int_fmt(need_monthly_total)} 円/月）。",
        f"いまの収入は全体で {int_fmt(monthly_total_now)} 円/月、必要との差は {int_fmt(gap_monthly_total)} 円/月。",
        f"収益性は表面利回り {yield_pct:.1f}%（相場 {int_fmt(rent_psqm)} 円/㎡・月）。"
    ]
}

st.divider()
colpdf1, colpdf2 = st.columns([1,3])
with colpdf1:
    if st.button("📄 コメント付きPDFを作成"):
        pdf_buf = build_pdf(data_for_pdf, events_df)
        st.download_button(
            label="📥 修繕積立レポート.pdf をダウンロード",
            data=pdf_buf,
            file_name="修繕積立レポート.pdf",
            mime="application/pdf"
        )
with colpdf2:
    st.caption("※ 基金が不明でも『0円（厳しめ）』で試算し、基金がある場合の感度表をPDFに併記します。")