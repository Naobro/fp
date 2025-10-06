# fp/pages/諸費用明細.py
# 仕様：
# - PDFフォーマット：サンクタス調布ヶ丘／パークハウス四季の森形式
# - 借入金額：万円単位
# - 仲介手数料 合計は自動計算、契約時は手動入力、決済時は自動計算
# - 契約時必要費用／決済時必要費用をPDF下部に表示
# - Supabase保存は上書き方式
# - 下部署名欄を復元（TERASS / 西山直樹）

import os, re, io, zipfile, tempfile
from pathlib import Path
import streamlit as st
import requests
from fpdf import FPDF
from client_portal import get_sb, now_iso

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

# ============ ページ設定 ============
st.set_page_config(page_title="資金計画書（諸費用明細）", layout="centered")
st.title("資金計画書（諸費用明細）")

# ============ フォント準備 ============
def _pick_font_dir() -> Path:
    for d in [Path.cwd()/"fonts_runtime", Path(tempfile.gettempdir())/"fonts_runtime"]:
        try:
            d.mkdir(parents=True, exist_ok=True)
            t = d/".wtest"; t.write_text("ok", encoding="utf-8"); t.unlink()
            return d
        except Exception:
            continue
    return Path(tempfile.mkdtemp(prefix="fonts_runtime_"))

FONT_DIR = _pick_font_dir()
IPAEX_G_ZIP = "https://moji.or.jp/wp-content/ipafont/IPAexfont/ipaexg00401.zip"
FONT_GOTHIC_PATH = FONT_DIR/"IPAexGothic.ttf"

def _ensure_font():
    if not FONT_GOTHIC_PATH.exists():
        resp = requests.get(IPAEX_G_ZIP)
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            for n in zf.namelist():
                if n.endswith("ipaexg.ttf"):
                    with zf.open(n) as src, open(FONT_GOTHIC_PATH, "wb") as dst:
                        dst.write(src.read())
                    break

def _register_font(pdf: FPDF):
    _ensure_font()
    pdf.add_font("IPAexGothic", "", str(FONT_GOTHIC_PATH), uni=True)
    pdf.add_font("IPAexGothic", "B", str(FONT_GOTHIC_PATH), uni=True)

# ============ ユーティリティ ============
def fmt_jpy(n: int): return f"{n:,} 円"
def number_input_commas(label, value, step=1):
    s = st.text_input(label, f"{value:,}")
    s = re.sub(r"[^\d]", "", s)
    try: return int(s)
    except: return value
def calc_stamp_tax(p):
    if p <= 5_000_000: return 5_000
    if p <= 10_000_000: return 10_000
    if p <= 50_000_000: return 10_000
    if p <= 100_000_000: return 30_000
    if p <= 500_000_000: return 60_000
    return 160_000

# ============ 入力 ============
st.session_state["customer_name"] = st.text_input("お客様名", st.session_state.get("customer_name",""))
st.session_state["property_name"] = st.text_input("物件名", st.session_state.get("property_name",""))

price_man = st.number_input("物件価格（万円）", min_value=100, max_value=200_000, value=5800, step=10)
property_price = price_man * 10_000
deposit = number_input_commas("手付金（円）", int(property_price * 0.05))
stamp_fee = calc_stamp_tax(property_price)
regist_fee = number_input_commas("登記費用（円）", 400_000)
tax_clear = number_input_commas("精算金（円）", 100_000)

# 仲介手数料関連
tax_rate = 0.10
brokerage_total = int((property_price * 0.03 + 60_000) * (1 + tax_rate))
brokerage_contract = number_input_commas("契約時仲介手数料（円）", 1_100_000)
brokerage_settlement = brokerage_total - brokerage_contract

