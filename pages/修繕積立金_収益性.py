# pages/修繕積立金_収益性.py
# ─────────────────────────────────────────────────────────────
# 結論ファースト：このマンションは「修繕積立金 いくら以上あれば安心か」を1行で出す
# 　・出力：①安心ライン（全体・円）　②（任意入力時）現状→安心/不安
# 　・根拠：次回大規模修繕の予想額（インフレ3%既定）× 安心係数（既定40%）
# 　・“現在の修繕積立金”の確認書類：管理会社の「重要事項調査報告書等」
# 　・余計な月割り/残月/キャッシュフロー表は一切出しません
# ─────────────────────────────────────────────────────────────

import math
import io
import datetime as dt
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

# 既定パラメータ（必要最小限）
CYCLE_YEARS = 12           # 大規模修繕の基準周期（目安）
DEFAULT_INFL = 0.03        # インフレ率（年・複利）
DEFAULT_UNIT = 20_000      # 大規模修繕 単価（円/㎡・回）…仮の代表値
DEFAULT_SAFE_RATIO = 0.40  # 安心係数（次回必要額の何割あれば「安心」とみなすか）

# 直近未来の「次回年」を築年から推定
def predict_next_year(built_year:int, cycle:int=CYCLE_YEARS)->int:
    if built_year <= 0:
        return 0
    this = dt.date.today().year
    y = built_year
    while y <= this:
        y += cycle
    return y

# 金額の整形（整数のみ）
def yen(n:int)->str:
    try:
        return f"{int(n):,}"
    except:
        return "0"

# PDF生成（A4・1ページ）
def build_pdf(data):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=28, bottomMargin=28, leftMargin=28, rightMargin=28)
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    h1 = styles["Heading1"]; h2 = styles["Heading2"]
    note = ParagraphStyle("note", parent=normal, textColor=colors.grey, leading=14)

    elems = []
    elems.append(Paragraph("🏢 修繕積立金｜『いくら以上あれば安心？』レポート", h1))
    elems.append(Paragraph(f"作成日：{dt.date.today().isoformat()}", normal))
    elems.append(Spacer(1, 10))

    # 結論
    elems.append(Paragraph("■ 結論（この物件の安心ライン）", h2))
    elems.append(Paragraph(
        f"<b>修繕積立金：{yen(data['safe_line_yen'])} 円以上 → 安心</b>", normal
    ))
    elems.append(Spacer(1, 6))
    elems.append(Paragraph(
        f"根拠：次回大規模修繕の予想額（{data['next_year']}年） × 安心係数 {int(data['safe_ratio']*100)}%",
        normal
    ))
    elems.append(Paragraph(
        f"次回大規模の予想額（インフレ{int(data['infl']*100)}%）：{yen(data['next_cost_yen'])} 円",
        normal
    ))
    elems.append(Spacer(1, 10))

    # 参考情報（現状額が入力されていれば判定を表示）
    elems.append(Paragraph("■ 参考（現状の修繕積立金が入力された場合の判定）", h2))
    if data["current_total_input"] > 0:
        elems.append(Paragraph(
            f"現在の修繕積立金（全体・自己申告）：{yen(data['current_total_input'])} 円 → 判定：<b>{data['judge']}</b>",
            normal
        ))
    else:
        elems.append(Paragraph("現在の修繕積立金：不明", normal))
        elems.append(Paragraph("※ 確認書類：管理会社の『重要事項調査報告書等』で確認してください。", note))

    # テーブル：算式の内訳
    elems.append(Spacer(1, 10))
    elems.append(Paragraph("■ 算式の内訳（シンプル）", h2))
    tbl = [
        ["項目", "値"],
        ["延べ床面積（㎡）", yen(data["total_floor_area"])],
        ["大規模修繕 単価（円/㎡・回）", yen(data["unit_cost"])],
        ["次回年（築年から自動推定）", str(data["next_year"])],
        ["今年→次回までの年数", str(data["years_to_next"]) + " 年"],
        ["インフレ率（年・複利）", f"{int(data['infl']*100)} %"],
        ["次回大規模の予想額（円）", yen(data["next_cost_yen"])],
        ["安心係数", f"{int(data['safe_ratio']*100)} %"],
        ["安心ライン（円）", yen(data["safe_line_yen"])],
    ]
    t = Table(tbl, colWidths=[220, 250])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#eeeeee")),
        ("BOX", (0,0), (-1,-1), 0.6, colors.grey),
        ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
        ("ALIGN", (1,1), (-1,-1), "RIGHT"),
    ]))
    elems.append(t)

    doc.build(elems)
    buf.seek(0)
    return buf

