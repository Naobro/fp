# fp/pages/諸費用明細.py
# 保存機能＋仲介手数料分割＋銀行事務手数料連動＋PDF出力（完全版）

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

client_id = st.query_params.get("client", "unknown")
saved = load_saved_data(client_id)
if saved:
    for k, v in saved.items():
        st.session_state[k] = v

# ----------------------------
# 画面設定
# ----------------------------
st.set_page_config(page_title="資金計画書（諸費用明細）", layout="centered")
st.title("資金計画書（諸費用明細）")

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
# 共通関数
# ----------------------------
def fmt_jpy(n): return f"{int(n):,} 円"
def number_input_commas(label, value, step=1):
    """カンマ付き整数入力（Noneや空値を安全に処理）"""
    if value is None:
        value = 0
    try:
        s = st.text_input(label, f"{int(value):,}")
    except Exception:
        s = st.text_input(label, "0")
    s = re.sub(r"[^\d]", "", s)
    try:
        return int(s)
    except Exception:
        return int(value)
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

def save_to_state(key, value):
    st.session_state[key] = value
    return value

# ----------------------------
# 入力エリア（基本情報）
# ----------------------------
st.session_state["customer_name"] = st.text_input("お客様名", st.session_state.get("customer_name", ""))
st.session_state["property_name"] = st.text_input("物件名", st.session_state.get("property_name", ""))

col1, col2, col3 = st.columns(3)
with col1:
    prop_type = st.selectbox("物件種別", ["マンション", "戸建て"],
                             index=0 if st.session_state.get("prop_type", "マンション") == "マンション" else 1)
    save_to_state("prop_type", prop_type)
with col2:
    is_new = st.checkbox("新築戸建（表示登記あり）",
                         value=st.session_state.get("is_new", prop_type == "戸建て"))
    save_to_state("is_new", is_new)
with col3:
    use_flat35 = st.checkbox("フラット35（適合証明）",
                             value=st.session_state.get("use_flat35", False))
    save_to_state("use_flat35", use_flat35)

price_man = st.number_input("物件価格（万円）",
                            min_value=100,
                            max_value=200_000,
                            value=st.session_state.get("price_man", 5800),
                            step=10)
save_to_state("price_man", price_man)
property_price = price_man * 10_000

# --- 手付金（物件価格×5%を自動計算＋手動修正可） ---
auto_deposit = round_deposit(price_man * 10_000)
prev_price = st.session_state.get("_prev_price", 0)
manual_flag = st.session_state.get("_deposit_manual", False)

# 自動計算（物件価格変更時のみ再計算）
if (prev_price != price_man) and not manual_flag:
    deposit = auto_deposit
else:
    deposit = st.session_state.get("deposit", auto_deposit)

new_deposit = number_input_commas("手付金（円：物件価格×5%を自動計算）", deposit)

# 手動変更検出
st.session_state["_deposit_manual"] = (new_deposit != auto_deposit)
st.session_state["_prev_price"] = price_man
save_to_state("deposit", new_deposit)

# --- 印紙代（自動計算＋電子契約で0円） ---
elec_contract = st.checkbox("電子契約（印紙代 0円）",
                            value=st.session_state.get("elec_contract", False))
save_to_state("elec_contract", elec_contract)

stamp_fee_auto = 0 if elec_contract else calc_stamp_tax(price_man * 10_000)
stamp_fee = number_input_commas("契約書 印紙代（円：自動計算）",
                                st.session_state.get("stamp_fee", stamp_fee_auto))
save_to_state("stamp_fee", stamp_fee)


# --- 借入金額入力 ---
loan_amount_man = st.number_input(
    "借入金額（万円）",
    min_value=0,
    max_value=200_000,
    value=st.session_state.get("loan_amount_man", int(price_man)),
    step=10
)
save_to_state("loan_amount_man", loan_amount_man)

# --- 銀行事務手数料（借入金額×2.2％を自動計算＋手動修正可） ---
auto_loan_fee = int(loan_amount_man * 10_000 * 0.022)
prev_loan = st.session_state.get("_prev_loan_amount", 0)
manual_fee_flag = st.session_state.get("_loanfee_manual", False)

# 自動更新条件
if (prev_loan != loan_amount_man) and not manual_fee_flag:
    loan_fee = auto_loan_fee
else:
    loan_fee = st.session_state.get("loan_fee", auto_loan_fee)

new_loan_fee = number_input_commas(
    "銀行事務手数料（円：借入金額×2.2% 自動計算）", loan_fee
)

# 手動検出・保存
st.session_state["_loanfee_manual"] = (new_loan_fee != auto_loan_fee)
st.session_state["_prev_loan_amount"] = loan_amount_man
save_to_state("loan_fee", new_loan_fee)
# --- 仲介手数料（物件価格に自動連動＋分割） ---
tax_rate = 0.10
auto_broker_total = int((property_price * 0.03 + 60_000) * (1 + tax_rate))

