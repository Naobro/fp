import os
import re
import io
import zipfile
import tempfile
from pathlib import Path
import streamlit as st
import requests
from fpdf import FPDF
from client_portal import now_iso, get_sb

# ----------------------------
# Supabase接続
# ----------------------------
SB = get_sb()

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

# ----------------------------
# 画面設定
# ----------------------------
st.set_page_config(page_title="資金計画書（諸費用明細）", layout="centered")
st.title("資金計画書（諸費用明細）")

# ----------------------------
# 共通関数
# ----------------------------
def fmt_jpy(n):
    return f"{int(n):,} 円"

def number_input_commas(label, value, key):
    if value is None:
        value = 0
    if key not in st.session_state:
        st.session_state[key] = f"{int(value):,}"
    s = st.text_input(label, key=key)
    s = re.sub(r"[^\d]", "", str(s))
    if s == "":
        return 0
    return int(s)

def round_deposit(price_yen):
    return int(round(price_yen * 0.05 / 500_000) * 500_000)

def calc_stamp_tax(p):
    if p <= 5_000_000:
        return 5_000
    if p <= 10_000_000:
        return 10_000
    if p <= 50_000_000:
        return 10_000
    if p <= 100_000_000:
        return 30_000
    if p <= 500_000_000:
        return 60_000
    if p <= 1_000_000_000:
        return 160_000
    if p <= 5_000_000_000:
        return 320_000
    return 480_000

def monthly_payment(loan, years, rate):
    n = years * 12
    r = rate / 100 / 12
    if r == 0:
        return int(loan / n)
    return int(loan * r * (1 + r) ** n / ((1 + r) ** n - 1))

def round_to_10man(n):
    import math
    return int(math.ceil(n / 100_000.0) * 100_000)

def save_to_state(key, value):
    st.session_state[key] = value
    return value

# ----------------------------
# フォント設定
# ----------------------------
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

# ----------------------------
# Supabaseから保存データを取得・反映
# ----------------------------
client_id = st.query_params.get("client", "unknown")
saved = load_saved_data(client_id)

if saved:
    for k, v in saved.items():
        st.session_state[k] = v

    if "price_man" in saved and saved.get("price_man") is not None:
        st.session_state["_prev_price"] = int(saved["price_man"])

    if "loan_amount_man" in saved and saved.get("loan_amount_man") is not None:
        st.session_state["_prev_loan_amount"] = int(saved["loan_amount_man"])

    if "property_price" in saved and saved.get("property_price") is not None:
        st.session_state["_prev_broker_price"] = int(saved["property_price"])
    elif "price_man" in saved and saved.get("price_man") is not None:
        st.session_state["_prev_broker_price"] = int(saved["price_man"]) * 10_000

# ----------------------------
# 入力エリア（基本情報）
# ----------------------------
st.session_state["customer_name"] = st.text_input(
    "お客様名",
    value=st.session_state.get("customer_name", ""),
    key="input_customer_name",
)
st.session_state["property_name"] = st.text_input(
    "物件名",
    value=st.session_state.get("property_name", ""),
    key="input_property_name",
)

col1, col2, col3 = st.columns(3)
with col1:
    prop_type = st.selectbox(
        "物件種別",
        ["マンション", "戸建て"],
        index=0 if st.session_state.get("prop_type", "マンション") == "マンション" else 1,
        key="input_prop_type",
    )
    save_to_state("prop_type", prop_type)

with col2:
    is_new = st.checkbox(
        "新築戸建（表示登記あり）",
        value=st.session_state.get("is_new", prop_type == "戸建て"),
        key="input_is_new",
    )
    save_to_state("is_new", is_new)

with col3:
    use_flat35 = st.checkbox(
        "フラット35（適合証明）",
        value=st.session_state.get("use_flat35", False),
        key="input_use_flat35",
    )
    save_to_state("use_flat35", use_flat35)

price_man = st.number_input(
    "物件価格（万円）",
    min_value=0,
    max_value=10_000_000,
    value=int(float(st.session_state.get("price_man", 5800) or 5800)),
    step=1,
    format="%d",
    key="input_price_man",
)
price_man = int(price_man)
save_to_state("price_man", price_man)
property_price = int(price_man * 10_000)
save_to_state("property_price", property_price)

