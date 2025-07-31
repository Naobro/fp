import streamlit as st
import pandas as pd
import os
from fpdf import FPDF
import tempfile

# ========== フォント ==========
FONT_PATH = os.path.join("fonts", "NotoSansJP-Regular.ttf")
if not os.path.exists(FONT_PATH):
    st.error(f"フォントファイル {FONT_PATH} が見つかりません。\nfonts フォルダに NotoSansJP-Regular.ttf を配置してください。")
    st.stop()

# ========== ローン計算 ==========
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

# ========== 借入上限額（10万円単位切り捨て）==========
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

# ========== テーブル生成 ==========
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

# ========== 金利比較HTMLテーブル ==========
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

html_table_output += f"<tr><td style='{plan_width}text-align:center;font-weight:bold;font-size:14px;background-color:#FCF9F0;'>特記事項</td>"
for bank in bank_order:
    html_table_output += f"<td style='{bank_width}font-size:12px;text-align:left;background-color:#FCF9F0;'>{'<br>'.join(special_notes[bank])}</td>"
html_table_output += "</tr></tbody></table>"

st.markdown(html_table_output, unsafe_allow_html=True)

# ========== PDF出力 ==========
class PDF(FPDF):
    def __init__(self, orientation="L", unit="mm", format="A4"):
        super().__init__(orientation, unit, format)
        self.add_font("Noto", "", FONT_PATH, uni=True)
        self.add_font("Noto", "B", FONT_PATH, uni=True)
        self.set_auto_page_break(auto=True, margin=12)

    def header(self):
        self.set_font("Noto", "B", 22)
        self.cell(0, 15, "住宅ローン提案書", ln=True, align="C")
        self.set_font("Noto", "", 13)
        self.cell(0, 7, f"借入金額：¥{principal:,.0f}", ln=True, align="C")
        self.ln(3)

    def colored_cell(self, w, h, txt, fill, align="C", bold=False):
        self.set_fill_color(*fill)
        self.set_font("Noto", "B" if bold else "", 13)
        self.cell(w, h, txt, align=align, border=1, fill=True)

def pdf_make():
    pdf = PDF()
    pdf.add_page()
    table_cols = [43] * (len(bank_order)+1)
    table_cols[0] = 62
    th = 14

    # ヘッダー
    pdf.set_font("Noto", "B", 13)
    pdf.set_fill_color(242,246,250)
    pdf.cell(table_cols[0], th, "プラン", border=1, align="C", fill=True)
    for b in bank_order:
        pdf.cell(table_cols[1], th, b, border=1, align="C", fill=True)
    pdf.ln()

    # 金利・返済テーブル
    for i, plan in enumerate(plans_order):
        pdf.set_font("Noto", "B", 12)
        pdf.set_fill_color(255,255,255)
        pdf.cell(table_cols[0], th, plan, border=1, align="C", fill=True)
        for col_idx, bank in enumerate(bank_order):
            d = table_rows[i][col_idx]
            minflag = col_idx in highlight_rows[i] and d["monthly"] is not None
            if d["rate"] is None:
                pdf.cell(table_cols[1], th, "", border=1)
            else:
                if minflag:
                    pdf.set_fill_color(255,248,200)
                else:
                    pdf.set_fill_color(255,255,255)
                txt = f"{d['rate']*100:.3f}%\n¥{d['monthly']:,.0f}\n({d['years']}年)"
                pdf.multi_cell(table_cols[1], th/3, txt, border=1, align="C", fill=True, max_line_height=pdf.font_size)
        pdf.ln(th - th/3*2)

        # 一般団信の下に最長50年
        if plan == "一般団信":
            pdf.set_fill_color(249,246,239)
            pdf.cell(table_cols[0], th, "最長50年", border=1, align="C", fill=True)
            for col_idx, bank in enumerate(bank_order):
                d = row_50[col_idx]
                minflag = col_idx in highlight_50 and d["monthly"] is not None
                if d["rate"] is None:
                    pdf.cell(table_cols[1], th, "", border=1)
                else:
                    if minflag:
                        pdf.set_fill_color(255,248,200)
                    else:
                        pdf.set_fill_color(255,255,255)
                    txt = f"{d['rate']*
