import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io

# ========= フォント ==========
FONT_PATH = "NotoSansJP-Regular.ttf"
try:
    pdfmetrics.registerFont(TTFont('NotoSansJP', FONT_PATH))
except Exception as e:
    st.error(f"フォント読み込み失敗: {e}\n{FONT_PATH}をプロジェクト直下に置いてください。")
    st.stop()

def get_japanese_style(size=11, font_name='NotoSansJP', alignment='CENTER', leading=15, bold=False, color=colors.black):
    align_map = {'LEFT': 0, 'CENTER': 1, 'RIGHT': 2}
    return ParagraphStyle(
        name=f'japanese_style_{size}_{alignment}',
        fontName=font_name,
        fontSize=size,
        leading=leading,
        alignment=align_map.get(alignment, 1),  # デフォルトCENTER
        fontWeight="bold" if bold else "normal",
        textColor=color,
        spaceAfter=2, spaceBefore=2
    )

def calc_monthly_payment(principal, annual_rate, years):
    r = annual_rate / 12
    n = years * 12
    if r == 0:
        return principal / n
    return principal * r / (1 - (1 + r) ** -n)

# ========== 入力UI ==========
st.title("住宅ローン 提案シミュレーター")

c1, c2, c3, c4 = st.columns(4)
with c1:
    principal = st.number_input("借入額 (万円)", 500, 100000, 5000) * 10000
with c2:
    self_fund = st.number_input("自己資金 (万円)", 0, 100000, 500) * 10000
with c3:
    annual_income = st.number_input("年収 (万円)", 100, 10000, 600) * 10000
with c4:
    age = st.number_input("年齢", 18, 80, 35)

max_year = max(1, 79 - age)
years = st.slider("返済期間 (年)", 1, max_year, min(35, max_year))

# ========== 銀行・金利設定 ==========
rates = {
    "SBI新生銀行": 0.59,
    "三菱UFJ銀行": 0.595,
    "PayPay銀行": 0.599,
    "じぶん銀行": 0.78,
    "住信SBI銀行": 0.809,
}
property_price_guess = (principal + self_fund) / 1.07
ltv = principal / property_price_guess if property_price_guess else 1
if ltv <= 0.8:
    rates["住信SBI銀行"] = 0.649
elif ltv <= 1.0:
    rates["住信SBI銀行"] = 0.739
else:
    rates["住信SBI銀行"] = 0.809

rate_diff = {
    "SBI新生銀行": {"がん100": 0.01},
    "三菱UFJ銀行": {"がん50": 0.15, "7大疾病": 0.3, "全疾病": 0.5},
    "PayPay銀行": {"がん50": 0.05, "がん100": 0.15},
    "じぶん銀行": {"がん100": 0.054, "7大疾病": 0.1},
    "住信SBI銀行": {"三大疾病": 0.2 if age < 40 else 0.4},
}

special_notes = {
    "SBI新生銀行": ["125%ルールなし", "ZEH -0.1%"],
    "三菱UFJ銀行": ["三大疾病50%", "ワイド団信+0.3%"],
    "PayPay銀行": ["がん50以上で全疾病・失業補償", "ソフトバンク割 最大-0.13%", "125%ルールなし"],
    "じぶん銀行": ["ワイド団信+0.3%", "じぶん割 最大-0.15%"],
    "住信SBI銀行": ["全疾病保障+三大疾病50%標準付帯", "125%ルールなし"],
}
bank_order = list(rates.keys())
plans_order = ["一般団信", "がん50", "がん100", "三大疾病", "7大疾病", "全疾病"]

# ========== 金利修正欄 ==========
st.markdown("---")
with st.expander("🔧 金利を修正する（営業担当用）", expanded=False):
    cols = st.columns(len(rates))
    for i, bank in enumerate(rates.keys()):
        rates[bank] = cols[i].number_input(f"{bank} (%)", value=rates[bank], key=f"rate_input_{bank}", format="%.3f")

