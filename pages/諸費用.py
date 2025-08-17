# pages/諸費用明細.py
import os
import re
import tempfile
import streamlit as st
from fpdf import FPDF
from utils import create_pdf_with_fonts  # 日本語フォント登録済みFPDFを取得

A4_W = 210
A4_H = 297

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
option_rows = []
option_fee = number_input_commas("リフォーム・追加工事費（円）", 0, step=10_000)
if option_fee > 0:
    option_rows.append(["リフォーム費用", f"{option_fee:,} 円", "決済時", "任意工事・追加リフォーム等"])
moving_fee = number_input_commas("引越し費用（円）", 150_000, step=10_000)
if moving_fee > 0:
    option_rows.append(["引越し費用", f"{moving_fee:,} 円", "入居時", "距離・荷物量による"])
kaden_fee = number_input_commas("家具家電代（円）", 0, step=10_000)
if kaden_fee > 0:
    option_rows.append(["家具家電代", f"{kaden_fee:,} 円", "入居時", "新生活準備費用"])

cost_rows = []
cost_rows.append(["◆ 登記費用・税金・精算金等", "", "", ""])
cost_rows.extend([
    ["契約書 印紙代", f"{stamp_fee:,} 円", "契約時", "電子契約で削減可能"],
    ["登記費用", f"{regist_fee:,} 円", "決済時", "司法書士報酬＋登録免許税"],
    ["精算金", f"{tax_clear:,} 円", "決済時", "固都税・管理費等（日割り精算）"],
    ["表示登記", f"{display_fee:,} 円", "決済時", "新築戸建の場合必要（目安10万円）"]
])
cost_rows.append(["◆ 金融機関・火災保険", "", "", ""])
cost_rows.extend([
    ["銀行事務手数料", f"{loan_fee:,} 円", "決済時", "借入金額2.2%程度"],
    ["金消契約 印紙税", f"{kinko_stamp:,} 円", "金消契約時", "電子契約は不要・金融機関により必要"],
    ["火災保険", f"{fire_fee:,} 円", "決済時", "5年の火災保険（概算）"],
    ["適合証明書", f"{tekigo_fee:,} 円", "相談", "フラット35の場合 必須"]
])
cost_rows.append(["◆ 仲介会社（TERASS）", "", "", ""])
cost_rows.append([
    "仲介手数料", f"{brokerage:,} 円", "契約時/決済時", "物件価格×3%＋6万＋税"
])
if option_rows:
    cost_rows.append(["◆ 追加工事・引越し", "", "", ""])
    for row in option_rows:
        cost_rows.append(row)

total_expenses = sum(
    int(r[1].replace(' 円','').replace(',',''))
    for r in cost_rows
    if r[1] and ("◆" not in r[0])
)
total = int(property_price + total_expenses)

monthly1 = calc_monthly_payment(property_price + total_expenses, loan_years, loan_rate)
monthly2 = calc_monthly_payment(property_price, loan_years, loan_rate)

default_bikou = (
    "※諸費用は全て目安です。物件・契約形態・条件により変動します。\n"
    "登記費用・火災保険・精算金等も見積取得後確定します。\n"
    "銀行事務手数料は、借入金額＝物件価格で算出しています。"
)
bikou = st.text_area("備考・注釈欄（自由編集）", value=default_bikou, height=80)

my_name = "西山　直樹 / Naoki Nishiyama"
my_company = "TERASS, Inc."
my_address = "〒105-0001 東京都港区虎ノ門二丁目2番1号　住友不動産虎ノ門タワー 13階"
my_tel = "TEL: 090-4399-2480 / FAX: 03-6369-3864"
my_mail = "Email: naoki.nishiyama@terass.com"
my_line = "LINE：naokiwm"

