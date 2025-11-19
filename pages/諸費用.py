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
# Supabaseから保存データを取得・反映
# ----------------------------
client_id = st.query_params.get("client", "unknown")
saved = load_saved_data(client_id)

# ---- 🔧 Supabaseデータをsession_stateに強制上書き（初期値ロジック排除） ----
if saved:
    for k, v in saved.items():
        # Supabaseからのロード時、自動計算フラグもロードする
        if k in ["_deposit_manual", "_loanfee_manual", "_manual_broker"]:
            st.session_state[k] = v
        # _prev_price, _prev_loan_amount, _prev_broker_price はロードしない (現在の値と比較するため)
        elif not k.startswith("_prev_"):
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
        # Streamlitのtext_inputを使用
        # Streamlitのバージョンによっては、text_inputのkey引数が必要になる場合がありますが、
        # ここではnumber_input_commasを呼び出す箇所で一意のkeyを与える必要があります。
        # ただし、現状のコードでは呼び出し側のロジックが複雑なため、ここではtext_inputのまま残します。
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
    
def round_to_10man(n):
    """金額を10万円単位で繰り上げ"""
    import math
    return int(math.ceil(n / 100_000.0) * 100_000)

def save_to_state(key, value):
    st.session_state[key] = value
    return value

# ----------------------------
# 入力エリア（基本情報）
# ----------------------------
# 🔧 keyの追加
st.session_state["customer_name"] = st.text_input("お客様名", st.session_state.get("customer_name", ""), key="input_customer_name")
st.session_state["property_name"] = st.text_input("物件名", st.session_state.get("property_name", ""), key="input_property_name")

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

price_man = st.number_input(
    "物件価格（万円）",
    min_value=0,             # ✅ int型モード
    max_value=10_000_000,    # ✅ 上限 1,000万万円（＝100億円）
    value=int(float(st.session_state.get("price_man", 5800) or 5800)),
    step=1,                  # ✅ 万円単位
    format="%d"              # ✅ 整数表示
)

# ✅ Supabase 保存安全化処理：float混入防止
price_man = int(price_man)
save_to_state("price_man", price_man)
property_price = int(price_man * 10_000)  # ✅ 円換算（bigint対応）
# ================================
# 自動計算ブロック（手付金・印紙代・銀行事務手数料・仲介手数料）
# ================================

# --- 手付金（物件価格×5%を自動計算＋手動修正可／物件価格変更時のみ再計算） ---

# 1. 自動計算値 (物件価格の5%を50万円単位で丸める)
auto_deposit = int(round(price_man * 10_000 * 0.05 / 500_000) * 500_000)

# 2. 自動更新の条件をチェック
prev_price = st.session_state.get("_prev_price", 0)
manual_flag = st.session_state.get("_deposit_manual", False)

# 物件価格が変わった場合、または手動フラグが立っていない場合に自動計算値を初期値とする
if (prev_price != price_man) or not manual_flag:
    # 💡 修正: 価格が変わったら、強制的に自動計算値を初期値にセット
    deposit_initial = auto_deposit
    st.session_state["_deposit_manual"] = False # 強制的にリセット
else:
    # 💡 修正: 価格が変わっていない、かつ手動修正済みなら、保存された値を初期値とする
    # savedがNoneの場合のフォールバックとしてauto_depositを設定
    deposit_initial = st.session_state.get("deposit", auto_deposit) 

# 3. ユーザー入力
# 🔧 keyの追加
new_deposit = number_input_commas("手付金（円：物件価格×5%自動計算／50万円単位）", deposit_initial)

# 4. 手動フラグの更新
# ユーザーが入力した値が自動計算値と異なる場合、手動フラグをTrueにする
if new_deposit != auto_deposit:
    st.session_state["_deposit_manual"] = True
else:
    st.session_state["_deposit_manual"] = False

# 5. セッションステートの更新と永続化に必要な値の保存
st.session_state["_prev_price"] = price_man
deposit = save_to_state("deposit", new_deposit)


# --- 印紙代（自動計算＋電子契約で0円） ---
elec_contract = st.checkbox(
    "電子契約（印紙代 0円）",
    value=st.session_state.get("elec_contract", False)
)
save_to_state("elec_contract", elec_contract)

# ✅ 修正：チェック時に即0円へ反映（再描画対応）
if elec_contract:
    stamp_fee_auto = 0
