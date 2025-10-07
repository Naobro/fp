# fp/pages/諸費用明細.py
# 日本語PDF対応：IPAexフォント自動DL登録＋手付金5%自動＋借入金額×2.2%自動＋PDF完全出力版

import os, re, io, zipfile, tempfile
from pathlib import Path
import streamlit as st
import requests
from fpdf import FPDF

# ============ 表示設定 ============
st.set_page_config(page_title="資金計画書（諸費用明細）", layout="centered")
st.title("資金計画書（諸費用明細）")

# ============ フォント設定 ============
def _pick_font_dir() -> Path:
    for d in [Path.cwd() / "fonts_runtime",
              Path(tempfile.gettempdir()) / "fonts_runtime",
              Path.home() / ".cache" / "fonts_runtime"]:
        try:
            d.mkdir(parents=True, exist_ok=True)
            (d / ".wtest").write_text("ok", encoding="utf-8")
            (d / ".wtest").unlink()
            return d
        except Exception:
            continue
    return Path(tempfile.mkdtemp(prefix="fonts_runtime_"))

FONT_DIR = _pick_font_dir()
IPAEX_G_ZIP = "https://moji.or.jp/wp-content/ipafont/IPAexfont/ipaexg00401.zip"
IPAEX_M_ZIP = "https://moji.or.jp/wp-content/ipafont/IPAexfont/ipaexm00401.zip"
FONT_GOTHIC_PATH = FONT_DIR / "IPAexGothic.ttf"
FONT_MINCHO_PATH = FONT_DIR / "IPAexMincho.ttf"

def _download_and_extract_ttf(zip_url, member_suffix, save_path):
    resp = requests.get(zip_url, timeout=30)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        ttf_members = [n for n in zf.namelist() if n.lower().endswith(member_suffix)]
        with zf.open(ttf_members[0]) as src, open(save_path, "wb") as dst:
            dst.write(src.read())

def _ensure_fonts():
    if not FONT_GOTHIC_PATH.exists():
        _download_and_extract_ttf(IPAEX_G_ZIP, "ipaexg.ttf", FONT_GOTHIC_PATH)
    if not FONT_MINCHO_PATH.exists():
        _download_and_extract_ttf(IPAEX_M_ZIP, "ipaexm.ttf", FONT_MINCHO_PATH)

def _register_jp_fonts(pdf: FPDF):
    _ensure_fonts()
    pdf.add_font("IPAexGothic", "", str(FONT_GOTHIC_PATH), uni=True)
    pdf.add_font("IPAexGothic", "B", str(FONT_GOTHIC_PATH), uni=True)
    pdf.add_font("IPAexMincho", "", str(FONT_MINCHO_PATH), uni=True)
    pdf.add_font("IPAexMincho", "B", str(FONT_MINCHO_PATH), uni=True)

# ============ ユーティリティ ============
def fmt_jpy(n): return f"{int(n):,} 円"
def number_input_commas(label, value, step=1):
    s = st.text_input(label, f"{value:,}")
    s = re.sub(r"[^\d]", "", s)
    try: return int(s)
    except: return value
def round_deposit(price_yen): return int(round(price_yen * 0.05 / 500_000) * 500_000)
def calc_stamp_tax(p):
    if p <= 5_000_000: return 5_000
    if p <= 10_000_000: return 10_000
    if p <= 50_000_000: return 10_000
    if p <= 100_000_000: return 30_000
    if p <= 500_000_000: return 60_000
    if p <= 1_000_000_000: return 160_000
    if p <= 5_000_000_000: return 320_000
    return 480_000
def monthly_payment(loan, years, rate):
    n = years * 12
    r = rate / 100 / 12
    if r == 0: return int(loan / n)
    return int(loan * r * (1 + r) ** n / ((1 + r) ** n - 1))

# ============ 入力エリア ============
st.session_state["customer_name"] = st.text_input("お客様名", st.session_state.get("customer_name", ""))
st.session_state["property_name"] = st.text_input("物件名", st.session_state.get("property_name", ""))

col1, col2, col3 = st.columns(3)
with col1:
    prop_type = st.selectbox("物件種別", ["マンション", "戸建て"], index=0)
with col2:
    is_new = st.checkbox("新築戸建（表示登記あり）", value=(prop_type == "戸建て"))