# 自動算出（契約時分の初期値）
if auto_broker_total >= 2_200_000:
    auto_broker_contract = 1_100_000
elif auto_broker_total >= 1_100_000:
    auto_broker_contract = 550_000
else:
    auto_broker_contract = 330_000

auto_broker_settlement = auto_broker_total - auto_broker_contract

prev_price_broker = st.session_state.get("_prev_price_broker", 0)
manual_broker_flag = st.session_state.get("_broker_manual", False)

# 自動更新条件
if (prev_price_broker != price_man) and not manual_broker_flag:
    broker_total = auto_broker_total
    broker_contract = auto_broker_contract
else:
    broker_total = st.session_state.get("broker_total", auto_broker_total)
    broker_contract = st.session_state.get("broker_contract", auto_broker_contract)

# 入力欄
new_broker_total = number_input_commas("仲介手数料 総額（円）", broker_total)
new_broker_contract = number_input_commas("仲介手数料 契約時（円）", broker_contract)

# 残額自動計算＋安全ロジック
if new_broker_contract > new_broker_total:
    new_broker_contract = new_broker_total
broker_settlement = new_broker_total - new_broker_contract

# 手動検出＋保存
st.session_state["_broker_manual"] = (
    new_broker_total != auto_broker_total or new_broker_contract != auto_broker_contract
)
st.session_state["_prev_price_broker"] = price_man

save_to_state("broker_total", new_broker_total)
save_to_state("broker_contract", new_broker_contract)
save_to_state("broker_settlement", broker_settlement)
# --- 各種費用 ---
regist_fee = number_input_commas("登記費用（円）",
                                 st.session_state.get("regist_fee", 400_000))
fire_fee = number_input_commas("火災保険料（円）",
                               st.session_state.get("fire_fee", 200_000))
tax_clear = number_input_commas("精算金（円）",
                                st.session_state.get("tax_clear", 100_000))
display_fee = number_input_commas("表示登記（円）",
                                  st.session_state.get("display_fee", 110_000 if (prop_type == "戸建て" and is_new) else 0))
tekigo_fee = number_input_commas("適合証明書（円）",
                                 st.session_state.get("tekigo_fee", 55_000 if use_flat35 else 0))
reform_fee = number_input_commas("追加リフォーム費用（円）",
                                 st.session_state.get("reform_fee", 0))
move_fee = number_input_commas("引越し費用（円）",
                               st.session_state.get("move_fee", 120_000))

save_to_state("regist_fee", regist_fee)
save_to_state("fire_fee", fire_fee)
save_to_state("tax_clear", tax_clear)
save_to_state("display_fee", display_fee)
save_to_state("tekigo_fee", tekigo_fee)
save_to_state("reform_fee", reform_fee)
save_to_state("move_fee", move_fee)



# --- 金利パターン ---
st.markdown("#### 借入パターン A / B（手動入力）")
base_rate = st.number_input("基準金利（年%）", value=0.780, step=0.001, format="%.3f")
base_years = 35

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

# --- 月々支払計算 ---
loan_full = property_price + regist_fee + fire_fee + loan_fee
m_full = monthly_payment(loan_full, base_years, base_rate)
m_only = monthly_payment(property_price, base_years, base_rate)
mA = monthly_payment(loanA, yearA, rateA)
mB = monthly_payment(loanB, yearB, rateB)

# --- 契約・決済必要資金 ---
contract_funds = int(deposit + stamp_fee + broker_contract)
settlement_funds = int((property_price - deposit) + regist_fee + tax_clear + broker_settlement)