# ================================
# 自動計算ブロック
# ================================

# --- 手付金 ---
auto_deposit = int(round(property_price * 0.05 / 500_000) * 500_000)
prev_price = int(st.session_state.get("_prev_price", price_man))
manual_flag = bool(st.session_state.get("_deposit_manual", False))

if (prev_price != price_man) or ("deposit" not in st.session_state):
    deposit_initial = auto_deposit
    st.session_state["_deposit_manual"] = False
    st.session_state["deposit"] = auto_deposit
    st.session_state["input_deposit"] = f"{auto_deposit:,}"
else:
    deposit_initial = int(st.session_state.get("deposit", auto_deposit))

new_deposit = number_input_commas(
    "手付金（円：物件価格×5%自動計算／50万円単位）",
    deposit_initial,
    "input_deposit",
)
st.session_state["_deposit_manual"] = bool(new_deposit != auto_deposit)
st.session_state["_prev_price"] = price_man
deposit = save_to_state("deposit", new_deposit)

# --- 印紙代 ---
elec_contract = st.checkbox(
    "電子契約（印紙代 0円）",
    value=st.session_state.get("elec_contract", False),
    key="input_elec_contract",
)
save_to_state("elec_contract", elec_contract)

stamp_fee_auto = 0 if elec_contract else calc_stamp_tax(property_price)

if "stamp_fee" not in st.session_state:
    st.session_state["stamp_fee"] = stamp_fee_auto
    st.session_state["input_stamp_fee"] = f"{stamp_fee_auto:,}"

stamp_fee = number_input_commas(
    "契約書 印紙代（円：自動計算）",
    st.session_state.get("stamp_fee", stamp_fee_auto),
    "input_stamp_fee",
)
save_to_state("stamp_fee", stamp_fee)

# --- 借入金額 ---
loan_amount_man_raw = st.session_state.get("loan_amount_man", price_man)
if loan_amount_man_raw is None:
    loan_amount_man_raw = price_man

loan_amount_man = st.number_input(
    "借入金額（万円）",
    min_value=0,
    max_value=200_000,
    value=int(loan_amount_man_raw),
    step=10,
    format="%d",
    key="input_loan_amount_man",
)
save_to_state("loan_amount_man", int(loan_amount_man))

loan_amount = int(loan_amount_man * 10_000)
save_to_state("loan_amount", loan_amount)

# --- 銀行事務手数料 ---
auto_loan_fee = int(loan_amount * 0.022)
prev_loan = int(st.session_state.get("_prev_loan_amount", loan_amount_man))
manual_fee_flag = bool(st.session_state.get("_loanfee_manual", False))

if (prev_loan != loan_amount_man) or ("loan_fee" not in st.session_state):
    loan_fee_initial = auto_loan_fee
    st.session_state["_loanfee_manual"] = False
    st.session_state["loan_fee"] = auto_loan_fee
    st.session_state["input_loan_fee"] = f"{auto_loan_fee:,}"
else:
    loan_fee_initial = int(st.session_state.get("loan_fee", auto_loan_fee))

new_loan_fee = number_input_commas(
    "銀行事務手数料（円：借入金額×2.2% 自動計算）",
    loan_fee_initial,
    "input_loan_fee",
)
st.session_state["_loanfee_manual"] = bool(new_loan_fee != auto_loan_fee)
st.session_state["_prev_loan_amount"] = int(loan_amount_man)
loan_fee = int(new_loan_fee)
save_to_state("loan_fee", loan_fee)

# --- 仲介手数料 ---
tax_rate = 0.10
auto_broker_total = int((property_price * 0.03 + 60_000) * (1 + tax_rate))

if auto_broker_total >= 2_200_000:
    auto_broker_contract = 1_100_000
elif auto_broker_total >= 1_100_000:
    auto_broker_contract = 550_000
else:
    auto_broker_contract = 330_000

prev_broker_price = int(st.session_state.get("_prev_broker_price", property_price))
manual_broker_flag = bool(st.session_state.get("_manual_broker", False))

