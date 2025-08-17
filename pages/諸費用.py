# fp/pages/諸費用明細.py

import os
import re
import tempfile
import streamlit as st
from fpdf import FPDF
from pathlib import Path

# ========== A4サイズ定義 ==========
A4_W = 210
A4_H = 297

# ========== 日本語フォント設定 ==========
FONT_DIR = Path("/System/Library/Fonts/Supplemental")
FONT_REGULAR = FONT_DIR / "ヒラギノ明朝 ProN W3.otf"
FONT_BOLD = FONT_DIR / "ヒラギノ角ゴ ProN W6.otf"

def create_pdf() -> FPDF:
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("NotoSans", "", str(FONT_REGULAR), uni=True)
    pdf.add_font("NotoSans", "B", str(FONT_BOLD), uni=True)
    return pdf

# ========== 共通関数 ==========
def number_input_commas(label, value, step=1):
    s = st.text_input(label, f"{value:,}")
    s = re.sub(r'[^\d]', '', s)
    try:
        v = int(s)
    except:
        v = value
    return v

def round_deposit(price):
    base = price * 0.05
    return int(round(base / 500000) * 500000)

def calc_stamp_tax(price):
    if price <= 5_000_000:
        return 5000
    elif price <= 10_000_000:
        return 10000
    elif price <= 50_000_000:
        return 10000
    elif price <= 100_000_000:
        return 30000
    elif price <= 500_000_000:
        return 60000
    elif price <= 1_000_000_000:
        return 160000
    elif price <= 5_000_000_000:
        return 320000
    else:
        return 480000

def calc_monthly_payment(loan_amount, years, annual_rate):
    n = years * 12
    r = annual_rate / 100 / 12
    if r == 0:
        return int(loan_amount / n)
    return int(loan_amount * r * (1 + r) ** n / ((1 + r) ** n - 1))

# ========== Streamlit UI ==========
st.set_page_config(page_title="資金計画書", layout="centered")
st.title("資金計画書")

customer_name = st.text_input("お客様名（例：山田太郎）", "")
property_name = st.text_input("物件名", "")
property_price = number_input_commas("物件価格（円）", 58_000_000, step=100_000)
default_deposit = round_deposit(property_price)
deposit = number_input_commas("手付金（円・物件価格5%/50万円単位で四捨五入）", default_deposit, step=500_000)
kanri_month = number_input_commas("管理費・修繕積立金（月額円）", 18_000, step=1_000)

# ローン条件
col1, col2, col3 = st.columns(3)
with col1:
    loan_amount = number_input_commas("借入金額（円・シミュ用）", property_price, step=100_000)
with col2:
    loan_rate = st.number_input("金利（年%・シミュ用）", min_value=0.0, max_value=5.0, value=0.7)
with col3:
    loan_years = st.number_input("返済期間（年・シミュ用）", min_value=1, max_value=50, value=35)

# 諸費用計算
tax_rate = 0.10
brokerage = int((property_price * 0.03 + 60_000) * (1 + tax_rate))
stamp_fee = calc_stamp_tax(property_price)
regist_fee = number_input_commas("登記費用（円・司法書士報酬＋登録免許税）", 400_000, step=10_000)
tax_clear = number_input_commas("精算金（固都税・管理費等・日割り精算）", 100_000, step=10_000)
display_fee = number_input_commas("表示登記（新築戸建のみ／10万円前後）", 0, step=10_000)
loan_fee = int(loan_amount * 0.022)
kinko_stamp = number_input_commas("金銭消費貸借 印紙税（通常0円）", 0, step=1_000)
fire_fee = number_input_commas("火災保険料（円・5年分概算）", 200_000, step=10_000)
tekigo_fee = number_input_commas("適合証明書（フラット35の場合必須）", 0, step=10_000)

cost_rows = [
    ["契約書 印紙代", f"{stamp_fee:,} 円", "契約時", "電子契約で削減可能"],
    ["登記費用", f"{regist_fee:,} 円", "決済時", "司法書士報酬＋登録免許税"],
    ["精算金", f"{tax_clear:,} 円", "決済時", "固都税・管理費等（日割り精算）"],
    ["表示登記", f"{display_fee:,} 円", "決済時", "新築戸建の場合必要（目安10万円）"],
    ["銀行事務手数料", f"{loan_fee:,} 円", "決済時", "借入金額2.2%程度"],
    ["金消契約 印紙税", f"{kinko_stamp:,} 円", "金消契約時", "電子契約は不要・金融機関により必要"],
    ["火災保険", f"{fire_fee:,} 円", "決済時", "5年の火災保険（概算）"],
    ["適合証明書", f"{tekigo_fee:,} 円", "相談", "フラット35の場合 必須"],
    ["仲介手数料", f"{brokerage:,} 円", "契約時/決済時", "物件価格×3%＋6万＋税"],
]

total_expenses = sum(int(r[1].replace(" 円", "").replace(",", "")) for r in cost_rows)
total = property_price + total_expenses

monthly1 = calc_monthly_payment(property_price + total_expenses, loan_years, loan_rate)

# 備考
default_bikou = (
    "※諸費用は全て目安です。物件・契約形態・条件により変動します。\n"
    "登記費用・火災保険・精算金等も見積取得後確定します。"
)
bikou = st.text_area("備考・注釈欄（自由編集）", value=default_bikou, height=80)

# PDFボタン
if st.button("PDFダウンロード"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp_path = tmp.name
    try:
        pdf = create_pdf()
        pdf.set_font("NotoSans", "B", 14)
        pdf.cell(0, 10, "資金計画書", ln=1, align="C")

        if customer_name:
            pdf.cell(0, 8, f"{customer_name} 様", ln=1, align="L")
        pdf.set_font("NotoSans", "", 12)
        pdf.cell(0, 8, f"物件名: {property_name}", ln=1, align="L")
        pdf.cell(0, 8, f"物件価格: {property_price:,} 円", ln=1, align="L")
        pdf.cell(0, 8, f"手付金: {deposit:,} 円", ln=1, align="L")

        pdf.ln(5)
        pdf.set_font("NotoSans", "B", 12)
        pdf.cell(0, 8, "諸費用明細", ln=1)

        pdf.set_font("NotoSans", "", 11)
        for row in cost_rows:
            pdf.cell(0, 7, f"{row[0]}: {row[1]} ({row[2]}) {row[3]}", ln=1)

        pdf.ln(5)
        pdf.set_font("NotoSans", "B", 12)
        pdf.cell(0, 8, f"諸費用合計: {total_expenses:,} 円", ln=1)
        pdf.cell(0, 8, f"総合計: {total:,} 円", ln=1)

        pdf.ln(5)
        pdf.multi_cell(0, 6, bikou)

        pdf.output(tmp_path)
        with open(tmp_path, "rb") as f:
            st.download_button("📥 ダウンロード", f.read(), file_name="諸費用明細.pdf", mime="application/pdf")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)