with col3:
    use_flat35 = st.checkbox("フラット35（適合証明）", value=False)

# 物件価格（万円→円）
price_man = st.number_input("物件価格（万円）", min_value=100, max_value=200_000, value=5800, step=10)
property_price = price_man * 10_000

# 手付金：物件価格×5%を自動計算
deposit = number_input_commas("手付金（円・物件価格の5%自動計算）", round_deposit(property_price))
st.session_state["deposit"] = deposit

# 管理費
kanri_month = number_input_commas("管理費・修繕積立（月額）", 18_000)

# 電子契約チェック
elec_contract = st.checkbox("電子契約（印紙代 0円）", value=False)
stamp_fee = 0 if elec_contract else calc_stamp_tax(property_price)

# 借入金額入力
loan_amount_man = st.number_input("借入金額（万円）", min_value=0, max_value=200_000, value=int(price_man), step=10)
loan_amount = loan_amount_man * 10_000

# 銀行事務手数料：借入金額×2.2%
loan_fee_auto = int(loan_amount * 0.022)
loan_fee = number_input_commas("銀行事務手数料（円：借入金×2.2%自動）", loan_fee_auto)

# 火災保険・登記費用等
regist_fee = number_input_commas("登記費用（円）", 400_000)
fire_fee = number_input_commas("火災保険料（円）", 200_000)
tax_clear = number_input_commas("精算金（円）", 100_000)
display_fee = number_input_commas("表示登記（円）", 110_000 if (prop_type == "戸建て" and is_new) else 0)
tekigo_fee = number_input_commas("適合証明書（円）", 55_000 if use_flat35 else 0)
reform_fee = number_input_commas("追加リフォーム費用（円）", 0)
move_fee = number_input_commas("引越し費用（円）", 120_000)

# 仲介手数料計算
brokerage_total = int((property_price * 0.03 + 60_000) * 1.1)
if brokerage_total >= 2_200_000:
    auto_contract = 1_100_000
elif brokerage_total >= 1_100_000:
    auto_contract = 550_000
else:
    auto_contract = 330_000
brokerage_contract = st.number_input("仲介手数料（契約時・円）", min_value=0, max_value=brokerage_total, value=auto_contract, step=10_000)
brokerage_settlement = brokerage_total if brokerage_contract == 0 else brokerage_total - brokerage_contract

# 資金計算
contract_funds = int(deposit + stamp_fee + brokerage_contract)
settlement_funds = int((property_price - deposit) + regist_fee + tax_clear + brokerage_settlement)
total_expenses = int(regist_fee + loan_fee + fire_fee + tax_clear + display_fee +
                     tekigo_fee + brokerage_total + move_fee + reform_fee + stamp_fee)
total = property_price + total_expenses

# 基準金利・借入パターン
base_rate = st.number_input("基準金利（年%）", value=0.780, step=0.001, format="%.3f")
base_years = 35
st.markdown("#### 借入パターン A / B（手動入力）")
colA1, colA2, colA3 = st.columns(3)
with colA1: loanA_man = st.number_input("借入金額（万円：A）", value=int(price_man), step=10)
with colA2: rateA = st.number_input("金利（A）", value=base_rate, step=0.001, format="%.3f")
with colA3: yearA = st.number_input("年数（A）", value=35, step=1)
loanA = loanA_man * 10_000
colB1, colB2, colB3 = st.columns(3)
with colB1: loanB_man = st.number_input("借入金額（万円：B）", value=int(price_man), step=10)
with colB2: rateB = st.number_input("金利（B）", value=base_rate, step=0.001, format="%.3f")
with colB3: yearB = st.number_input("年数（B）", value=35, step=1)
loanB = loanB_man * 10_000

m_full = monthly_payment(property_price + total_expenses, base_years, base_rate)
m_only = monthly_payment(property_price, base_years, base_rate)
mA = monthly_payment(loanA, yearA, rateA)
mB = monthly_payment(loanB, yearB, rateB)