if (prev_broker_price != property_price) or ("broker_total" not in st.session_state) or ("broker_contract" not in st.session_state):
    broker_total_initial = auto_broker_total
    broker_contract_initial = auto_broker_contract
    st.session_state["_manual_broker"] = False
    st.session_state["broker_total"] = auto_broker_total
    st.session_state["broker_contract"] = auto_broker_contract
    st.session_state["input_broker_total"] = f"{auto_broker_total:,}"
    st.session_state["input_broker_contract"] = f"{auto_broker_contract:,}"
else:
    broker_total_initial = int(st.session_state.get("broker_total", auto_broker_total))
    broker_contract_initial = int(st.session_state.get("broker_contract", auto_broker_contract))

new_broker_total = number_input_commas(
    "仲介手数料 総額（円）",
    broker_total_initial,
    "input_broker_total",
)
new_broker_contract = number_input_commas(
    "仲介手数料 契約時（円）",
    broker_contract_initial,
    "input_broker_contract",
)

if new_broker_contract > new_broker_total:
    new_broker_contract = new_broker_total
    st.session_state["input_broker_contract"] = f"{new_broker_contract:,}"

broker_settlement = int(new_broker_total) - int(new_broker_contract)
st.session_state["_manual_broker"] = bool(
    new_broker_total != auto_broker_total or new_broker_contract != auto_broker_contract
)
st.session_state["_prev_broker_price"] = property_price

broker_total = int(new_broker_total)
broker_contract = int(new_broker_contract)
broker_settlement = int(broker_settlement)

save_to_state("broker_total", broker_total)
save_to_state("broker_contract", broker_contract)
save_to_state("broker_settlement", broker_settlement)

# --- その他費用 ---
registration_tax_rate = 0.0015
judicial_fee = 150000
auto_regist_fee = int(property_price * registration_tax_rate + judicial_fee)

regist_fee = number_input_commas(
    "登記費用（円：物件価格×0.15%＋司法書士報酬15万円 自動計算）",
    st.session_state.get("regist_fee", auto_regist_fee),
    "input_regist_fee",
)
fire_fee = number_input_commas(
    "火災保険料（円）",
    st.session_state.get("fire_fee", 200_000),
    "input_fire_fee",
)
tax_clear = number_input_commas(
    "精算金（円）",
    st.session_state.get("tax_clear", 100_000),
    "input_tax_clear",
)
display_fee = number_input_commas(
    "表示登記（円）",
    st.session_state.get("display_fee", 110_000 if (prop_type == "戸建て" and is_new) else 0),
    "input_display_fee",
)
tekigo_fee = number_input_commas(
    "適合証明書（円）",
    st.session_state.get("tekigo_fee", 55_000 if use_flat35 else 0),
    "input_tekigo_fee",
)
reform_fee = number_input_commas(
    "追加リフォーム費用（円）",
    st.session_state.get("reform_fee", 0),
    "input_reform_fee",
)
move_fee = number_input_commas(
    "引越し費用（円）",
    st.session_state.get("move_fee", 120_000),
    "input_move_fee",
)

save_to_state("regist_fee", regist_fee)
save_to_state("fire_fee", fire_fee)
save_to_state("tax_clear", tax_clear)
save_to_state("display_fee", display_fee)
save_to_state("tekigo_fee", tekigo_fee)
save_to_state("reform_fee", reform_fee)
save_to_state("move_fee", move_fee)

# --- 金利パターン ---
st.markdown("#### 借入パターン A / B（手動入力）")

base_rate_default = st.session_state.get("base_rate", 0.590)
if base_rate_default in [None, ""]:
    base_rate_default = 0.590
try:
    base_rate_default = float(base_rate_default)
except:
    base_rate_default = 0.590

base_rate = st.number_input(
    "基準金利（年%）",
    value=base_rate_default,
    step=0.001,
    format="%.3f",
    key="input_base_rate",
)
base_rate = float(base_rate)
save_to_state("base_rate", base_rate)

base_years_default = st.session_state.get("base_years", 35)
if base_years_default in [None, ""]:
    base_years_default = 35
try:
    base_years_default = int(base_years_default)
except:
    try:
        base_years_default = int(float(base_years_default))
    except:
        base_years_default = 35

base_years = base_years_default
save_to_state("base_years", base_years)

colA1, colA2, colA3 = st.columns(3)

