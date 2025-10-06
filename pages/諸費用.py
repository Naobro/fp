# fp/pages/諸費用.py
# 改訂版：金利を小数第3位まで対応・Supabase保存対応（rateA / rateB含む）

import os, re, io, zipfile, tempfile
from pathlib import Path
import streamlit as st
import requests
from fpdf import FPDF
from client_portal import db_insert_record, db_log_event, now_iso, get_sb

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

# ============ 表示設定 ============
st.set_page_config(page_title="資金計画書（諸費用明細）", layout="centered")
st.title("資金計画書（諸費用明細）")

# ============ フォント準備 ============
def _pick_font_dir() -> Path:
    for d in [
        Path.cwd() / "fonts_runtime",
        Path(tempfile.gettempdir()) / "fonts_runtime",
        Path.home() / ".cache" / "fonts_runtime",
    ]:
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

def _download_and_extract_ttf(zip_url: str, member_suffix: str, save_path: Path):
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

# ============ 関数群 ============
def fmt_jpy(n: int): return f"{n:,} 円"
def number_input_commas(label, value, step=1):
    s = st.text_input(label, f"{value:,}")
    s = re.sub(r"[^\d]", "", s)
    try: return int(s)
    except: return value
def round_deposit(price_yen): return int(round(price_yen*0.05/500_000)*500_000)
def calc_stamp_tax(p):
    if p<=5_000_000: return 5_000
    if p<=10_000_000: return 10_000
    if p<=50_000_000: return 10_000
    if p<=100_000_000: return 30_000
    if p<=500_000_000: return 60_000
    if p<=1_000_000_000: return 160_000
    if p<=5_000_000_000: return 320_000
    return 480_000
def monthly_payment(loan_amount, years, rate):
    n = years*12; r = rate/100/12
    if n<=0: return 0
    if r==0: return int(loan_amount/n)
    return int(loan_amount*r*(1+r)**n/((1+r)**n-1))

# ============ 入力 ============
st.session_state["customer_name"] = st.text_input("お客様名", st.session_state.get("customer_name",""))
st.session_state["property_name"] = st.text_input("物件名", st.session_state.get("property_name",""))

col1,col2,col3 = st.columns(3)
with col1: prop_type = st.selectbox("物件種別", ["マンション","戸建て"], index=0)
with col2: is_new = st.checkbox("新築戸建（表示登記あり）", value=(prop_type=="戸建て"))
with col3: use_flat35 = st.checkbox("フラット35（適合証明）", value=False)

price_man = st.number_input("物件価格（万円）", min_value=100, max_value=200_000, value=5800, step=10)
property_price = price_man*10_000
deposit = number_input_commas("手付金（円）", round_deposit(property_price))
kanri_month = number_input_commas("管理費・修繕積立（月額）", 18_000)
base_rate = st.number_input("基準金利（年%）", min_value=0.0, max_value=5.0, value=0.780, step=0.001, format="%.3f")
base_years = 35

colr1,colr2 = st.columns(2)
with colr1:
    mode = st.radio("登記費用の計算方法", ["固定額","物件価格比例（%）"], index=0, horizontal=True)
if mode=="固定額":
    regist_fee = number_input_commas("登記費用（円）", 400_000)
else:
    with colr2: rate = st.number_input("登記費用（%）", min_value=0.0, max_value=3.0, value=0.5)
    regist_fee = int(property_price*(rate/100))

tax_rate=0.10
brokerage = int((property_price*0.03+60_000)*(1+tax_rate))
stamp_fee = calc_stamp_tax(property_price)
tax_clear = number_input_commas("精算金",100_000)
display_fee = number_input_commas("表示登記",100_000 if (prop_type=="戸建て" and is_new) else 0)

loan_amount_fee_man = st.number_input("借入金額（事務手数料計算用：万円）", value=int(price_man), step=100)
loan_amount_fee = int(loan_amount_fee_man)*10_000
auto_fee = int(loan_amount_fee*0.022)
loan_fee = number_input_commas("銀行事務手数料（円）", auto_fee)
kinko_stamp = number_input_commas("金消契約 印紙税",0)
fire_fee = number_input_commas("火災保険料",200_000)
tekigo_fee = number_input_commas("適合証明書",55_000 if use_flat35 else 0)