# ========== 借入上限額（10万円単位切り捨て・右揃え）==========
def calc_borrowing_limit(income, exam_rate, limit_ratio, age):
    exam_years = min(35, 79 - age)
    annual_payment = income * limit_ratio
    monthly_payment = annual_payment / 12
    r = exam_rate / 12
    n = exam_years * 12
    if r == 0:
        raw_limit = monthly_payment * n
    else:
        raw_limit = monthly_payment * (1 - (1 + r) ** -n) / r
    return int(raw_limit // 100000 * 100000)

banks_info = {
    "SBI新生銀行": {"審査金利": 0.03, "返済比率": 0.40},
    "三菱UFJ銀行": {"審査金利": 0.0354, "返済比率": 0.35},
    "PayPay銀行": {"審査金利": 0.03, "返済比率": 0.40},
    "じぶん銀行": {"審査金利": 0.0257, "返済比率": 0.35},
    "住信SBI銀行": {"審査金利": 0.0325, "返済比率": 0.35},
}
limit_amounts = {}
limit_data = []
for bank, info in banks_info.items():
    limit = calc_borrowing_limit(annual_income, info["審査金利"], info["返済比率"], age)
    limit_amounts[bank] = limit
    man = int(limit // 10000)
    limit_data.append([bank, f"{man:,} 万円"])
limit_df = pd.DataFrame(limit_data, columns=["銀行名", "借入上限額"])

st.subheader("💰 年収からの借入上限額")
table_html = """
<style>
.blimit th, .blimit td {border:1.2px solid #aaa; padding:12px; font-size:18px;}
.blimit th {background:#F2F6FA;}
.blimit {border-collapse:collapse; width:480px; margin-bottom:20px;}
</style>
<table class="blimit">
<thead><tr><th align="center" style="width:250px;">銀行名</th><th align="center" style="width:230px;">借入上限額</th></tr></thead>
<tbody>
"""
for i, row in limit_df.iterrows():
    table_html += f"<tr><td align='center'>{row['銀行名']}</td><td align='right'>{row['借入上限額']}</td></tr>"
table_html += "</tbody></table>"
st.markdown(table_html, unsafe_allow_html=True)

# ========== テーブル生成＆ハイライトインデックス抽出 ==========
def make_table_data_and_highlight():
    rows = []
    highlights = []
    for plan in plans_order:
        row = []
        row_vals = []
        for bank in bank_order:
            if principal > limit_amounts[bank]:
                row.append({"rate": None, "monthly": None, "years": None})
                continue
            available = (plan == "一般団信" or plan in rate_diff.get(bank, {}))
            if available:
                base_rate = rates[bank] / 100
                add = rate_diff.get(bank, {}).get(plan, 0) / 100
                calc_years = min(79 - age, years)
                if bank in ["SBI新生銀行", "三菱UFJ銀行"]:
                    calc_years = min(calc_years, 35)
                if bank not in ["SBI新生銀行", "三菱UFJ銀行"] and calc_years > 35:
                    base_rate += 0.001
                monthly = calc_monthly_payment(principal, base_rate + add, calc_years)
                row.append({"rate": base_rate + add, "monthly": monthly, "years": calc_years})
                row_vals.append((len(row)-1, monthly))
            else:
                row.append({"rate": None, "monthly": None, "years": None})
        min_idxs = set()
        if row_vals:
            minval = min([x[1] for x in row_vals])
            for col_idx, v in row_vals:
                if abs(v - minval) < 0.5:
                    min_idxs.add(col_idx)
        rows.append(row)
        highlights.append(min_idxs)
    # 最長50年（一般団信下のみ）
    row_50 = []
    row_50_vals = []
    for bank in bank_order:
        if principal > limit_amounts[bank] or bank in ["SBI新生銀行", "三菱UFJ銀行"]:
            row_50.append({"rate": None, "monthly": None, "years": None})
        else:
            base_rate = rates[bank] / 100
            add = rate_diff.get(bank, {}).get("一般団信", 0) / 100
            current_bank_max_years = min(79 - age, 50)
            if current_bank_max_years > 35:
                base_rate += 0.001
            monthly_longest = calc_monthly_payment(principal, base_rate + add, current_bank_max_years)
            row_50.append({"rate": base_rate + add, "monthly": monthly_longest, "years": current_bank_max_years})
            row_50_vals.append((len(row_50)-1, monthly_longest))
    min_idxs_50 = set()
    if row_50_vals:
        minval = min([x[1] for x in row_50_vals])
        for col_idx, v in row_50_vals:
            if abs(v - minval) < 0.5:
                min_idxs_50.add(col_idx)
    return rows, highlights, row_50, min_idxs_50

table_rows, highlight_rows, row_50, highlight_50 = make_table_data_and_highlight()

# ========== 金利比較HTMLテーブル（Web UI用）==========
def make_html_cell(rate_data, is_min_monthly, width_css):
    rate = rate_data["rate"]
    monthly = rate_data["monthly"]
    years = rate_data["years"]
    base_style = "text-align:center;vertical-align:middle;"
    bg = "background-color:#FFF8C8;" if is_min_monthly else ""
    if rate is None:
        return f"<td style='{width_css}{base_style}'></td>"
    return (f"<td style='{width_css}height:68px;{base_style}{bg}'>"
            f"<div style='font-size:22px;font-weight:bold;color:#1B232A'>{rate*100:.3f}%</div>"
            f"<div style='font-size:22px;font-weight:bold;color:#226BB3'>¥{monthly:,.0f}</div>"
            f"<div style='font-size:14px;color:#666;'>({years}年返済)</div></td>")

# -------- 幅拡大（プラン=220px, 銀行=180px）---------
plan_width = "min-width:220px;max-width:220px;width:220px;"
bank_width = "min-width:180px;max-width:180px;width:180px;"
html_table_output = f"""
<style>
.loan-table, .loan-table th, .loan-table td {{border:1.2px solid #aaa; border-collapse: collapse;}}
.loan-table th, .loan-table td {{padding: 13px;}}
.loan-table {{background-color:#fff; width:100%; table-layout:fixed;}}
.loan-table th {{background-color:#F2F6FA; font-size:18px;}}
.loan-table td {{font-size:18px;}}
</style>
<table class="loan-table">
<thead><tr>
<th style='{plan_width}text-align:center;font-size:18px;'>プラン</th>""" + "".join(
    [f"<th style='{bank_width}text-align:center;font-size:18px'>{b}</th>" for b in bank_order]
) + "</tr></thead><tbody>"

for i, plan in enumerate(plans_order):
    html_table_output += f"<tr><td style='{plan_width}text-align:center;font-weight:bold;font-size:18px;'>{plan}</td>"
    for col_idx, bank in enumerate(bank_order):
        rate_data = table_rows[i][col_idx]
        is_min = (col_idx in highlight_rows[i] and rate_data["monthly"] is not None)
        html_table_output += make_html_cell(rate_data, is_min, bank_width)
    # 一般団信の下に最長50年
    if plan == "一般団信":
        html_table_output += f"<tr><td style='{plan_width}text-align:center;font-weight:bold;font-size:17px;background-color:#F9F6EF;'>最長50年</td>"
        for col_idx, bank in enumerate(bank_order):
            rate_data = row_50[col_idx]
            is_min = (col_idx in highlight_50 and rate_data["monthly"] is not None)
            html_table_output += make_html_cell(rate_data, is_min, bank_width)
        html_table_output += "</tr>"

# 特記事項
html_table_output += f"<tr><td style='{plan_width}text-align:center;font-weight:bold;font-size:14px;background-color:#FCF9F0;'>特記事項</td>"
for bank in bank_order:
    html_table_output += f"<td style='{bank_width}font-size:12px;text-align:left;background-color:#FCF9F0;'>{'<br>'.join(special_notes[bank])}</td>"
html_table_output += "</tr></tbody></table>"

st.markdown(html_table_output, unsafe_allow_html=True)

# ========== PDF出力：UIテーブルの完全コピー ==========
def create_pdf_reportlab():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                            leftMargin=10*mm, rightMargin=10*mm,
                            topMargin=13*mm, bottomMargin=13*mm)
    style_title = get_japanese_style(size=21, font_name='NotoSansJP', alignment='CENTER', leading=31, bold=True)
    style_header = get_japanese_style(size=13, font_name='NotoSansJP', alignment='CENTER', leading=24, bold=True, color=colors.HexColor('#226BB3'))
    style_cell = get_japanese_style(size=12, font_name='NotoSansJP', alignment='CENTER', leading=24)
    style_cellcontent = get_japanese_style(size=15, font_name='NotoSansJP', alignment='CENTER', leading=19, bold=True, color=colors.HexColor('#1B232A'))

    elements = []
    elements.append(Paragraph("住宅ローン提案書", style_title))
    elements.append(Spacer(1, 5*mm))
    elements.append(Paragraph(f"<b>■ 借入金額：¥{principal:,.0f}</b>", style_header))
    elements.append(Spacer(1, 8*mm))

    table_data_pdf = []
    header_row = [Paragraph("プラン", style_header)] + [Paragraph(b, style_header) for b in bank_order]
    table_data_pdf.append(header_row)
    for i, plan in enumerate(plans_order):
        row = [Paragraph(plan, style_cell)]
        for col_idx, bank in enumerate(bank_order):
            rate_data = table_rows[i][col_idx]
            if rate_data["rate"] is None:
                row.append(Paragraph("", style_cell))
            else:
                cell_content = f"<b>{rate_data['rate']*100:.3f}%</b><br/><b>¥{rate_data['monthly']:,.0f}</b><br/><font size=10>({rate_data['years']}年返済)</font>"
                row.append(Paragraph(cell_content, style_cellcontent))
        table_data_pdf.append(row)
        if plan == "一般団信":
            row_50_pdf = [Paragraph("最長50年", style_cell)]
            for col_idx, bank in enumerate(bank_order):
                rate_data = row_50[col_idx]
                if rate_data["rate"] is None:
                    row_50_pdf.append(Paragraph("", style_cell))
                else:
                    cell_content = f"<b>{rate_data['rate']*100:.3f}%</b><br/><b>¥{rate_data['monthly']:,.0f}</b><br/><font size=10>({rate_data['years']}年返済)</font>"
                    row_50_pdf.append(Paragraph(cell_content, style_cellcontent))
            table_data_pdf.append(row_50_pdf)

    nrows = len(table_data_pdf)
    row_heights = [36*mm]*nrows
    col_widths = [58*mm] + [43*mm]*len(bank_order)  # 全体で約273mm

    table_style = TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.9, colors.HexColor("#bbb")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F2F6FA")),
        ('LEFTPADDING', (0,0), (-1,-1), 14),
        ('RIGHTPADDING', (0,0), (-1,-1), 14),
        ('TOPPADDING', (0,0), (-1,-1), 13),
        ('BOTTOMPADDING', (0,0), (-1,-1), 13),
    ])
    row_cursor = 1
    for i, min_idxs in enumerate(highlight_rows):
        for col_idx in min_idxs:
            table_style.add('BACKGROUND', (col_idx+1, row_cursor), (col_idx+1, row_cursor), colors.HexColor('#FFF8C8'))
        row_cursor += 1
        if plans_order[i] == "一般団信":
            for col_idx in highlight_50:
                table_style.add('BACKGROUND', (col_idx+1, row_cursor), (col_idx+1, row_cursor), colors.HexColor('#FFF8C8'))
            row_cursor += 1

    table = Table(table_data_pdf, colWidths=col_widths, rowHeights=row_heights)
    table.setStyle(table_style)
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer

if st.button("📄 PDFを作成"):
    pdf_buffer = create_pdf_reportlab()
    st.download_button(
        label="📥 PDFをダウンロード",
        data=pdf_buffer,
        file_name="住宅ローン提案書.pdf",
        mime="application/pdf"
    )
