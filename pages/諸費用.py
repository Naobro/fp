# fp/pages/諸費用.py
# 改訂版（2025-10-07）
# PDFは添付フォーマット完全準拠版（仲介手数料3分割・契約時/決済時必要資金）
# 借入金額は万円単位入力、金利は小数第3位まで対応

import os, re, io, zipfile, tempfile
from pathlib import Path
import streamlit as st
import requests
from fpdf import FPDF
from client_portal import now_iso, get_sb

SB = get_sb()

# ============ データロード ============
def load_saved_data(client_id: str):
    if not SB:
        return None
    try:
        res = (
            SB.table("fees_detail")
            .select("*")
            .eq("client_id", client_id)
            .order("saved_at", desc=True)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]
    except Exception as e:
        st.warning(f"保存データ読み込み失敗: {e}")
    return None


client_id = st.query_params.get("client", "unknown")
saved = load_saved_data(client_id)
if saved:
    for k, v in saved.items():
        st.session_state[k] = v

# ============ 基本設定 ============
st.set_page_config(page_title="資金計画書（諸費用明細）", layout="centered")
st.title("資金計画書（諸費用明細）")

# ============ フォント ============
def _pick_font_dir() -> Path:
    for d in [
        Path.cwd() / "fonts_runtime",
        Path(tempfile.gettempdir()) / "fonts_runtime",
        Path.home() / ".cache" / "fonts_runtime",
    ]:
        try:
            d.mkdir(parents=True, exist_ok=True)
            t = d / ".wtest"
            t.write_text("ok", encoding="utf-8")
            t.unlink()
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

def _register_fonts(pdf):
    _ensure_fonts()
    pdf.add_font("IPAexGothic", "", str(FONT_GOTHIC_PATH), uni=True)
    pdf.add_font("IPAexGothic", "B", str(FONT_GOTHIC_PATH), uni=True)

# ============ 関数群 ============
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
with col1: prop_type = st.selectbox("物件種別", ["マンション", "戸建て"], index=0)
with col2: is_new = st.checkbox("新築戸建（表示登記あり）", value=(prop_type == "戸建て"))
with col3: use_flat35 = st.checkbox("フラット35（適合証明）", value=False)

# 価格・基礎費用
price_man = st.number_input("物件価格（万円）", min_value=100, max_value=200_000, value=5800, step=10)
property_price = price_man * 10_000
deposit = number_input_commas("手付金（円）", round_deposit(property_price))
kanri_month = number_input_commas("管理費・修繕積立（月額）", 18_000)

# 電子契約
elec_contract = st.checkbox("電子契約（印紙代 0円）", value=False)
stamp_fee = 0 if elec_contract else calc_stamp_tax(property_price)

# 仲介手数料
st.markdown("#### 仲介手数料")
brokerage_total = number_input_commas("仲介手数料（合計・円）", int(property_price * 0.03 + 60_000))
brokerage_contract = number_input_commas("仲介手数料（契約時・円）", int(brokerage_total / 2))
brokerage_settlement = brokerage_total - brokerage_contract

# 登記・火災・銀行
regist_fee = number_input_commas("登記費用（円）", 400_000)
loan_fee = number_input_commas("銀行事務手数料（円）", int(property_price * 0.022))
fire_fee = number_input_commas("火災保険料（円）", 200_000)
tax_clear = number_input_commas("精算金（円）", 100_000)
display_fee = number_input_commas("表示登記（円）", 100_000 if (prop_type == "戸建て" and is_new) else 0)
tekigo_fee = number_input_commas("適合証明書（円）", 55_000 if use_flat35 else 0)

# リフォーム・引越し
option_fee = number_input_commas("リフォーム費用（円）", 0)
move_fee = number_input_commas("引越し費用（円）", 150_000)

# 金利条件
base_rate = st.number_input("基準金利（年%）", value=0.780, step=0.001, format="%.3f")
base_years = 35

# 借入パターン
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

# 計算
loan_full = property_price + regist_fee + fire_fee + loan_fee + brokerage_total
m_full = monthly_payment(loan_full, base_years, base_rate)
mA = monthly_payment(loanA, yearA, rateA)
mB = monthly_payment(loanB, yearB, rateB)

# 契約時・決済時資金
need_contract = deposit + stamp_fee + brokerage_contract
need_settle = property_price - deposit + regist_fee + tax_clear + brokerage_settlement

