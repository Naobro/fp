# fp/pages/諸費用明細.py
# 修正版：借入金額×2.2%計算 + 借入金額入力欄追加

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
        res = (SB.table("fees_detail")
               .select("*")
               .eq("client_id", client_id)
               .order("saved_at", desc=True)
               .limit(1)
               .execute())
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
import tempfile as _tmp
def _pick_font_dir() -> Path:
    for d in [Path.cwd()/"fonts_runtime", Path(_tmp.gettempdir())/"fonts_runtime", Path.home()/".cache"/"fonts_runtime"]:
        try:
            d.mkdir(parents=True, exist_ok=True)
            t = d/".wtest"; t.write_text("ok", encoding="utf-8"); t.unlink()
            return d
        except Exception:
            continue
    return Path(_tmp.mkdtemp(prefix="fonts_runtime_"))

FONT_DIR = _pick_font_dir()
IPAEX_G_ZIP = "https://moji.or.jp/wp-content/ipafont/IPAexfont/ipaexg00401.zip"
FONT_GOTHIC_PATH = FONT_DIR/"IPAexGothic.ttf"

def _ensure_fonts():
    if not FONT_GOTHIC_PATH.exists():
        resp = requests.get(IPAEX_G_ZIP, timeout=30); resp.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            ttf_members = [n for n in zf.namelist() if n.lower().endswith("ipaexg.ttf")]
            with zf.open(ttf_members[0]) as src, open(FONT_GOTHIC_PATH, "wb") as dst:
                dst.write(src.read())

def _register_font(pdf: FPDF):
    _ensure_fonts()
    pdf.add_font("IPAexGothic", "", str(FONT_GOTHIC_PATH), uni=True)
    pdf.add_font("IPAexGothic", "B", str(FONT_GOTHIC_PATH), uni=True)

# ============ 関数 ============
def fmt_jpy(n): return f"{n:,} 円"
def number_input_commas(label, value):
    s = st.text_input(label, f"{value:,}")
    s = re.sub(r"[^\d]", "", s)
    try: return int(s)
    except: return value
def monthly_payment(loan_amount, years, rate):
    n = years*12; r = rate/100/12
    if r==0: return int(loan_amount/n)
    return int(loan_amount*r*(1+r)**n/((1+r)**n-1))

# ============ 入力 ============
st.session_state["customer_name"] = st.text_input("お客様名", st.session_state.get("customer_name",""))
st.session_state["property_name"] = st.text_input("物件名", st.session_state.get("property_name",""))
price_man = st.number_input("物件価格（万円）", min_value=100, max_value=200000, value=7880, step=10)
property_price = price_man*10000
deposit = number_input_commas("手付金（円）", 4000000)
stamp_fee = number_input_commas("契約書印紙代（円）", 30000)
regist_fee = number_input_commas("登記費用（円）", 500000)
tax_clear = number_input_commas("精算金（円）", 50000)
fire_fee = number_input_commas("火災保険（円）", 100000)

# 借入金額入力追加（銀行事務手数料用）
loan_amount_man = st.number_input("借入金額（万円）", min_value=100, max_value=200000, value=int(price_man), step=10)
loan_amount = loan_amount_man * 10000
loan_fee = int(loan_amount * 0.022)

tekigo_fee = number_input_commas("適合証明書（円）", 0)
brokerage_total = int(property_price*0.03+60000)*1.1
broker_contract = number_input_commas("仲介手数料（契約時・円）", 1100000)
broker_decision = brokerage_total - broker_contract
option_reform = number_input_commas("リフォーム費用（円）", 0)
option_move = number_input_commas("引越し費用（円）", 120000)
base_rate = st.number_input("基準金利（年%）", 0.88, step=0.01)
loanA = number_input_commas("借入金額③（円）", int(property_price))
loanB = number_input_commas("借入金額④（円）", int(property_price))
yearA = 47
yearB = 35
m_full = monthly_payment(property_price+regist_fee+tax_clear+loan_fee+fire_fee, 35, base_rate)
m_only = monthly_payment(property_price, 35, base_rate)
mA = monthly_payment(loanA, yearA, base_rate)
mB = monthly_payment(loanB, yearB, base_rate)
need_contract = deposit + stamp_fee + broker_contract