else:
    stamp_fee_auto = calc_stamp_tax(price_man * 10_000)

# 🔧 keyの追加
stamp_fee = number_input_commas(
    "契約書 印紙代（円：自動計算）",
    stamp_fee_auto
)
save_to_state("stamp_fee", stamp_fee)


# --- 借入金額入力（None対策入り） ---
loan_amount_man_raw = st.session_state.get("loan_amount_man", price_man)

# None が混入した場合の完全ガード
if loan_amount_man_raw is None:
    loan_amount_man_raw = price_man

loan_amount_man = st.number_input(
    "借入金額（万円）",
    min_value=0,
    max_value=200_000,
    value=int(loan_amount_man_raw),
    step=10
)

save_to_state("loan_amount_man", loan_amount_man)
# --- 銀行事務手数料（借入金額×2.2％を自動計算＋手動修正可） ---
# 借入金額（円）の計算
loan_amount = loan_amount_man * 10_000 # 👈 loan_amountをここで定義
save_to_state("loan_amount", loan_amount) # 👈 loan_amountをここで保存

auto_loan_fee = int(loan_amount * 0.022) # 👈 loan_amountを使って計算
prev_loan = st.session_state.get("_prev_loan_amount", 0)
manual_fee_flag = st.session_state.get("_loanfee_manual", False)

# 自動更新条件: 借入金額が変わった or （手動フラグがFalseなのに）保存値が自動計算値と異なる
if (prev_loan != loan_amount_man) or \
   (not manual_fee_flag and st.session_state.get("loan_fee") != auto_loan_fee): # 👈 修正点: 初期ロード時の補正を追加
    loan_fee = auto_loan_fee
    st.session_state["_loanfee_manual"] = False # 👈 修正点: 強制更新で手動フラグをリセット
else:
    loan_fee = st.session_state.get("loan_fee", auto_loan_fee)

# 🔧 keyの追加
new_loan_fee = number_input_commas(
    "銀行事務手数料（円：借入金額×2.2% 自動計算）", loan_fee
)

# 手動検出・保存
if new_loan_fee != auto_loan_fee: # 👈 修正点: 自動計算値と異なればTrue
    st.session_state["_loanfee_manual"] = True
else:
    st.session_state["_loanfee_manual"] = False # 👈 修正点: 自動計算値に戻ったらFalse

st.session_state["_prev_loan_amount"] = loan_amount_man
save_to_state("loan_fee", new_loan_fee)


# --- 仲介手数料（物件価格に自動連動＋分割） ---
tax_rate = 0.10

# 自動算出
auto_broker_total = int((property_price * 0.03 + 60_000) * (1 + tax_rate))

# 契約時分の初期値（段階的に決定）
if auto_broker_total >= 2_200_000:
    auto_broker_contract = 1_100_000
elif auto_broker_total >= 1_100_000:
    auto_broker_contract = 550_000
else:
    auto_broker_contract = 330_000

auto_broker_settlement = auto_broker_total - auto_broker_contract

# -------------------------------
# ✅ 仲介手数料は「物件価格」変更時のみ再計算
# -------------------------------
prev_broker_price = st.session_state.get("_prev_broker_price", 0)
manual_broker_flag = st.session_state.get("_manual_broker", False)

# 🔹物件価格が変更されたとき or 初回ロード時に物件価格と一致しないとき
#    手動フラグがあっても強制的に自動計算値を適用する
if (prev_broker_price != property_price) or \
   (not manual_broker_flag and st.session_state.get("broker_total") != auto_broker_total): # ← この行を追加・修正

    broker_total = auto_broker_total
    broker_contract = auto_broker_contract
    # 強制的に自動計算値を適用した場合は、手動フラグをFalseに戻す
    st.session_state["_manual_broker"] = False # ← この行を追加（デバッグ修正点）

else:
    # 以前の値かセッションステートの値を読み込む（手動フラグがTrueの場合）
    broker_total = int(st.session_state.get("broker_total", auto_broker_total) or 0)
    broker_contract = int(st.session_state.get("broker_contract", auto_broker_contract) or 0)