with colA1:
    loanA_default = st.session_state.get("loanA_man", price_man)
    if loanA_default in [None, ""]:
        loanA_default = price_man
    try:
        loanA_default = int(loanA_default)
    except:
        try:
            loanA_default = int(float(loanA_default))
        except:
            loanA_default = int(price_man)

    loanA_man = st.number_input(
        "借入金額（万円：A）",
        min_value=0,
        max_value=10_000_000,
        value=loanA_default,
        step=10,
        format="%d",
        key="input_loanA_man",
    )

with colA2:
    rateA_default = st.session_state.get("rateA", base_rate)
    if rateA_default in [None, ""]:
        rateA_default = base_rate
    try:
        rateA_default = float(rateA_default)
    except:
        rateA_default = float(base_rate)

    rateA = st.number_input(
        "金利（A）",
        value=rateA_default,
        step=0.001,
        format="%.3f",
        key="input_rateA",
    )

with colA3:
    yearA_default = st.session_state.get("yearA", base_years)
    if yearA_default in [None, ""]:
        yearA_default = base_years
    try:
        yearA_default = int(yearA_default)
    except:
        try:
            yearA_default = int(float(yearA_default))
        except:
            yearA_default = int(base_years)

    yearA = st.number_input(
        "年数（A）",
        min_value=1,
        max_value=100,
        value=yearA_default,
        step=1,
        format="%d",
        key="input_yearA",
    )

loanA_man = loanA_man if loanA_man is not None else 0
rateA = rateA if rateA is not None else 0.0
yearA = yearA if yearA is not None else 35

loanA = int(loanA_man) * 10_000
rateA = float(rateA)
yearA = int(yearA)
save_to_state("loanA_man", int(loanA_man))
save_to_state("rateA", rateA)
save_to_state("yearA", yearA)

colB1, colB2, colB3 = st.columns(3)

with colB1:
    loanB_default = st.session_state.get("loanB_man", price_man)
    if loanB_default in [None, ""]:
        loanB_default = price_man
    try:
        loanB_default = int(loanB_default)
    except:
        try:
            loanB_default = int(float(loanB_default))
        except:
            loanB_default = int(price_man)

    loanB_man = st.number_input(
        "借入金額（万円：B）",
        min_value=0,
        max_value=10_000_000,
        value=loanB_default,
        step=10,
        format="%d",
        key="input_loanB_man",
    )

with colB2:
    rateB_default = st.session_state.get("rateB", base_rate)
    if rateB_default in [None, ""]:
        rateB_default = base_rate
    try:
        rateB_default = float(rateB_default)
    except:
        rateB_default = float(base_rate)

    rateB = st.number_input(
        "金利（B）",
        value=rateB_default,
        step=0.001,
        format="%.3f",
        key="input_rateB",
    )

with colB3:
    yearB_default = st.session_state.get("yearB", base_years)
    if yearB_default in [None, ""]:
        yearB_default = base_years
    try:
        yearB_default = int(yearB_default)
    except:
        try:
            yearB_default = int(float(yearB_default))
        except:
            yearB_default = int(base_years)

    yearB = st.number_input(
        "年数（B）",
        min_value=1,
        max_value=100,
        value=yearB_default,
        step=1,
        format="%d",
        key="input_yearB",
    )

loanB_man = loanB_man if loanB_man is not None else 0
rateB = rateB if rateB is not None else 0.0
yearB = yearB if yearB is not None else 35

loanB = int(loanB_man) * 10_000
rateB = float(rateB)
yearB = int(yearB)
save_to_state("loanB_man", int(loanB_man))
save_to_state("rateB", rateB)
save_to_state("yearB", yearB)
# --- 月々支払計算 ---
total_expenses = int(
    regist_fee + loan_fee + fire_fee + tax_clear + display_fee +
    tekigo_fee + move_fee + reform_fee + stamp_fee + broker_total
)
total = property_price + total_expenses

loan_full = round_to_10man(total)
m_full = monthly_payment(loan_full, base_years, base_rate)
m_only = monthly_payment(property_price, base_years, base_rate)
mA = monthly_payment(loanA, yearA, rateA)
mB = monthly_payment(loanB, yearB, rateB)

contract_funds = int(deposit + stamp_fee + broker_contract)
settlement_funds = int((property_price - deposit) + regist_fee + tax_clear + broker_settlement + loan_fee)