# ============ ③④ 入力 ============
st.markdown("#### ③ 入力A（手動）")
colA1,colA2,colA3=st.columns(3)
with colA1:
    loanA_man=st.number_input("借入金額（万円：③）", value=int(price_man), step=10)
    loanA=int(loanA_man)*10_000
with colA2:
    rateA=st.number_input("金利（③）", value=base_rate, step=0.001, format="%.3f")
with colA3:
    yearA=st.number_input("年数（③）", value=35, step=1)

st.markdown("#### ④ 入力B（手動）")
colB1,colB2,colB3=st.columns(3)
with colB1:
    loanB_man=st.number_input("借入金額（万円：④）", value=int(price_man), step=10)
    loanB=int(loanB_man)*10_000
with colB2:
    rateB=st.number_input("金利（④）", value=base_rate, step=0.001, format="%.3f")
with colB3:
    yearB=st.number_input("年数（④）", value=35, step=1)

# ============ 計算 ============
m_full=monthly_payment(property_price+loan_fee,base_years,base_rate)
m_only=monthly_payment(property_price,base_years,base_rate)
mA=monthly_payment(loanA,yearA,rateA)
mB=monthly_payment(loanB,yearB,rateB)
need=int(deposit+stamp_fee+brokerage/2)
total_expenses = int(stamp_fee+regist_fee+tax_clear+display_fee+loan_fee+fire_fee+tekigo_fee+brokerage)
total = property_price + total_expenses

# ============ 保存 ============
if st.button("💾 諸費用データを保存"):
    payload={
        "customer_name":st.session_state["customer_name"],
        "property_name":st.session_state["property_name"],
        "property_price":property_price,
        "deposit":deposit,
        "total_expenses":total_expenses,
        "total":total,
        "monthly_full":m_full,
        "monthly_only":m_only,
        "monthly_A":mA,
        "monthly_B":mB,
        "rateA":rateA,
        "rateB":rateB,
        "saved_at":now_iso(),
    }
    SB.table("fees_detail").upsert({**payload,"client_id":client_id},on_conflict="client_id").execute()
    st.success("保存しました ✅")

# ============ PDF ============
def build_pdf():
    pdf = FPDF(unit="mm", format="A4")
    _register_jp_fonts(pdf)
    pdf.add_page()
    pdf.set_font("IPAexGothic", "B", 12)
    if st.session_state["customer_name"]:
        pdf.cell(0, 8, f"{st.session_state['customer_name']} 様", ln=1)
    pdf.set_font("IPAexGothic", "", 11)
    pdf.cell(0, 7, f"物件名：{st.session_state['property_name']}", ln=1)
    pdf.cell(0, 7, f"物件価格：{fmt_jpy(property_price)}", ln=1)
    pdf.cell(0, 7, f"諸費用合計：{fmt_jpy(total_expenses)}", ln=1)
    pdf.cell(0, 7, f"契約時必要資金：{fmt_jpy(need)}", ln=1)
    pdf.ln(3)

    rows = [
        ["①自己資金0", property_price+total_expenses, m_full],
        ["②諸費用のみ", property_price, m_only],
        [f"③A 金利{rateA:.3f}%／{yearA}年", loanA, mA],
        [f"④B 金利{rateB:.3f}%／{yearB}年", loanB, mB],
    ]
    pdf.set_font("IPAexGothic", "", 10)
    for r in rows:
        pdf.cell(80, 7, r[0], 1)
        pdf.cell(50, 7, fmt_jpy(r[1]), 1, 0, "R")
        pdf.cell(60, 7, fmt_jpy(r[2]), 1, 1, "R")

    out = pdf.output(dest="S")
    return out.encode("latin-1") if isinstance(out, str) else bytes(out)

pdf_bytes = build_pdf()

st.download_button(
    "📄 資金計画書.pdf ダウンロード",
    data=pdf_bytes,
    file_name=f"{st.session_state['property_name']}　諸費用明細.pdf",
    mime="application/pdf",
)
