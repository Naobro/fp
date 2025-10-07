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

# 契約書印紙税（自動計算：物件価格連動＋電子契約で0円）
st.markdown("#### 契約書 印紙代（自動計算）")
col_stamp1, col_stamp2 = st.columns([1, 1])
with col_stamp1:
    elec_contract = st.checkbox("電子契約（印紙代 0円）", value=False)

# 自動計算ロジック
if elec_contract:
    stamp_fee = 0
else:
    stamp_fee = calc_stamp_tax(property_price)

# 自動反映欄（編集不可・見た目は数値欄）
with col_stamp2:
    st.number_input(
        "契約書 印紙代（円）",
        value=int(stamp_fee),
        step=1,
        disabled=True,
        help="物件価格に応じて自動計算されます（電子契約時は0円）"
    )
# 仲介手数料
st.markdown("#### 仲介手数料")
brokerage_total = number_input_commas("仲介手数料（合計・円）", int(property_price * 0.03 + 60_000))
brokerage_contract = number_input_commas("仲介手数料（契約時・円）", int(brokerage_total / 2))
brokerage_settlement = brokerage_total - brokerage_contract

# 登記・火災・銀行
regist_fee = number_input_commas("登記費用（円）", 400_000)
loan_fee = number_input_commas("銀行事務手数料（円）", int(property_price * 0.022))

# --- 金消契約 印紙税（電子契約なら0円に） ---
use_e_contract = st.checkbox("電子契約（印紙代 0円）", value=False, key="e_contract_stamp")
if use_e_contract:
    kinko_stamp = 0
else:
    kinko_stamp = number_input_commas("金消契約 印紙税（円）", 0)

fire_fee = number_input_commas("火災保険料（円）", 200_000)
tax_clear = number_input_commas("精算金（円）", 100_000)
display_fee = number_input_commas("表示登記（円）", 100_000 if (prop_type == "戸建て" and is_new) else 0)
# --- 追加リフォーム費用・引越し費用 ---
reform_fee = number_input_commas("追加リフォーム費用（円）", 0)
move_fee = number_input_commas("引越し費用（円）", 120_000)
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
m_only = monthly_payment(property_price, base_years, base_rate)
mA = monthly_payment(loanA, yearA, rateA)
mB = monthly_payment(loanB, yearB, rateB)

# 契約時・決済時資金
need_contract = deposit + stamp_fee + brokerage_contract
need_settle = property_price - deposit + regist_fee + tax_clear + brokerage_settlement


# ============ フォント登録関数（PDF生成前に必須） ============
from fpdf import FPDF
import requests, io, zipfile, tempfile
from pathlib import Path

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


# ======== PDF生成・保存・DL ========

# --- 仲介手数料（契約時／決済時）自動割振り ---
brokerage_total = int((property_price * 0.03 + 60000) * 1.1)

# --- 契約時入力欄（ユーザーが上書きできる） ---
brokerage_contract = st.number_input(
    "仲介手数料（契約時・円）",
    min_value=0,
    max_value=brokerage_total,
    value=0 if "brokerage_contract" not in st.session_state else st.session_state["brokerage_contract"],
    step=10_000,
)

# --- ロジック：自動割振り or 手動指定対応 ---
if brokerage_contract == 0:
    # 全額を決済時にまわす
    brokerage_settlement = brokerage_total
else:
    # 自動割振り
    if brokerage_total >= 2_200_000:
        default_contract = 1_100_000
    elif brokerage_total >= 1_100_000:
        default_contract = 550_000
    else:
        default_contract = 330_000
    # ユーザーが0以外を入力した場合はそのまま採用
    brokerage_contract = brokerage_contract or default_contract
    brokerage_settlement = brokerage_total - brokerage_contract

# --- 表示確認用 ---
st.markdown("#### 仲介手数料（自動割振り・調整後）")
col_b1, col_b2, col_b3 = st.columns(3)
with col_b1:
    st.number_input("仲介手数料（合計・円）", value=brokerage_total, step=10_000, disabled=True)
with col_b2:
    st.number_input("契約時（円）", value=brokerage_contract, step=10_000, disabled=True)