# 🔽 以下の入力欄のコードはそのまま 🔽
# --- 入力欄（カンマ入力でも安全に数値変換） ---
# 🔧 keyの追加
new_broker_total = number_input_commas("仲介手数料 総額（円）", broker_total)
# 🔧 keyの追加
new_broker_contract = number_input_commas("仲介手数料 契約時（円）", broker_contract)

# --- 安全ロジック（契約時が総額を超えたら補正） ---
if new_broker_contract > new_broker_total:
    new_broker_contract = new_broker_total

broker_settlement = int(new_broker_total) - int(new_broker_contract)

# --- 手動検出・保存 ---
# 🚨 ここで手動フラグのロジックを修正し、自動計算値から少しでもズレたら手動と見なす
# (new_broker_total != auto_broker_total) または (new_broker_contract != auto_broker_contract) のどちらか。
if new_broker_total != auto_broker_total or new_broker_contract != auto_broker_contract:
    st.session_state["_manual_broker"] = True
else:
    st.session_state["_manual_broker"] = False # ← 追加: 自動計算値に戻ったらフラグも戻す（デバッグ修正点）

st.session_state["_prev_broker_price"] = property_price

# --- 保存（確実にint型で保持） ---
save_to_state("broker_total", int(new_broker_total))
save_to_state("broker_contract", int(new_broker_contract))
save_to_state("broker_settlement", int(broker_settlement))
# --- 各種費用（登記費用ロジック付き）---

# 🔹 登記費用：物件価格×登録免許税率＋司法書士報酬（15万円）
registration_tax_rate = 0.0015  # 減税税率（住宅用 0.15%）
judicial_fee = 150000           # 司法書士報酬（円）

auto_regist_fee = int(property_price * registration_tax_rate + judicial_fee)
# 🔧 keyの追加
regist_fee = number_input_commas("登記費用（円：物件価格×0.15%＋司法書士報酬15万円 自動計算）",
                             st.session_state.get("regist_fee", auto_regist_fee))

# 🔧 keyの追加
fire_fee = number_input_commas("火災保険料（円）",
                              st.session_state.get("fire_fee", 200_000))
# 🔧 keyの追加
tax_clear = number_input_commas("精算金（円）",
                               st.session_state.get("tax_clear", 100_000))
# 🔧 keyの追加
display_fee = number_input_commas("表示登記（円）",
                                 st.session_state.get("display_fee", 110_000 if (prop_type == "戸建て" and is_new) else 0))
# 🔧 keyの追加
tekigo_fee = number_input_commas("適合証明書（円）",
                               st.session_state.get("tekigo_fee", 55_000 if use_flat35 else 0))
# 🔧 keyの追加
reform_fee = number_input_commas("追加リフォーム費用（円）",
                               st.session_state.get("reform_fee", 0))
# 🔧 keyの追加
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
# 🔧 keyの追加
base_rate = st.number_input("基準金利（年%）", value=0.780, step=0.001, format="%.3f", key="input_base_rate")
base_years = 35

colA1, colA2, colA3 = st.columns(3)
with colA1: loanA_man = st.number_input("借入金額（万円：A）", value=int(price_man), step=10, key="input_loanA_man")
with colA2: rateA = st.number_input("金利（A）", value=base_rate, step=0.001, format="%.3f", key="input_rateA")
with colA3: yearA = st.number_input("年数（A）", value=base_years, step=1, key="input_yearA")
loanA = loanA_man * 10_000

colB1, colB2, colB3 = st.columns(3)
with colB1: loanB_man = st.number_input("借入金額（万円：B）", value=int(price_man), step=10, key="input_loanB_man")
with colB2: rateB = st.number_input("金利（B）", value=base_rate, step=0.001, format="%.3f", key="input_rateB")
with colB3: yearB = st.number_input("年数（B）", value=base_years, step=1, key="input_yearB")
loanB = loanB_man * 10_000

# --- 月々支払計算 ---
# ✅ 修正：total（物件＋諸費用合計）をここで再定義してから利用
total_expenses = int(
    regist_fee + loan_fee + fire_fee + tax_clear + display_fee +
    tekigo_fee + move_fee + reform_fee + stamp_fee + broker_total
)
total = property_price + total_expenses

# ✅ 自己資金0（物件＋諸費用すべてを借入）
loan_full = round_to_10man(total)  # ✅ 総額を10万円単位で切り上げて借入額に
m_full = monthly_payment(loan_full, base_years, base_rate)