# ──────────────── 画面 ────────────────
st.set_page_config(page_title="修繕積立金｜安心ラインだけ出す", layout="centered")
st.title("修繕積立金｜いくら以上あれば安心？（結論だけ）")

with st.sidebar:
    st.header("入力（整数のみ）")
    # 物件条件（デフォルトは「あなたがこれまで使っていたマンション規模」）
    total_floor_area = st.number_input("延べ床面積（㎡・全体）", min_value=0, value=8_000, step=100)
    built_year       = st.number_input("築年（西暦）", min_value=0, max_value=9999, value=2000, step=1)

    # 大規模のモデル
    unit_cost        = st.number_input("大規模修繕 単価（円/㎡・回）", min_value=0, value=DEFAULT_UNIT, step=1_000)
    infl_pct         = st.number_input("インフレ率（年％・複利）", min_value=0, value=3, step=1)
    safe_ratio_pct   = st.number_input("安心係数（％）※次回必要額の何割あれば安心か", min_value=10, value=int(DEFAULT_SAFE_RATIO*100), step=5)

    st.divider()
    # 任意：現状の修繕積立金（全体額）が判明している場合のみ入力
    current_total_input = st.number_input("（任意）現在の修繕積立金（全体・円）", min_value=0, value=0, step=1_000_000)

# 次回年と年差
this_year = dt.date.today().year
next_year = predict_next_year(int(built_year), CYCLE_YEARS) if built_year>0 else 0
years_to_next = max(0, next_year - this_year) if next_year else 0

# 次回大規模の予想額（円）：単価×延床×インフレ複利
infl = (infl_pct/100) if infl_pct>0 else DEFAULT_INFL
if total_floor_area>0 and unit_cost>0 and years_to_next>0:
    base = unit_cost * total_floor_area
    next_cost_yen = int(round(base * ((1 + infl) ** years_to_next)))
else:
    next_cost_yen = 0

# 安心ライン（円）＝ 次回必要額 × 安心係数
safe_ratio = max(0, safe_ratio_pct) / 100.0
safe_line_yen = int(round(next_cost_yen * safe_ratio)) if next_cost_yen>0 else 0

# 画面：結論だけ
st.subheader("結論")
if safe_line_yen > 0:
    st.metric("修繕積立金：いくら以上あれば安心？（全体・円）", f"{yen(safe_line_yen)} 以上")
else:
    st.write("必要な前提（延床・築年・単価）が不足しています。左の入力を確認してください。")

# 現状が入力されたら即判定（安心 / 不安）
if current_total_input > 0 and safe_line_yen > 0:
    judge = "安心" if current_total_input >= safe_line_yen else "不安"
    st.metric("判定（現在の修繕積立金 → 安心/不安）", judge)

st.caption("※ 現在の修繕積立金（全体額）は「管理会社の重要事項調査報告書等」で確認してください。")

# PDF出力
data_for_pdf = {
    "safe_line_yen": safe_line_yen,
    "next_cost_yen": next_cost_yen,
    "safe_ratio": safe_ratio,
    "infl": infl,
    "next_year": next_year if next_year else "—",
    "years_to_next": years_to_next,
    "total_floor_area": total_floor_area,
    "unit_cost": unit_cost,
    "current_total_input": current_total_input,
    "judge": ("安心" if (current_total_input >= safe_line_yen and safe_line_yen>0) else "不安") if current_total_input>0 else "—",
}

st.divider()
if st.button("📄 PDFを作成（結論＋根拠の簡単表）"):
    pdf_buf = build_pdf(data_for_pdf)
    st.download_button(
        label="📥 修繕積立金_安心ライン.pdf をダウンロード",
        data=pdf_buf,
        file_name="修繕積立金_安心ライン.pdf",
        mime="application/pdf"
    )