default_target = int(property_price * 0.07)
target_expenses = st.number_input(
    "目標諸費用（円）",
    min_value=0,
    max_value=100_000_000,
    value=int(st.session_state.get("target_expenses", default_target)),
    step=10_000,
    format="%d",
    key="input_target_expenses",
)
st.session_state["target_expenses"] = int(target_expenses)

st.markdown("### 💰 諸費用の現在値と目標値の差額（リアルタイム）")
st.table({
    "項目": [
        "🎯 目標 諸費用（円）",
        "📌 現在の諸費用（入力合計）",
        "🔻 差額（目標 − 現在）",
    ],
    "金額（円）": [
        f"{target_expenses:,}",
        f"{total_expenses:,}",
        f"{target_expenses - total_expenses:,}",
    ],
})

total = property_price + total_expenses

# ----------------------------
# PDF 生成関数
# ----------------------------
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
    pdf.cell(0, 7, f"手付金：{fmt_jpy(deposit)}（物件価格の5%目安）", ln=1)
    pdf.cell(0, 7, f"借入金額：{fmt_jpy(loan_amount_man * 10_000)}", ln=1)
       pdf.ln(4)

    # --- 決済時 金種テーブル ---
    seller_payment = int((property_price - deposit) + tax_clear)
    settlement_self_funds = int(max(0, seller_payment + loan_fee + broker_settlement - loan_amount))

    pdf.set_font("IPAexGothic", "B", 10)
    pdf.cell(0, 7, "◆ 決済時 金種", ln=1)

    money_w = [55, 35, 100]
    money_headers = ["項目", "金額", "計算式"]
    pdf.set_fill_color(220, 230, 250)

    for h, ww in zip(money_headers, money_w):
        pdf.cell(ww, 7, h, 1, 0, "C", 1)
    pdf.ln(7)

    pdf.set_font("IPAexGothic", "", 9)

    money_rows = [
        ["借入金額", f"{int(loan_amount_man):,}万円", f"{fmt_jpy(loan_amount)}"],
        ["売主支払額", fmt_jpy(seller_payment), f"残代金{fmt_jpy(property_price - deposit)}＋精算金{fmt_jpy(tax_clear)}"],
        ["住宅ローン手数料", fmt_jpy(loan_fee), ""],
        ["仲介手数料 決済時金額", fmt_jpy(broker_settlement), ""],
        ["決済時必要自己資金", fmt_jpy(settlement_self_funds), f"売主支払額{fmt_jpy(seller_payment)}＋住宅ローン手数料{fmt_jpy(loan_fee)}＋仲介手数料決済時{fmt_jpy(broker_settlement)}－借入金額{fmt_jpy(loan_amount)}"],
    ]

    for r in money_rows:
        x_row = pdf.get_x()
        y_row = pdf.get_y()

        formula_width = money_w[2]
        formula_text = r[2]
        lines = max(1, int(pdf.get_string_width(formula_text) / (formula_width - 2)) + 1) if formula_text else 1
        row_h = max(7, 6 * lines)

        pdf.rect(x_row, y_row, money_w[0], row_h)
        pdf.rect(x_row + money_w[0], y_row, money_w[1], row_h)
        pdf.rect(x_row + money_w[0] + money_w[1], y_row, money_w[2], row_h)

        pdf.set_xy(x_row, y_row)
        pdf.multi_cell(money_w[0], 6, r[0], border=0)

        pdf.set_xy(x_row + money_w[0], y_row)
        pdf.cell(money_w[1], row_h, r[1], border=0, align="R")

        pdf.set_xy(x_row + money_w[0] + money_w[1], y_row)
        pdf.multi_cell(money_w[2], 6, r[2], border=0)

        pdf.set_xy(x_row, y_row + row_h)

    pdf.ln(4)

    # --- テーブル設定（A4幅内に収まるサイズ） ---

    pdf.set_fill_color(235, 240, 255)
    pdf.set_font("IPAexGothic", "B", 11)

    x_start = pdf.get_x()
    y_start = pdf.get_y()
    box_width = 190
    line_height = 8
    total_height = line_height * 3

    pdf.rect(x_start, y_start, box_width, total_height, style="DF")
    pdf.set_xy(x_start, y_start)
    pdf.cell(
        box_width,
        8,
        f"諸費用合計：{fmt_jpy(total_expenses)}　総合計：{fmt_jpy(total)}　自己資金差額：{fmt_jpy(max(0, total - (loan_amount_man * 10_000)))}",
        border=0,
        ln=1,
        fill=1,
    )
    pdf.set_x(x_start)
    pdf.cell(box_width, 8, f"契約時必要資金：{fmt_jpy(contract_funds)}", border=0, ln=1, fill=1)
    pdf.set_x(x_start)
    pdf.cell(
        box_width,
        8,
        f"決済時必要資金：{fmt_jpy(settlement_funds)}　※（追加リフォーム・火災保険・引っ越し費用除く）",
        border=0,
        ln=1,
        fill=1,
    )
    pdf.ln(4)

    w = [60, 40, 25, 65]
    headers = ["項目", "金額", "支払時期", "説明"]

    def draw_table(title, rows):
        pdf.set_font("IPAexGothic", "B", 10)
        pdf.cell(0, 7, title, ln=1)
        pdf.set_fill_color(220, 230, 250)
        for h, ww in zip(headers, w):
            pdf.cell(ww, 7, h, 1, 0, "C", 1)
        pdf.ln(7)

        pdf.set_font("IPAexGothic", "", 9)
        for r in rows:
            x_row = pdf.get_x()
            y_row = pdf.get_y()

            desc_width = w[3]
            desc_text = r[3]
            lines = max(
                1,
                int(pdf.get_string_width(desc_text) / (desc_width - 2)) + 1
            )
            row_h = max(6, 6 * lines)

            pdf.rect(x_row, y_row, w[0], row_h)
            pdf.rect(x_row + w[0], y_row, w[1], row_h)
            pdf.rect(x_row + w[0] + w[1], y_row, w[2], row_h)
            pdf.rect(x_row + w[0] + w[1] + w[2], y_row, w[3], row_h)

            pdf.set_xy(x_row, y_row)
            pdf.multi_cell(w[0], 6, r[0], border=0)
            pdf.set_xy(x_row + w[0], y_row)
            pdf.cell(w[1], row_h, r[1], border=0, align="R")
            pdf.set_xy(x_row + w[0] + w[1], y_row)
            pdf.cell(w[2], row_h, r[2], border=0, align="C")
            pdf.set_xy(x_row + w[0] + w[1] + w[2], y_row)
            pdf.multi_cell(w[3], 6, r[3], border=0)

            pdf.set_xy(x_row, y_row + row_h)

        pdf.ln(3)

    draw_table("◆ 登記費用・税金・精算金等", [
        ["契約書 印紙代", fmt_jpy(stamp_fee), "契約時", "電子契約なら0円"],
        ["登記費用", fmt_jpy(regist_fee), "決済時", "司法書士報酬＋登録免許税"],
        ["精算金", fmt_jpy(tax_clear), "決済時", "固都税・管理費の日割精算"],
        ["表示登記", fmt_jpy(display_fee), "決済時", "新築戸建のみ必要（約10万円）"],
    ])

    draw_table("◆ 金融機関・火災保険", [
        ["銀行事務手数料", fmt_jpy(new_loan_fee), "決済時", "借入金額×2.2%で自動算出"],
        ["火災保険", fmt_jpy(fire_fee), "決済時", "5年分の概算"],
        ["適合証明書", fmt_jpy(tekigo_fee), "相談", "フラット35利用時に必要"],
    ])

    draw_table("◆ 仲介会社（TERASS）", [
        ["仲介手数料 総額", fmt_jpy(new_broker_total), "契約＋決済", "物件価格×3%＋6万＋税"],
        ["契約時 仲介手数料", fmt_jpy(new_broker_contract), "契約時", "契約時 半金"],
        ["決済時 仲介手数料", fmt_jpy(broker_settlement), "決済時", "残額分"],
    ])

    draw_table("◆ 追加工事・引越し", [
        ["追加リフォーム", fmt_jpy(reform_fee), "相談", "内容により異なる"],
        ["引越し費用", fmt_jpy(move_fee), "入居時", "距離・荷物量による目安"],
    ])

    pdf.set_font("IPAexGothic", "", 9)
    pdf.multi_cell(
        0,
        5,
        "※諸費用は概算です。物件・契約内容により増減します。\n"
        "登記費用・保険料・精算金などは見積確定後に決定します。"
    )
    pdf.ln(2)

    pdf.set_font("IPAexGothic", "B", 10)
    pdf.cell(0, 6, "◆ 借入パターン比較", ln=1)
    pdf.cell(90, 7, "借入パターン", 1, 0, "C")
    pdf.cell(50, 7, "借入金額", 1, 0, "C")
    pdf.cell(50, 7, "支払い合計", 1, 1, "C")

    rows = [
        ["①自己資金0（物件＋諸費用）", loan_full, m_full],
        ["②諸費用のみ自己資金", round_to_10man(property_price), m_only],
        [f"③A 金利{rateA:.3f}%／{yearA}年", round_to_10man(loanA), mA],
        [f"④B 金利{rateB:.3f}%／{yearB}年", round_to_10man(loanB), mB],
    ]

    pdf.set_font("IPAexGothic", "", 9)
    for r in rows:
        pdf.cell(90, 7, r[0], 1)
        pdf.cell(50, 7, fmt_jpy(r[1]), 1, 0, "R")
        pdf.cell(50, 7, fmt_jpy(r[2]), 1, 1, "R")

    out = pdf.output(dest="S")
    return out.encode("latin-1") if isinstance(out, str) else bytes(out)