with col_b3:
    st.number_input("決済時（円）", value=brokerage_settlement, step=10_000, disabled=True)
# --- 契約時・決済時必要資金（仲介手数料の入力値反映版） ---
# 契約時必要資金：手付金 + 印紙代 + 契約時仲介手数料
contract_funds = int(deposit + stamp_fee + brokerage_contract)

# 決済時必要資金：
#   残代金 + 登記費用 + 精算金 + 決済時仲介手数料
settlement_funds = int(
    (property_price - deposit)
    + regist_fee
    + tax_clear
    + brokerage_settlement
)
# --- 諸費用合計と総合計 ---
total_expenses = int(
    regist_fee + loan_fee + fire_fee + tax_clear + display_fee +
    tekigo_fee + brokerage_total + move_fee + reform_fee + stamp_fee
)
total = property_price + total_expenses


def build_pdf():
    pdf = FPDF(unit="mm", format="A4")
    _register_jp_fonts(pdf)
    pdf.add_page()

    # ===== HEADER =====
    pdf.set_font("IPAexGothic", "B", 12)
    if st.session_state["customer_name"]:
        pdf.cell(0, 8, f"{st.session_state['customer_name']} 様", ln=1)
    pdf.set_font("IPAexGothic", "", 11)
    pdf.cell(0, 7, f"物件名：{st.session_state['property_name']}", ln=1)
    pdf.cell(0, 7, f"物件価格：{fmt_jpy(property_price)}", ln=1)
    pdf.cell(0, 7, f"手付金：{fmt_jpy(deposit)}（物件価格の5%前後／契約時振込・物件価格に充当）", ln=1)
    pdf.ln(3)

    # ===== テーブル用共通設定 =====
    w = [55, 35, 25, 75]  # 幅調整：説明欄を広く
    headers = ["項目", "金額", "支払時期", "説明"]

    def draw_table_section(title, rows):
        pdf.set_font("IPAexGothic", "B", 10)
        pdf.cell(0, 7, title, ln=1)
        pdf.set_fill_color(220, 230, 250)
        for h, ww in zip(headers, w):
            pdf.cell(ww, 7, h, 1, 0, "C", 1)
        pdf.ln(7)

        pdf.set_font("IPAexGothic", "", 9)
        for r in rows:
            y_before = pdf.get_y()
            x_before = pdf.get_x()

            pdf.cell(w[0], 6, r[0], border=1)
            pdf.cell(w[1], 6, r[1], border=1, align="R")
            pdf.cell(w[2], 6, r[2], border=1, align="C")

            x = pdf.get_x()
            y = pdf.get_y()
            pdf.multi_cell(w[3], 6, r[3], border=1)
            pdf.set_xy(x_before, max(y, pdf.get_y()))
        pdf.ln(3)

    # ===== 各セクション =====
    draw_table_section("◆ 登記費用・税金・精算金等", [
        ["契約書 印紙代", fmt_jpy(stamp_fee), "契約時", "電子契約で削減可能"],
        ["登記費用", fmt_jpy(regist_fee), "決済時", "司法書士報酬＋登録免許税"],
        ["精算金", fmt_jpy(tax_clear), "決済時", "固都税・管理費等（日割り精算）"],
        ["表示登記", fmt_jpy(display_fee), "決済時", "新築戸建の場合必要（目安10万円）"],
    ])

    draw_table_section("◆ 金融機関・火災保険", [
        ["銀行事務手数料", fmt_jpy(loan_fee), "決済時", "借入金額概算として物件価格×2.2%"],
        ["金消契約 印紙税", fmt_jpy(kinko_stamp), "金消契約時", "電子契約は不要・金融機関により必要"],
        ["火災保険", fmt_jpy(fire_fee), "決済時", "5年の火災保険（概算）"],
        ["適合証明書", fmt_jpy(tekigo_fee), "相談", "フラット35の場合 必須"],
    ])

    draw_table_section("◆ 仲介会社（TERASS）", [
        ["仲介手数料（合計）", fmt_jpy(brokerage_total), "契約時/決済時", "物件価格×3%＋6万＋税"],
        ["契約時", fmt_jpy(brokerage_contract), "契約時", "手付金と同時入金"],
        ["決済時", fmt_jpy(brokerage_settlement), "決済時", "残金決済時支払い"],
    ])

    draw_table_section("◆ 追加工事・引越し", [
        ["引越し費用", fmt_jpy(move_fee), "入居時", "距離・荷物量による"],
        ["追加リフォーム", fmt_jpy(reform_fee), "相談", "内容により異なる"],
    ])

    # ===== 注意書き =====
    pdf.set_font("IPAexGothic", "", 9)
    pdf.multi_cell(0, 5, "※諸費用は全て目安です。物件・契約形態・条件により変動します。\n登記費用・火災保険・精算金等も見積取得後に確定します。")
    pdf.ln(3)

    # ===== 合計部分（背景付き） =====
    pdf.set_fill_color(235, 240, 255)
    pdf.set_font("IPAexGothic", "B", 11)
    pdf.cell(0, 8, f"諸費用合計：{fmt_jpy(total_expenses)}　総合計（物件＋諸費用）：{fmt_jpy(total)}", ln=1, fill=True)
    pdf.cell(0, 8, f"契約時必要資金（手付金＋印紙代＋仲介半金）：{fmt_jpy(contract_funds)}", ln=1, fill=True)
    pdf.cell(0, 8, f"決済時必要資金（残代金＋精算金＋登記費用＋手数料残金）：{fmt_jpy(settlement_funds)}", ln=1, fill=True)
    pdf.ln(4)

    # ===== 支払例 =====
    pdf.set_font("IPAexGothic", "B", 10)
    pdf.cell(0, 7, "（支払例）①②は基準金利0.88％／35年、③④は手動入力条件", ln=1)
    pdf.set_font("IPAexGothic", "", 10)
    rows = [
        ["①自己資金0（物件＋諸費用フル）", property_price + total_expenses, m_full],
        ["②諸費用のみ自己資金（物件のみ借入）", property_price, m_only],
        [f"③パターンA 金利{rateA:.3f}%／{yearA}年", loanA, mA],
        [f"④パターンB 金利{rateB:.3f}%／{yearB}年", loanB, mB],
    ]
    for r in rows:
        pdf.cell(80, 7, r[0], 1)
        pdf.cell(50, 7, fmt_jpy(r[1]), 1, 0, "R")
        pdf.cell(60, 7, fmt_jpy(r[2]), 1, 1, "R")

   

    out = pdf.output(dest="S")
    return out.encode("latin-1") if isinstance(out, str) else bytes(out)