# ✅ 諸費用のみ自己資金パターン
m_only = monthly_payment(property_price, base_years, base_rate)

# ✅ A／Bパターン
mA = monthly_payment(loanA, yearA, rateA)
mB = monthly_payment(loanB, yearB, rateB)

# --- 契約・決済必要資金 ---
contract_funds = int(deposit + stamp_fee + broker_contract)
settlement_funds = int((property_price - deposit) + regist_fee + tax_clear + broker_settlement + loan_fee)

# --- 諸費用合計 ---
# 再計算（上で定義済みだが、安全のため再確認）
total_expenses = int(
    regist_fee + loan_fee + fire_fee + tax_clear + display_fee +
    tekigo_fee + move_fee + reform_fee + stamp_fee + broker_total
)
total = property_price + total_expenses


# ----------------------------
# PDF 生成関数
# ----------------------------
def build_pdf():
    pdf = FPDF(unit="mm", format="A4")
    _register_jp_fonts(pdf)
    pdf.add_page()
    pdf.set_font("IPAexGothic", "B", 12)

    # --- ヘッダー ---
    if st.session_state["customer_name"]:
        pdf.cell(0, 8, f"{st.session_state['customer_name']} 様", ln=1)
    pdf.set_font("IPAexGothic", "", 11)
    pdf.cell(0, 7, f"物件名：{st.session_state['property_name']}", ln=1)
    pdf.cell(0, 7, f"物件価格：{fmt_jpy(property_price)}", ln=1)
    pdf.cell(0, 7, f"手付金：{fmt_jpy(deposit)}（物件価格の5%目安）", ln=1)
    pdf.cell(0, 7, f"借入金額：{fmt_jpy(loan_amount_man * 10_000)}", ln=1)  # ✅ 追加（万円→円換算）
    pdf.ln(4)
