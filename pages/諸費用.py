# fp/pages/諸費用.py
# 改訂版（2025-10-09）
# 完全業務用フルコード（借入金額連動・仲介料自動判定・Supabase保存・PDF整形）

import os, re, io, zipfile, tempfile
from pathlib import Path
import streamlit as st
import requests
from fpdf import FPDF
from client_portal import now_iso, get_sb

# ==========================
# Supabase 接続
# ==========================
SB = get_sb()

# ==========================
# データロード関数
# ==========================
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


# ==========================
# 初期設定
# ==========================
st.set_page_config(page_title="資金計画書（諸費用明細）", layout="centered")
st.title("資金計画書（諸費用明細）")

client_id = st.query_params.get("client", "unknown")
saved = load_saved_data(client_id)
if saved:
    for k, v in saved.items():
        st.session_state[k] = v


# ==========================
# フォントセットアップ
# ==========================
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
    pdf.add_font("IPAexMincho", "", str(FONT_MINCHO_PATH), uni=True)
    pdf.add_font("IPAexMincho", "B", str(FONT_MINCHO_PATH), uni=True)


# ==========================
# 共通関数群
# ==========================
def fmt_jpy(n): return f"{int(n):,} 円"

def number_input_commas(label, value, step=1):
    s = st.text_input(label, f"{value:,}")
    s = re.sub(r"[^\d]", "", s)
    try:
        return int(s)
    except:
        return value

def round_deposit(price_yen):
    return int(round(price_yen * 0.05 / 500_000) * 500_000)

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


# ==========================
# 入力フォーム開始
# ==========================
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

# ==========================
# 物件価格・借入金額
# ==========================
price_man = st.number_input("物件価格（万円）", min_value=100, max_value=200_000,
                            value=st.session_state.get("price_man", 5800), step=10)
save_to_state("price_man", price_man)
property_price = price_man * 10_000

deposit = number_input_commas("手付金（円）",
                              st.session_state.get("deposit", round_deposit(property_price)))
save_to_state("deposit", deposit)

loan_amount_man = st.number_input("借入金額（万円）",
                                  min_value=0, max_value=200_000,
                                  value=st.session_state.get("loan_amount_man", int(price_man)), step=10)
save_to_state("loan_amount_man", loan_amount_man)
loan_amount = loan_amount_man * 10_000
save_to_state("loan_amount", loan_amount)

# ==========================
# 印紙税・銀行事務手数料（自動連動）
# ==========================
elec_contract = st.checkbox("電子契約（印紙代 0円）",
                            value=st.session_state.get("elec_contract", False))
save_to_state("elec_contract", elec_contract)
stamp_fee = 0 if elec_contract else calc_stamp_tax(property_price)
save_to_state("stamp_fee", stamp_fee)

loan_fee_auto = int(loan_amount * 0.022)
loan_fee = number_input_commas("銀行事務手数料（円）",
                               st.session_state.get("loan_fee", loan_fee_auto))
save_to_state("loan_fee", loan_fee)

# ==========================
# その他費用入力
# ==========================
regist_fee = number_input_commas("登記費用（円）", st.session_state.get("regist_fee", 400_000))
fire_fee = number_input_commas("火災保険料（円）", st.session_state.get("fire_fee", 200_000))
tax_clear = number_input_commas("精算金（円）", st.session_state.get("tax_clear", 100_000))
display_fee = number_input_commas("表示登記（円）",
                                  st.session_state.get("display_fee", 110_000 if (prop_type == "戸建て" and is_new) else 0))
tekigo_fee = number_input_commas("適合証明書（円）",
                                 st.session_state.get("tekigo_fee", 55_000 if use_flat35 else 0))
reform_fee = number_input_commas("追加リフォーム費用（円）", st.session_state.get("reform_fee", 0))
move_fee = number_input_commas("引越し費用（円）", st.session_state.get("move_fee", 120_000))

for k, v in [
    ("regist_fee", regist_fee),
    ("fire_fee", fire_fee),
    ("tax_clear", tax_clear),
    ("display_fee", display_fee),
    ("tekigo_fee", tekigo_fee),
    ("reform_fee", reform_fee),
    ("move_fee", move_fee),
]:
    save_to_state(k, v)

# ==========================
# 仲介手数料：自動判定
# ==========================
brokerage_total = int((property_price * 0.03 + 60_000) * 1.1)
save_to_state("brokerage_total", brokerage_total)

if brokerage_total >= 2_200_000:
    auto_contract = 1_100_000
elif brokerage_total >= 1_100_000:
    auto_contract = 550_000
else:
    auto_contract = 330_000

brokerage_contract = st.number_input("仲介手数料（契約時・円）",
                                     min_value=0, max_value=brokerage_total,
                                     value=auto_contract, step=10_000)
if brokerage_contract == 0:
    brokerage_settlement = brokerage_total
else:
    brokerage_settlement = brokerage_total - brokerage_contract

st.markdown("#### 仲介手数料（自動判定）")
colb1, colb2, colb3 = st.columns(3)
with colb1: st.number_input("合計", value=brokerage_total, disabled=True)
with colb2: st.number_input("契約時", value=brokerage_contract, disabled=True)
with colb3: st.number_input("決済時", value=brokerage_settlement, disabled=True)