# ============ PDF 生成 ============
def build_pdf():
    pdf = FPDF(unit="mm", format="A4")
    _register_jp_fonts(pdf)
    pdf.add_page()
    pdf.set_font("IPAexGothic", "B", 12)
    pdf.cell(0, 8, f"{st.session_state['customer_name']} 様", ln=1)
    pdf.set_font("IPAexGothic", "", 11)
    pdf.cell(0, 7, f"物件名：{st.session_state['property_name']}", ln=1)
    pdf.cell(0, 7, f"物件価格：{fmt_jpy(property_price)}", ln=1)
    pdf.cell(0, 7, f"手付金：{fmt_jpy(deposit)}（5%前後）", ln=1)
    pdf.ln(3)

    w = [55, 35, 25, 75]
    headers = ["項目", "金額", "支払時期", "説明"]
    pdf.set_font("IPAexGothic", "B", 10)
    pdf.set_fill_color(220, 230, 250)
    for h, ww in zip(headers, w): pdf.cell(ww, 7, h, 1, 0, "C", 1)
    pdf.ln(7)
    pdf.set_font("IPAexGothic", "", 9)

    def row(title, value, timing, desc):
        pdf.cell(w[0], 6, title, 1)
        pdf.cell(w[1], 6, fmt_jpy(value), 1, 0, "R")
        pdf.cell(w[2], 6, timing, 1, 0, "C")
        pdf.multi_cell(w[3], 6, desc, 1)

    row("契約書 印紙代", stamp_fee, "契約時", "電子契約で削減可能")
    row("登記費用", regist_fee, "決済時", "司法書士報酬＋登録免許税")
    row("精算金", tax_clear, "決済時", "固都税・管理費等（日割り精算）")
    row("銀行事務手数料", loan_fee, "決済時", "借入金額×2.2％")
    row("火災保険", fire_fee, "決済時", "5年契約目安")
    row("適合証明書", tekigo_fee, "相談", "フラット35利用時に必要")
    row("仲介手数料（合計）", brokerage_total, "契約時/決済時", "3％＋6万＋税")
    row("契約時", brokerage_contract, "契約時", "手付金と同時入金")
    row("決済時", brokerage_settlement, "決済時", "残金決済時支払い")
    row("引越し費用", move_fee, "入居時", "距離・荷物量による")
    row("追加リフォーム費用", reform_fee, "相談", "内容により異なる")

    pdf.ln(3)
    pdf.set_font("IPAexGothic", "", 9)
    pdf.multi_cell(0, 5, "※諸費用は全て目安です。登記費用・火災保険・精算金等も見積取得後に確定します。")
    pdf.ln(2)

    pdf.set_fill_color(235, 240, 255)
    pdf.set_font("IPAexGothic", "B", 11)
    pdf.cell(0, 8, f"諸費用合計：{fmt_jpy(total_expenses)}　総合計（物件＋諸費用）：{fmt_jpy(total)}", ln=1, fill=True)
    pdf.cell(0, 8, f"契約時必要資金（手付金＋印紙代＋仲介半金）：{fmt_jpy(contract_funds)}", ln=1, fill=True)
    pdf.cell(0, 8, f"決済時必要資金（残代金＋精算金＋登記費用＋手数料残金）：{fmt_jpy(settlement_funds)}", ln=1, fill=True)
    pdf.ln(4)

    pdf.set_font("IPAexGothic", "B", 10)
    pdf.cell(0, 7, "（支払例）①②は基準金利、③④は手動条件", ln=1)
    pdf.set_font("IPAexGothic", "", 10)
    rows = [
        ["①自己資金0（物件＋諸費用）", property_price + total_expenses, m_full],
        ["②諸費用のみ自己資金（物件のみ）", property_price, m_only],
        [f"③パターンA 金利{rateA:.3f}%／{yearA}年", loanA, mA],
        [f"④パターンB 金利{rateB:.3f}%／{yearB}年", loanB, mB],
    ]
    for r in rows:
        pdf.cell(80, 7, r[0], 1)
        pdf.cell(50, 7, fmt_jpy(r[1]), 1, 0, "R")
        pdf.cell(60, 7, fmt_jpy(r[2]), 1, 1, "R")

    out = pdf.output(dest="S")
    return out.encode("latin-1") if isinstance(out, str) else bytes(out)

# PDF 出力ボタン
pdf_bytes = build_pdf()
st.download_button("📄 資金計画書.pdf ダウンロード",
                   data=pdf_bytes,
                   file_name=f"{st.session_state['property_name']}　諸費用明細.pdf",
                   mime="application/pdf")