# ============ PDF ============
def build_pdf():
    pdf = FPDF(unit="mm", format="A4")
    _register_fonts(pdf)
    pdf.add_page()

    pdf.set_font("IPAexGothic", "B", 13)
    pdf.cell(0, 8, f"{st.session_state['customer_name']} 様", ln=1)
    pdf.set_font("IPAexGothic", "", 11)
    pdf.cell(0, 7, f"物件名：{st.session_state['property_name']}", ln=1)
    pdf.cell(0, 7, f"物件価格：{fmt_jpy(property_price)}", ln=1)
    pdf.ln(3)

    headers = ["項目", "金額", "支払時期", "説明"]
    w = [46, 34, 33, 77]
    pdf.set_font("IPAexGothic", "B", 10)
    pdf.set_fill_color(220, 230, 250)
    for i, h in enumerate(headers):
        pdf.cell(w[i], 7, h, 1, 0, "C", 1)
    pdf.ln(7)

    def row(title, amount, when, note, bold=False):
        pdf.set_font("IPAexGothic", "B" if bold else "", 10)
        pdf.cell(w[0], 7, title, 1)
        pdf.cell(w[1], 7, fmt_jpy(amount), 1, 0, "R")
        pdf.cell(w[2], 7, when, 1, 0, "C")
        pdf.cell(w[3], 7, note, 1, 1, "L")

    # ---- 本文 ----
    pdf.set_font("IPAexGothic", "B", 10)
    pdf.cell(sum(w), 7, "◆ 登記費用・税金・精算金等", 1, 1)
    row("契約書 印紙代", stamp_fee, "契約時", "電子契約で削減可")
    row("登記費用", regist_fee, "決済時", "司法書士報酬＋登録免許税")
    row("精算金", tax_clear, "決済時", "固定資産税・管理費日割")
    row("表示登記", display_fee, "決済時", "新築戸建の場合")

    pdf.cell(sum(w), 7, "◆ 金融機関・火災保険", 1, 1)
    row("銀行事務手数料", loan_fee, "決済時", "借入金額×2.2%")
    row("火災保険", fire_fee, "決済時", "5年分概算")
    row("適合証明書", tekigo_fee, "相談", "フラット35の場合必要")

    pdf.cell(sum(w), 7, "◆ 仲介会社（TERASS）", 1, 1)
    row("仲介手数料（合計）", brokerage_total, "契約時/決済時", "3%＋6万＋税")
    row("仲介手数料（契約時）", brokerage_contract, "契約時", "")
    row("仲介手数料（決済時）", brokerage_settlement, "決済時", "")

    if option_fee or move_fee:
        pdf.cell(sum(w), 7, "◆ 追加工事・引越し", 1, 1)
        if option_fee: row("リフォーム費用", option_fee, "決済時", "任意工事")
        if move_fee: row("引越し費用", move_fee, "入居時", "距離による")

    pdf.ln(3)
    pdf.set_font("IPAexGothic", "B", 11)
    pdf.cell(0, 8, f"契約時必要資金：{fmt_jpy(need_contract)}", ln=1)
    pdf.cell(0, 8, f"決済時必要資金：{fmt_jpy(need_settle)}", ln=1)
    pdf.ln(3)

    rows = [
        ["①自己資金0（物件＋諸費用）", loan_full, m_full],
        [f"③パターンA　金利{rateA:.3f}%／{yearA}年", loanA, mA],
        [f"④パターンB　金利{rateB:.3f}%／{yearB}年", loanB, mB],
    ]
    pdf.set_font("IPAexGothic", "B", 10)
    pdf.cell(80, 7, "借入パターン", 1)
    pdf.cell(50, 7, "借入金額", 1)
    pdf.cell(60, 7, "月々返済額", 1, 1)
    pdf.set_font("IPAexGothic", "", 10)
    for r in rows:
        pdf.cell(80, 7, r[0], 1)
        pdf.cell(50, 7, fmt_jpy(r[1]), 1, 0, "R")
        pdf.cell(60, 7, fmt_jpy(r[2]), 1, 1, "R")

    return pdf.output(dest="S").encode("latin-1")

pdf_bytes = build_pdf()

# ============ 出力・保存 ============
if st.button("💾 諸費用データを保存"):
    payload = {
        "customer_name": st.session_state["customer_name"],
        "property_name": st.session_state["property_name"],
        "property_price": property_price,
        "deposit": deposit,
        "total_expenses": regist_fee + fire_fee + loan_fee + brokerage_total + tax_clear + stamp_fee,
        "total": property_price + regist_fee + fire_fee + loan_fee + brokerage_total,
        "monthly_full": m_full,
        "monthly_A": mA,
        "monthly_B": mB,
        "rateA": rateA,
        "rateB": rateB,
        "saved_at": now_iso(),
    }
    SB.table("fees_detail").upsert({**payload, "client_id": client_id}, on_conflict="client_id").execute()
    st.success("保存しました ✅")

st.download_button(
    "📄 資金計画書.pdf ダウンロード",
    data=pdf_bytes,
    file_name=f"{st.session_state['property_name']}　諸費用明細.pdf",
    mime="application/pdf",
)