# ==========================
# 契約時／決済時必要資金
# ==========================
contract_funds = int(deposit + stamp_fee + brokerage_contract)
settlement_funds = int((property_price - deposit) + regist_fee + tax_clear + brokerage_settlement)

# ==========================
# 諸費用合計・総合計
# ==========================
total_expenses = int(regist_fee + loan_fee + fire_fee + tax_clear + display_fee +
                     tekigo_fee + brokerage_total + move_fee + reform_fee + stamp_fee)
total = property_price + total_expenses

# ==========================
# PDF生成
# ==========================
def build_pdf():
    pdf = FPDF(unit="mm", format="A4")
    _register_fonts(pdf)
    pdf.add_page()
    pdf.set_font("IPAexGothic", "B", 12)
    if st.session_state["customer_name"]:
        pdf.cell(0, 8, f"{st.session_state['customer_name']} 様", ln=1)
    pdf.set_font("IPAexGothic", "", 11)
    pdf.cell(0, 7, f"物件名：{st.session_state['property_name']}", ln=1)
    pdf.cell(0, 7, f"物件価格：{fmt_jpy(property_price)}", ln=1)
    pdf.cell(0, 7, f"手付金：{fmt_jpy(deposit)}（契約時振込）", ln=1)
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
            pdf.cell(w[0], 6, r[0], 1)
            pdf.cell(w[1], 6, r[1], 1, 0, "R")
            pdf.cell(w[2], 6, r[2], 1, 0, "C")
            pdf.multi_cell(w[3], 6, r[3], 1)
        pdf.ln(3)

    draw_table("◆ 登記・税金・精算金", [
        ["契約書 印紙代", fmt_jpy(stamp_fee), "契約時", "電子契約で削減可"],
        ["登記費用", fmt_jpy(regist_fee), "決済時", "司法書士報酬＋登録免許税"],
        ["精算金", fmt_jpy(tax_clear), "決済時", "固都税・管理費など日割"],
        ["表示登記", fmt_jpy(display_fee), "決済時", "新築戸建のみ必要（目安10万円）"]
    ])

    draw_table("◆ 金融機関・火災保険", [
        ["銀行事務手数料", fmt_jpy(loan_fee), "決済時", "借入金額×2.2%"],
        ["金消契約 印紙税", fmt_jpy(0), "金消契約時", "電子契約は不要"],
        ["火災保険料", fmt_jpy(fire_fee), "決済時", "概算5年分"],
        ["適合証明書", fmt_jpy(tekigo_fee), "相談", "フラット35利用時"]
    ])

    draw_table("◆ 仲介会社（TERASS）", [
        ["仲介手数料（合計）", fmt_jpy(brokerage_total), "契約／決済", "3％＋6万円＋税"],
        ["契約時", fmt_jpy(brokerage_contract), "契約時", ""],
        ["決済時", fmt_jpy(brokerage_settlement), "決済時", ""]
    ])

    draw_table("◆ 追加工事・引越し", [
        ["引越し費用", fmt_jpy(move_fee), "入居時", ""],
        ["追加リフォーム", fmt_jpy(reform_fee), "相談", ""]
    ])

    pdf.set_font("IPAexGothic", "", 9)
    pdf.multi_cell(0, 5, "※諸費用は全て目安です。契約内容により変動します。登記費用・火災保険・精算金等は見積取得後に確定します。")
    pdf.ln(2)

    pdf.set_fill_color(235, 240, 255)
    pdf.set_font("IPAexGothic", "B", 11)
    pdf.cell(0, 8, f"諸費用合計：{fmt_jpy(total_expenses)}　総合計（物件＋諸費用）：{fmt_jpy(total)}", ln=1, fill=True)
    pdf.cell(0, 8, f"契約時必要資金（手付＋印紙＋仲介半金）：{fmt_jpy(contract_funds)}", ln=1, fill=True)
    pdf.cell(0, 8, f"決済時必要資金（残代＋登記＋精算＋仲介残）：{fmt_jpy(settlement_funds)}", ln=1, fill=True)

    out = pdf.output(dest="S")
    return out.encode("latin-1") if isinstance(out, str) else bytes(out)


# ==========================
# PDF生成・保存・DL
# ==========================
pdf_bytes = build_pdf()

if st.button("💾 諸費用データを保存"):
    try:
        payload = {
            "client_id": client_id,
            "customer_name": st.session_state["customer_name"],
            "property_name": st.session_state["property_name"],
            "property_price": property_price,
            "deposit": deposit,
            "loan_amount": loan_amount,
            "stamp_fee": stamp_fee,
            "loan_fee": loan_fee,
            "regist_fee": regist_fee,
            "fire_fee": fire_fee,
            "tax_clear": tax_clear,
            "display_fee": display_fee,
            "tekigo_fee": tekigo_fee,
            "move_fee": move_fee,
            "reform_fee": reform_fee,
            "brokerage_contract": brokerage_contract,
            "brokerage_settlement": brokerage_settlement,
            "brokerage_total": brokerage_total,
            "contract_funds": contract_funds,
            "settlement_funds": settlement_funds,
            "total_expenses": total_expenses,
            "total": total,
            "saved_at": now_iso(),
        }
        SB.table("fees_detail").upsert(payload, on_conflict="client_id").execute()
        st.success("保存しました ✅")
    except Exception as e:
        st.error(f"保存中にエラー発生: {e}")