# ✅ 3行まとめて外枠付き（罫線ボックス化）
    pdf.set_fill_color(235, 240, 255)
    pdf.set_font("IPAexGothic", "B", 11)

    # 枠の開始位置と幅・高さを記録
    x_start = pdf.get_x()
    y_start = pdf.get_y()
    box_width = 190  # A4余白考慮
    line_height = 8
    total_height = line_height * 3

    # 背景ボックス描画（塗り＋外枠）
    pdf.rect(x_start, y_start, box_width, total_height, style="DF")  # D=枠線, F=塗り

    # テキスト描画（背景付き）
    # 描画位置を調整して枠線内に収める
    pdf.set_xy(x_start, y_start)
    pdf.cell(box_width, 8, f"諸費用合計：{fmt_jpy(total_expenses)}　総合計：{fmt_jpy(total)}　自己資金差額：{fmt_jpy(max(0, total - (loan_amount_man * 10_000)))}", border=0, ln=1, fill=1)
    pdf.set_x(x_start)
    pdf.cell(box_width, 8, f"契約時必要資金：{fmt_jpy(contract_funds)}", border=0, ln=1, fill=1)
    pdf.set_x(x_start)
    pdf.cell(box_width, 8, f"決済時必要資金：{fmt_jpy(settlement_funds)}　※（追加リフォーム・火災保険・引っ越し費用除く）", border=0, ln=1, fill=1)
    pdf.ln(4)
    

    # --- テーブル設定（A4幅内に収まるサイズ） ---
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
            y_start = pdf.get_y()
            pdf.cell(w[0], 6, r[0], border=1)
            pdf.cell(w[1], 6, r[1], border=1, align="R")
            pdf.cell(w[2], 6, r[2], border=1, align="C")
            x = pdf.get_x()
            y = pdf.get_y()
            pdf.multi_cell(w[3], 6, r[3], border=1)
            # multi_cellを使った後のカーソルY座標調整
            max_y = pdf.get_y()
            pdf.set_xy(x_start, max_y) # 次の行の開始位置をリセット
        pdf.ln(3)

    # --- 各テーブル ---
    draw_table("◆ 登記費用・税金・精算金等", [
        ["契約書 印紙代", fmt_jpy(stamp_fee), "契約時", "電子契約なら0円"],
        ["登記費用", fmt_jpy(regist_fee), "決済時", "司法書士報酬＋登録免許税"],
        ["精算金", fmt_jpy(tax_clear), "決済時", "固都税・管理費の日割精算"],
        ["表示登記", fmt_jpy(display_fee), "決済時", "新築戸建のみ必要（約10万円）"],
    ])

    draw_table("◆ 金融機関・火災保険", [
        ["銀行事務手数料", fmt_jpy(loan_fee), "決済時", "借入金額×2.2%で自動算出"],
        ["火災保険", fmt_jpy(fire_fee), "決済時", "5年分の概算"],
        ["適合証明書", fmt_jpy(tekigo_fee), "相談", "フラット35利用時に必要"],
    ])

    draw_table("◆ 仲介会社（TERASS）", [
        ["仲介手数料 総額", fmt_jpy(broker_total), "契約＋決済", "物件価格×3%＋6万＋税"],
        ["契約時 仲介手数料", fmt_jpy(broker_contract), "契約時", "契約時 半金"],
        ["決済時 仲介手数料", fmt_jpy(broker_settlement), "決済時", "残額分"],
    ])

    draw_table("◆ 追加工事・引越し", [
        ["追加リフォーム", fmt_jpy(reform_fee), "相談", "内容により異なる"],
        ["引越し費用", fmt_jpy(move_fee), "入居時", "距離・荷物量による目安"],
    ])

    pdf.set_font("IPAexGothic", "", 9)
    pdf.multi_cell(0, 5,
        "※諸費用は概算です。物件・契約内容により増減します。\n"
        "登記費用・保険料・精算金などは見積確定後に決定します。")
    pdf.ln(2)

    
    
    # --- 借入パターン比較 ---
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
        # 不要な一時キー（内部フラグ）を除外
        exclude_keys = {"_deposit_manual", "_prev_price", "_loanfee_manual", "_prev_loan_amount", "_manual_broker", "_prev_broker_price"}
        
        # 保存する値を再確認
        # broker_totalなどはnew_broker_totalなどを使わずに、session_stateから取得した値を使う
        # ※ session_stateには既にsave_to_stateで確定値が入っている
        
        payload = {
            "client_id": client_id,
            "customer_name": st.session_state.get("customer_name", ""),
            "property_name": st.session_state.get("property_name", ""),
            "prop_type": st.session_state.get("prop_type", "マンション"),
            "is_new": st.session_state.get("is_new", False),
            "use_flat35": st.session_state.get("use_flat35", False),
            "elec_contract": st.session_state.get("elec_contract", False),
            
            # 数値データ
            "price_man": price_man,
            "property_price": property_price,
            "deposit": deposit,
            "loan_amount_man": loan_amount_man,
            "loan_amount": loan_amount,
            "loan_fee": new_loan_fee, # ユーザー入力値
            "broker_total": new_broker_total, # ユーザー入力値
            "broker_contract": new_broker_contract, # ユーザー入力値
            "broker_settlement": broker_settlement,
            "regist_fee": regist_fee,
            "fire_fee": fire_fee,
            "tax_clear": tax_clear,
            "display_fee": display_fee,
            "tekigo_fee": tekigo_fee,
            "move_fee": move_fee,
            "reform_fee": reform_fee,
            "stamp_fee": stamp_fee,
            
            # 自動計算フラグ
            "_deposit_manual": st.session_state.get("_deposit_manual", False),
            "_loanfee_manual": st.session_state.get("_loanfee_manual", False),
            "_manual_broker": st.session_state.get("_manual_broker", False),

            # 合計/月々
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
            "yearA": yearA,
            "yearB": yearB,
            "loanA_man": loanA_man,
            "loanB_man": loanB_man,
            "saved_at": now_iso(),
        }

        # 安全対策：Supabaseのスキーマにないキーを排除 (今回はそのまま)
        # 内部フラグは保存したいので、exclude_keysから除外
        
        # 最終的に保存するデータ
        final_payload = {k: st.session_state[k] for k in st.session_state.keys() if not k.startswith("_prev_") and k in payload}
        final_payload["client_id"] = client_id
        final_payload["saved_at"] = now_iso()
        
        SB.table("fees_detail").upsert(final_payload, on_conflict="client_id").execute()
        st.success("保存しました ✅") # 👈 実際にはDB接続が必要
    except Exception as e:
        st.error(f"保存中にエラー: {e}")
# ----------------------------
# PDF生成（確実に定義後に呼び出し）
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