# ===== PDFセクション =====
def build_pdf():
    pdf = FPDF(unit="mm", format="A4")
    _register_font(pdf)
    pdf.add_page()
    pdf.set_font("IPAexGothic", "B", 13)
    pdf.cell(0, 10, f"{st.session_state['property_name']}　諸費用明細", ln=1, align="C")
    pdf.ln(4)

    pdf.set_font("IPAexGothic", "", 11)
    pdf.cell(0, 7, f"お客様名：{st.session_state['customer_name']} 様", ln=1)
    pdf.cell(0, 7, f"物件価格：{fmt_jpy(property_price)}", ln=1)
    pdf.cell(0, 7, f"手付金：{fmt_jpy(deposit)}", ln=1)
    pdf.ln(3)

    headers = ["項目", "金額", "時期", "備考"]
    w = [50, 40, 30, 70]
    pdf.set_font("IPAexGothic", "B", 10)
    pdf.set_fill_color(230, 235, 250)
    for h, ww in zip(headers, w):
        pdf.cell(ww, 8, h, 1, 0, "C", 1)
    pdf.ln(8)

    pdf.set_font("IPAexGothic", "", 10)
    rows = [
        ["契約書印紙代", fmt_jpy(stamp_fee), "契約時", "電子契約の場合不要"],
        ["登記費用", fmt_jpy(regist_fee), "決済時", "司法書士報酬＋登録免許税"],
        ["精算金", fmt_jpy(tax_clear), "決済時", "固定資産税・管理費等"],
        ["仲介手数料（合計）", fmt_jpy(brokerage_total), "－", "3%＋6万＋税"],
        ["仲介手数料（契約時）", fmt_jpy(brokerage_contract), "契約時", "手動入力"],
        ["仲介手数料（決済時）", fmt_jpy(brokerage_settlement), "決済時", "残額自動計算"],
    ]
    for r in rows:
        pdf.cell(w[0], 7, r[0], 1)
        pdf.cell(w[1], 7, r[1], 1, 0, "R")
        pdf.cell(w[2], 7, r[2], 1, 0, "C")
        pdf.cell(w[3], 7, r[3], 1, 1)
    pdf.ln(4)

    # 契約時・決済時必要費用
    pdf.set_font("IPAexGothic", "B", 11)
    need_contract = deposit + stamp_fee + brokerage_contract
    need_settlement = (property_price - deposit) + tax_clear + regist_fee
    pdf.cell(0, 8, f"契約時必要費用：{fmt_jpy(need_contract)}", ln=1)
    pdf.cell(0, 8, f"決済時必要費用：{fmt_jpy(need_settlement)}", ln=1)
    pdf.ln(8)

    # フッター（署名欄）
    pdf.set_font("IPAexGothic", "", 10)
    pdf.cell(0, 8, "株式会社TERASS", ln=1, align="R")
    pdf.cell(0, 8, "エージェント　西山直樹", ln=1, align="R")

    return pdf.output(dest="S").encode("latin-1")

pdf_bytes = build_pdf()

# ===== 保存処理 =====
if st.button("💾 諸費用データを保存"):
    payload = {
        "customer_name": st.session_state["customer_name"],
        "property_name": st.session_state["property_name"],
        "property_price": int(property_price),
        "deposit": int(deposit),
        "stamp_fee": int(stamp_fee),
        "regist_fee": int(regist_fee),
        "tax_clear": int(tax_clear),
        "brokerage_total": int(brokerage_total),
        "brokerage_contract": int(brokerage_contract),
        "brokerage_settlement": int(brokerage_settlement),
        "saved_at": now_iso(),
    }
    try:
        SB.table("fees_detail").upsert(
            {**payload, "client_id": client_id},
            on_conflict="client_id"
        ).execute()
        st.success("保存しました ✅")
    except Exception as e:
        st.error(f"保存エラー: {e}")

# ===== PDFダウンロード =====
st.download_button(
    label="📄 PDFをダウンロード",
    data=pdf_bytes,
    file_name=f"諸費用明細_{st.session_state.get('customer_name','未設定')}.pdf",
    mime="application/pdf"
)