# ============ PDF構築 ============
def build_pdf():
    pdf = FPDF(unit="mm", format="A4")
    _register_font(pdf)
    pdf.add_page()
    pdf.set_font("IPAexGothic", "B", 12)
    pdf.cell(0, 8, f"{st.session_state['customer_name']} 様", ln=1)
    pdf.set_font("IPAexGothic", "", 11)
    pdf.cell(0, 7, f"物件名：{st.session_state['property_name']}", ln=1)
    pdf.cell(0, 7, f"物件価格：{fmt_jpy(property_price)}", ln=1)
    pdf.cell(0, 7, f"手付金：{fmt_jpy(deposit)}（物件価格の5%前後／契約時振込・物件価格に充当）", ln=1)
    pdf.ln(2)

    headers = ["項目", "金額", "支払時期", "説明"]
    w = [46, 34, 33, 77]
    pdf.set_font("IPAexGothic", "B", 10)
    for h, ww in zip(headers, w):
        pdf.cell(ww, 7, h, 1, 0, "C")
    pdf.ln(7)

    rows = [
        ["◆ 登記費用・税金・精算金等","","",""],
        ["契約書 印紙代", fmt_jpy(stamp_fee), "契約時", "電子契約で削減可能"],
        ["登記費用", fmt_jpy(regist_fee), "決済時", "司法書士報酬＋登録免許税"],
        ["精算金", fmt_jpy(tax_clear), "決済時", "固都税・管理費等（日割り精算）"],
        ["表示登記", "0 円", "決済時", "新築戸建の場合必要（目安10万円）"],
        ["◆ 金融機関・火災保険","","",""],
        ["銀行事務手数料", fmt_jpy(loan_fee), "決済時", "借入金額×2.2%"],
        ["金消契約 印紙税", "0 円", "金消契約時", "電子契約は不要・金融機関により必要"],
        ["火災保険", fmt_jpy(fire_fee), "決済時", "5年の火災保険（概算）"],
        ["適合証明書", fmt_jpy(tekigo_fee), "相談", "フラット35の場合 必須"],
        ["◆ 仲介会社（TERASS）","","",""],
        ["仲介手数料（契約時）", fmt_jpy(broker_contract), "契約時", ""],
        ["仲介手数料（決済時）", fmt_jpy(broker_decision), "決済時", ""],
        ["仲介手数料 合計", fmt_jpy(brokerage_total), "", "物件価格×3%＋6万＋税"],
        ["◆ 追加工事・引越し","","",""],
        ["リフォーム費用", fmt_jpy(option_reform), "決済後", "任意工事（見積要）"],
        ["引越し費用", fmt_jpy(option_move), "入居時", "距離・荷物量による"],
    ]

    pdf.set_font("IPAexGothic", "", 10)
    for r in rows:
        if "◆" in r[0]:
            pdf.set_font("IPAexGothic", "B", 10)
            pdf.cell(sum(w), 7, r[0], 1, 1)
            pdf.set_font("IPAexGothic", "", 10)
        else:
            pdf.cell(w[0], 7, r[0], 1)
            pdf.cell(w[1], 7, r[1], 1, 0, "R")
            pdf.cell(w[2], 7, r[2], 1, 0, "C")
            pdf.cell(w[3], 7, r[3], 1, 1)
    pdf.ln(3)

    total_expenses = regist_fee + tax_clear + loan_fee + fire_fee + stamp_fee + brokerage_total + option_move
    pdf.set_font("IPAexGothic", "B", 11)
    pdf.cell(0, 8, f"諸費用合計：{fmt_jpy(total_expenses)}　総合計（物件＋諸費用）：{fmt_jpy(property_price+total_expenses)}", ln=1)
    pdf.ln(3)

    pdf.set_font("IPAexGothic", "B", 11)
    pdf.cell(0, 7, "（支払例）", ln=1)
    pdf.set_font("IPAexGothic", "", 10)
    examples = [
        ["①自己資金0（物件＋諸費用フル）", property_price+total_expenses, m_full, m_full+28200],
        ["②諸費用のみ自己資金（物件のみ借入）", property_price, m_only, m_only+28200],
        [f"③パターンA 金利{base_rate:.2f}%／{yearA}年", loanA, mA, mA+28200],
        [f"④パターンB 金利{base_rate:.2f}%／{yearB}年", loanB, mB, mB+28200],
    ]
    for e in examples:
        pdf.cell(80, 7, e[0], 1)
        pdf.cell(40, 7, fmt_jpy(e[1]), 1, 0, "R")
        pdf.cell(35, 7, fmt_jpy(e[2]), 1, 0, "R")
        pdf.cell(35, 7, fmt_jpy(e[3]), 1, 1, "R")

    pdf.ln(4)
    pdf.cell(0, 7, f"契約時必要資金（手付金＋印紙代＋仲介半金）：{fmt_jpy(need_contract)}", ln=1)
    pdf.ln(4)
    pdf.set_font("IPAexGothic", "", 9)
    pdf.multi_cell(0, 5, "※諸費用は全て目安です。物件・契約形態・条件により変動します\n登記費用・火災保険・精算金等も見積取得後に確定します。", align="L")

    pdf.set_y(-55)
    pdf.set_font("IPAexGothic", "B", 10)
    pdf.cell(0, 6, "西山 直樹 / Naoki Nishiyama", ln=1)
    pdf.set_font("IPAexGothic", "", 9)
    pdf.cell(0, 5, "TERASS, Inc.", ln=1)
    pdf.cell(0, 5, "〒105-0001 東京都港区虎ノ門二丁目2番1号 住友不動産虎ノ門タワー 13階", ln=1)
    pdf.cell(0, 5, "TEL: 090-4399-2480 / FAX: 03-6369-3864", ln=1)
    pdf.cell(0, 5, "Email: naoki.nishiyama@terass.com", ln=1)
    pdf.cell(0, 5, "LINE：naokiwm", ln=1)

    return pdf.output(dest="S").encode("latin-1")

pdf_bytes = build_pdf()

# ===== 保存＆ダウンロード =====
if st.button("💾 諸費用データを保存"):
    SB.table("fees_detail").upsert({
        "client_id": client_id,
        "customer_name": st.session_state["customer_name"],
        "property_name": st.session_state["property_name"],
        "property_price": property_price,
        "loan_amount": loan_amount,
        "total_expenses": regist_fee + tax_clear + loan_fee + fire_fee,
        "saved_at": now_iso()
    }, on_conflict="client_id").execute()
    st.success("保存しました ✅")

st.download_button(
    "📄 PDFダウンロード",
    data=pdf_bytes,
    file_name=f"{st.session_state['property_name']}　諸費用明細.pdf",
    mime="application/pdf"
)