if st.button("PDFダウンロード"):
    # 一時ファイル → バイト読込 → 削除（安全）
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp_path = tmp.name
    try:
        pdf = create_pdf_with_fonts()  # ✅ 日本語フォント登録済み
        pdf.set_left_margin(13)
        pdf.set_top_margin(13)
        pdf.add_page()
        pdf.set_auto_page_break(False)

        # --- 上部 物件名/価格/手付金 ---
        pdf.set_font('NotoSans', 'B', 12)
        if customer_name:
            pdf.cell(0, 8, f"{customer_name} 様", ln=1, align='L')
        pdf.set_font('NotoSans', 'B', 11.5)
        pdf.cell(0, 7, f"物件名：{property_name}", ln=1, align='L')
        pdf.set_font('NotoSans', 'B', 13)
        pdf.cell(0, 8, f"物件価格：{property_price:,} 円", ln=1, align='L')
        pdf.set_font('NotoSans', '', 11)
        pdf.cell(0, 7, f"手付金：{deposit:,} 円（物件価格の5%前後／契約時振込・物件価格に充当）", ln=1, align='L')
        pdf.ln(1)

        # --- 諸費用明細テーブル ---
        headers = ["項目", "金額", "支払時期", "説明"]
        col_w = [46, 34, 33, 77]
        pdf.set_font('NotoSans', 'B', 10)
        pdf.set_fill_color(220, 230, 250)
        for i, h in enumerate(headers):
            pdf.cell(col_w[i], 7, h, 1, 0, 'C', 1)
        pdf.ln(7)
        pdf.set_font('NotoSans', '', 10)
        for row in cost_rows:
            if "◆" in row[0]:
                pdf.set_font('NotoSans', 'B', 10)
                pdf.cell(sum(col_w), 7, row[0], 1, 1, 'L', 0)
                pdf.set_font('NotoSans', '', 10)
            else:
                pdf.cell(col_w[0], 7, row[0], 1, 0, 'L')
                pdf.cell(col_w[1], 7, row[1], 1, 0, 'R')
                pdf.cell(col_w[2], 7, row[2], 1, 0, 'C')
                pdf.cell(col_w[3], 7, row[3], 1, 1, 'L')
        pdf.ln(1)

        # --- 注意書き ---
        pdf.set_font('NotoSans', '', 9.5)
        pdf.set_text_color(80, 80, 80)
        bikou_clean = re.sub(r'。\n', '\n', bikou).strip()
        pdf.multi_cell(0, 6, bikou_clean)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

        # --- 諸費用合計・総合計 ---
        pdf.set_fill_color(220, 240, 255)
        sum_cols = [45, 50, 55, 40]
        pdf.set_font('NotoSans', 'B', 12)
        pdf.cell(sum_cols[0], 9, "諸費用合計", 1, 0, 'C', 1)
        pdf.cell(sum_cols[1], 9, f"{total_expenses:,} 円", 1, 0, 'R', 1)
        pdf.cell(sum_cols[2], 9, "総合計（物件＋諸費用）", 1, 0, 'C', 1)
        pdf.cell(sum_cols[3], 9, f"{total:,} 円", 1, 1, 'R', 1)
        pdf.ln(3)

        # --- 支払例 ---
        pdf.set_font('NotoSans', 'B', 11)
        pdf.cell(0, 8, f"（支払例）※金利{loan_rate:.2f}％／{loan_years}年返済の場合", ln=1, align='L')
        headers2 = ["借入パターン", "借入金額", "月々返済額", "総額（管理費含)"]
        col2_w = [90, 30, 35, 35]
        pdf.set_font('NotoSans', 'B', 10)
        pdf.set_fill_color(220, 240, 255)
        for i, h in enumerate(headers2):
            pdf.cell(col2_w[i], 7, h, 1, 0, 'C', 1)
        pdf.ln(7)
        pdf.set_font('NotoSans', '', 10)
        pdf.cell(col2_w[0], 8, "①物件価格＋諸費用フルローン", 1, 0, 'L')
        pdf.cell(col2_w[1], 8, f"{property_price+total_expenses:,} 円", 1, 0, 'R')
        pdf.cell(col2_w[2], 8, f"{monthly1:,} 円", 1, 0, 'R')
        pdf.set_font('NotoSans', '', 9.5)
        pdf.cell(col2_w[3], 8, f"{(monthly1+kanri_month):,} 円", 1, 1, 'R')
        pdf.set_font('NotoSans', '', 10)
        pdf.cell(col2_w[0], 8, "②物件価格のみ借入", 1, 0, 'L')
        pdf.cell(col2_w[1], 8, f"{property_price:,} 円", 1, 0, 'R')
        pdf.cell(col2_w[2], 8, f"{monthly2:,} 円", 1, 0, 'R')
        pdf.set_font('NotoSans', '', 9.5)
        pdf.cell(col2_w[3], 8, f"{(monthly2+kanri_month):,} 円", 1, 1, 'R')
        pdf.ln(2)

        pdf.set_text_color(90, 90, 90)
        pdf.cell(0, 8, f"管理費・修繕積立金（月額）：{kanri_month:,} 円", ln=1, align='L')
        pdf.set_text_color(0, 0, 0)

        # フッター
        footer_y = A4_H - 49
        pdf.set_y(footer_y)
        pdf.set_font('NotoSans', 'B', 10)
        pdf.cell(0, 6, my_name, ln=1, align='L')
        pdf.set_font('NotoSans', '', 9)
        pdf.cell(0, 6, my_company, ln=1, align='L')
        pdf.cell(0, 6, my_address, ln=1, align='L')
        pdf.cell(0, 6, my_tel, ln=1, align='L')
        pdf.cell(0, 6, my_mail, ln=1, align='L')
        pdf.cell(0, 6, my_line, ln=1, align='L')

        # 出力→読込→DL→削除
        pdf.output(tmp_path)
        with open(tmp_path, "rb") as f:
            st.download_button(label="資金計画書.pdf", data=f.read(),
                               file_name="資金計画書.pdf", mime="application/pdf")
    finally:
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except Exception:
            pass