# ----------------------------
# Supabase保存
# ----------------------------
if st.button("💾 諸費用データを保存"):
    try:
        payload = {
            "client_id": client_id,
            "customer_name": st.session_state.get("customer_name", ""),
            "property_name": st.session_state.get("property_name", ""),
            "prop_type": st.session_state.get("prop_type", "マンション"),
            "is_new": st.session_state.get("is_new", False),
            "use_flat35": st.session_state.get("use_flat35", False),
            "elec_contract": st.session_state.get("elec_contract", False),

            "price_man": int(price_man),
            "property_price": int(property_price),
            "deposit": int(deposit),
            "loan_amount_man": int(loan_amount_man),
            "loan_amount": int(loan_amount),
            "loan_fee": int(new_loan_fee),
            "broker_total": int(new_broker_total),
            "broker_contract": int(new_broker_contract),
            "broker_settlement": int(broker_settlement),
            "regist_fee": int(regist_fee),
            "fire_fee": int(fire_fee),
            "tax_clear": int(tax_clear),
            "display_fee": int(display_fee),
            "tekigo_fee": int(tekigo_fee),
            "move_fee": int(move_fee),
            "reform_fee": int(reform_fee),
            "stamp_fee": int(stamp_fee),

            "_deposit_manual": bool(st.session_state.get("_deposit_manual", False)),
            "_loanfee_manual": bool(st.session_state.get("_loanfee_manual", False)),
            "_manual_broker": bool(st.session_state.get("_manual_broker", False)),

            "contract_funds": int(contract_funds),
            "settlement_funds": int(settlement_funds),
            "total_expenses": int(total_expenses),
            "total": int(total),

            "monthly_full": int(m_full),
            "monthly_only": int(m_only),
            "monthly_A": int(mA),
            "monthly_B": int(mB),
            "rateA": float(rateA),
            "rateB": float(rateB),
            "yearA": int(yearA),
            "yearB": int(yearB),
            "loanA_man": int(loanA_man),
            "loanB_man": int(loanB_man),
            "saved_at": now_iso(),
        }

        SB.table("fees_detail").upsert(payload, on_conflict="client_id").execute()
        st.success("保存しました ✅")
    except Exception as e:
        st.error(f"保存中にエラー: {e}")

# ----------------------------
# PDF生成
# ----------------------------
try:
    pdf_bytes = build_pdf()
except Exception as e:
    st.error(f"PDF生成エラー: {e}")
    pdf_bytes = b""

# ----------------------------
# PDFダウンロードボタン
# ----------------------------
if pdf_bytes:
    st.download_button(
        "📄 諸費用明細PDFをダウンロード",
        data=pdf_bytes,
        file_name=f"{st.session_state.get('property_name', '資金計画書')}　諸費用明細.pdf",
        mime="application/pdf",
    )
else:
    st.warning("⚠️ PDFを生成できませんでした。")