# --- PDF生成 ---
pdf_bytes = build_pdf()

# --- Supabase保存 ---
if st.button("💾 諸費用データを保存"):
    try:
        payload = {
            "customer_name": st.session_state["customer_name"],
            "property_name": st.session_state["property_name"],
            "property_price": property_price,
            "deposit": deposit,
            "stamp_fee": stamp_fee,
            "regist_fee": regist_fee,
            "tax_clear": tax_clear,
            "display_fee": display_fee,
            "loan_fee": loan_fee,
            "fire_fee": fire_fee,
            "tekigo_fee": tekigo_fee,
            "brokerage_contract": brokerage_contract,
            "brokerage_settlement": brokerage_settlement,
            "brokerage_total": brokerage_total,
            "move_fee": move_fee,
            "reform_fee": reform_fee,
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

        # Supabaseへ保存
        result = SB.table("fees_detail").upsert(
            {**payload, "client_id": client_id},
            on_conflict="client_id"
        ).execute()

        st.success("保存しました ✅")
        st.json(result.data)  # ← 成功時も内容を確認できるように表示

    except Exception as e:
        st.error(f"保存中にエラー発生: {e}")
# --- ダウンロード ---
st.download_button(
    "📄 資金計画書.pdf ダウンロード",
    data=pdf_bytes,
    file_name=f"{st.session_state['property_name']}　諸費用明細.pdf",
    mime="application/pdf",
)