# --- 諸費用合計 ---
total_expenses = int(
    regist_fee + loan_fee + fire_fee + tax_clear + display_fee +
    tekigo_fee + move_fee + reform_fee + stamp_fee + broker_total
)
total = property_price + total_expenses
# ----------------------------
# PDF 生成
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
    pdf.cell(0, 7, f"手付金：{fmt_jpy(deposit)}（物件価格の5%前後／契約時振込・物件価格に充当）", ln=1)
    pdf.ln(3)

    w = [55, 35, 25, 75]
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
            pdf.cell(w[0], 6, r[0], border=1)
            pdf.cell(w[1], 6, r[1], border=1, align="R")
            pdf.cell(w[2], 6, r[2], border=1, align="C")
            pdf.multi_cell(w[3], 6, r[3], border=1)
        pdf.ln(3)

    draw_table("◆ 登記費用・税金・精算金等", [
        ["契約書 印紙代", fmt_jpy(stamp_fee), "契約時", "電子契約で削減可能"],
        ["登記費用", fmt_jpy(regist_fee), "決済時", "司法書士報酬＋登録免許税"],
        ["精算金", fmt_jpy(tax_clear), "決済時", "固都税・管理費等（日割り精算）"],
        ["表示登記", fmt_jpy(display_fee), "決済時", "新築戸建の場合必要（目安10万円）"],
    ])

    draw_table("◆ 金融機関・火災保険", [
        ["銀行事務手数料", fmt_jpy(loan_fee), "決済時", "借入金額×2.2%で自動算出"],
        ["火災保険", fmt_jpy(fire_fee), "決済時", "5年の火災保険（概算）"],
        ["適合証明書", fmt_jpy(tekigo_fee), "相談", "フラット35の場合 必須"],
    ])

    draw_table("◆ 仲介会社（TERASS）", [
        ["仲介手数料 総額", fmt_jpy(broker_total), "契約＋決済", "物件価格×3%＋6万＋税"],
        ["契約時 仲介手数料", fmt_jpy(broker_contract), "契約時", "物件価格によって自動算出"],
        ["決済時 仲介手数料", fmt_jpy(broker_settlement), "決済時", "総額から契約時分を差引いた残額"],
    ])

    draw_table("◆ 追加工事・引越し", [
        ["追加リフォーム", fmt_jpy(reform_fee), "相談", "内容により異なる"],
        ["引越し費用", fmt_jpy(move_fee), "入居時", "距離・荷物量による"],
    ])

    pdf.set_font("IPAexGothic", "", 9)
    pdf.multi_cell(0, 5,
        "※諸費用は全て目安です。物件・契約形態・条件により変動します。\n"
        "登記費用・火災保険・精算金等も見積取得後に確定します。")
    pdf.ln(3)
    pdf.set_fill_color(235, 240, 255)
    pdf.set_font("IPAexGothic", "B", 11)
    pdf.cell(0, 8, f"諸費用合計：{fmt_jpy(total_expenses)}　総合計：{fmt_jpy(total)}", ln=1, fill=True)
    pdf.cell(0, 8, f"契約時必要資金：{fmt_jpy(contract_funds)}", ln=1, fill=True)
    pdf.cell(0, 8, f"決済時必要資金：{fmt_jpy(settlement_funds)}", ln=1, fill=True)
    pdf.ln(5)

    rows = [
        ["①自己資金0（物件＋諸費用）", property_price + total_expenses, m_full],
        ["②諸費用のみ自己資金", property_price, m_only],
        [f"③A 金利{rateA:.3f}%／{yearA}年", loanA, mA],
        [f"④B 金利{rateB:.3f}%／{yearB}年", loanB, mB],
    ]
    for r in rows:
        pdf.cell(80, 7, r[0], 1)
        pdf.cell(50, 7, fmt_jpy(r[1]), 1, 0, "R")
        pdf.cell(60, 7, fmt_jpy(r[2]), 1, 1, "R")

    out = pdf.output(dest="S")
    return out.encode("latin-1") if isinstance(out, str) else bytes(out)

pdf_bytes = build_pdf()

# ----------------------------
# Supabase保存
# ----------------------------
if st.button("💾 諸費用データを保存"):
    try:
        payload = {
            "client_id": client_id,
            "customer_name": st.session_state["customer_name"],
            "property_name": st.session_state["property_name"],
            "price_man": price_man,
            "property_price": property_price,
            "deposit": deposit,
            "loan_amount": loan_amount,
            "loan_fee": loan_fee,
            "broker_total": broker_total,
            "broker_contract": broker_contract,
            "broker_settlement": broker_settlement,
            "regist_fee": regist_fee,
            "fire_fee": fire_fee,
            "tax_clear": tax_clear,
            "display_fee": display_fee,
            "tekigo_fee": tekigo_fee,
            "move_fee": move_fee,
            "reform_fee": reform_fee,
            "stamp_fee": stamp_fee,
            "contract_funds": contract_funds,
            "settlement_funds": settlement_funds,
            "total_expenses": total_expenses,
            "total": total,
            "monthly_full": m_full,
            "monthly_only": m_only,
            "monthly_A": mA,
            "monthly_B": mB,
            "rateA": rateA,
            "rateB": rateB,
            "saved_at": now_iso(),
        }
        SB.table("fees_detail").upsert(payload, on_conflict="client_id").execute()
        st.success("保存しました ✅")
    except Exception as e:
        st.error(f"保存中にエラー: {e}")

# ----------------------------
# PDFダウンロードボタン
# ----------------------------
st.download_button(
    "📄 諸費用明細PDFをダウンロード",
    data=pdf_bytes,
    file_name=f"{st.session_state['property_name']}　諸費用明細.pdf",
    mime="application/pdf",
)
