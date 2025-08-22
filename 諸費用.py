# fp/pages/諸費用明細.py
# 日本語PDF対応：IPAexフォントを公式ZIPから自動DL→展開→登録（utils不要・完全単体）
# 仕様：
#  - 物件名：入力 → PDFへ確実反映
#  - 借入パターン：①自己資金0（物件＋諸費用フル）／②諸費用のみ自己資金（物件のみ）／③入力A（手動）／④入力B（手動）
#  - ③④は 完全手動：借入金額（万円・整数）／金利（年%）／期間（年）
#  - ①②は 基準金利（年%）・年数35年固定で計算
#  - 銀行事務手数料は運用簡便のため「物件価格×2.2%」を採用（備考に明記）
#  - 金額入力は原則整数。借入金額の手入力は「万円」単位（万円未満は切り捨て）

import os
import re
import io
import zipfile
import tempfile
from pathlib import Path

import streamlit as st
import requests
from fpdf import FPDF  # ← FPDF_FONT_DIR は使いません（動的にTTFを登録）

# ============ 表示設定 ============
st.set_page_config(page_title="資金計画書（諸費用明細）", layout="centered")
st.title("資金計画書（諸費用明細）")

# ============ フォント（IPAexに全面切替） ============
import tempfile as _tmp

def _pick_font_dir() -> Path:
    """確実に書き込めるフォント置き場を選ぶ（順に試す）"""
    candidates = [
        Path.cwd() / "fonts_runtime",
        Path(_tmp.gettempdir()) / "fonts_runtime",
        Path.home() / ".cache" / "fonts_runtime",
    ]
    for d in candidates:
        try:
            d.mkdir(parents=True, exist_ok=True)
            # 書き込みテスト
            t = d / ".wtest"
            t.write_text("ok", encoding="utf-8")
            t.unlink()
            return d
        except Exception:
            continue
    # どれもダメなら一時ディレクトリを新規作成
    return Path(_tmp.mkdtemp(prefix="fonts_runtime_"))

FONT_DIR = _pick_font_dir()

# 公式配布の直リンク（単体zip）
IPAEX_G_ZIP = "https://moji.or.jp/wp-content/ipafont/IPAexfont/ipaexg00401.zip"  # ゴシック
IPAEX_M_ZIP = "https://moji.or.jp/wp-content/ipafont/IPAexfont/ipaexm00401.zip"  # 明朝
FONT_GOTHIC_PATH = FONT_DIR / "IPAexGothic.ttf"   # zip内 ipaexg.ttf を保存
FONT_MINCHO_PATH = FONT_DIR / "IPAexMincho.ttf"   # zip内 ipaexm.ttf を保存

def _download_and_extract_ttf(zip_url: str, member_suffix: str, save_path: Path) -> None:
    resp = requests.get(zip_url, timeout=30)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        ttf_members = [n for n in zf.namelist() if n.lower().endswith(member_suffix)]
        if not ttf_members:
            raise RuntimeError(f"TTF not found in {zip_url}")
        with zf.open(ttf_members[0]) as src, open(save_path, "wb") as dst:
            dst.write(src.read())

def _ensure_fonts() -> None:
    if not FONT_GOTHIC_PATH.exists():
        _download_and_extract_ttf(IPAEX_G_ZIP, "ipaexg.ttf", FONT_GOTHIC_PATH)
    if not FONT_MINCHO_PATH.exists():
        _download_and_extract_ttf(IPAEX_M_ZIP, "ipaexm.ttf", FONT_MINCHO_PATH)

def _register_jp_fonts(pdf: FPDF) -> None:
    _ensure_fonts()
    pdf.add_font("IPAexGothic", "", str(FONT_GOTHIC_PATH), uni=True)
    pdf.add_font("IPAexGothic", "B", str(FONT_GOTHIC_PATH), uni=True)  # 太字も同TTF
    pdf.add_font("IPAexMincho", "", str(FONT_MINCHO_PATH), uni=True)
    pdf.add_font("IPAexMincho", "B", str(FONT_MINCHO_PATH), uni=True)

# ============ ユーティリティ ============
A4_W = 210
A4_H = 297

def fmt_jpy(n: int) -> str:
    return f"{n:,} 円"

def number_input_commas(label, value, step=1):
    """カンマ付き整数入力（全角・記号除去→整数化）"""
    s = st.text_input(label, f"{value:,}")
    s = re.sub(r"[^\d]", "", s)
    try:
        v = int(s)
    except Exception:
        v = value
    return v

def round_deposit(price_yen: int) -> int:
    """手付金＝物件価格の5%を 50万円単位で四捨五入"""
    base = price_yen * 0.05
    return int(round(base / 500_000) * 500_000)

def calc_stamp_tax(price_yen: int) -> int:
    """契約書 印紙税（主要レンジのみ。必要ならレンジ追加可）"""
    p = price_yen
    if p <= 5_000_000: return 5_000
    if p <= 10_000_000: return 10_000
    if p <= 50_000_000: return 10_000
    if p <= 100_000_000: return 30_000
    if p <= 500_000_000: return 60_000
    if p <= 1_000_000_000: return 160_000
    if p <= 5_000_000_000: return 320_000
    return 480_000

def monthly_payment(loan_amount: int, years: int, annual_rate: float) -> int:
    """元利均等返済の月々返済額（端数は整数・円へ）"""
    n = years * 12
    r = annual_rate / 100.0 / 12.0
    if n <= 0:
        return 0
    if r == 0:
        return int(loan_amount / n)
    try:
        return int(loan_amount * r * (1 + r) ** n / ((1 + r) ** n - 1))
    except ZeroDivisionError:
        return 0

# ============ 入力（基本情報） ============
# 顧客名・物件名（PDFで使用）
st.session_state["customer_name"] = st.text_input("お客様名（例：山田太郎）", st.session_state.get("customer_name", ""))
st.session_state["property_name"] = st.text_input("物件名", st.session_state.get("property_name", ""))

# 物件条件
col_a1, col_a2, col_a3 = st.columns([1, 1, 1])
with col_a1:
    prop_type = st.selectbox("物件種別", ["マンション", "戸建て"], index=0)
with col_a2:
    is_new_house = st.checkbox("新築戸建（表示登記あり）", value=(prop_type == "戸建て"))
with col_a3:
    use_flat35 = st.checkbox("フラット35（適合証明）", value=False)

# 物件価格（万円入力 → 円換算。万円未満は切り捨て）
price_man = st.number_input("物件価格（万円）", min_value=100, max_value=200_000, value=5_800, step=10)
property_price = int(price_man) * 10_000  # 万円 → 円（整数・切り捨て）

# 手付金（自動初期値：5%を50万円単位で丸め）
default_deposit = round_deposit(property_price)
deposit = number_input_commas("手付金（円・物件価格5%/50万円単位で四捨五入）", default_deposit, step=500_000)

# 管理費・修繕積立（月額）
kanri_month = number_input_commas("管理費・修繕積立金（月額円）", 18_000, step=1_000)

# ============ 基準金利（①②用：年数は35年固定） ============
st.markdown("#### 基準金利（①自己資金0／②諸費用のみ自己資金 に適用）")
base_rate = st.number_input("基準金利（年%）", min_value=0.0, max_value=5.0, value=0.78, step=0.01)
base_years = 35  # 指定どおり固定

# ============ 登記費用の計算方法：固定 or 比例 ============
col_r1, col_r2 = st.columns([1, 1])
with col_r1:
    regist_mode = st.radio("登記費用の計算方法", ["固定額", "物件価格比例（%）"], index=0, horizontal=True)

if regist_mode == "固定額":
    default_regist = 400_000  # 種別で差が必要なら分岐可
    regist_fee = number_input_commas("登記費用（円）", default_regist, step=10_000)
else:
    col_r2.markdown("（例：0.5% = 0.5 を入力）")
    regist_rate = st.number_input("登記費用（物件価格に対する%）", min_value=0.0, max_value=3.0, value=0.5, step=0.1)
    regist_fee = int(property_price * (regist_rate / 100.0))

# ============ 税・精算・表示・保険など ============
tax_rate = 0.10
brokerage = int((property_price * 0.03 + 60_000) * (1 + tax_rate))  # 仲介手数料（税10%込）
stamp_fee = calc_stamp_tax(property_price)
tax_clear = number_input_commas("精算金（固都税・管理費等・日割り精算）", 100_000, step=10_000)
display_fee = number_input_commas(
    "表示登記（新築戸建のみ／10万円前後）",
    100_000 if (prop_type == "戸建て" and is_new_house) else 0,
    step=10_000,
)

# 事務手数料は「物件価格×2.2%」で見積（①の借入金と一致しやすい／循環参照を避ける）
loan_fee = int(property_price * 0.022)
kinko_stamp = number_input_commas("金銭消費貸借 印紙税（通常0円）", 0, step=1_000)
fire_fee = number_input_commas("火災保険料（円・5年分概算）", 200_000, step=10_000)
tekigo_fee = number_input_commas("適合証明書（フラット35の場合必須）", 55_000 if use_flat35 else 0, step=5_000)

# ============ 任意項目 ============
option_rows = []
option_fee = number_input_commas("リフォーム・追加工事費（円）", 0, step=10_000)
if option_fee > 0:
    option_rows.append(["リフォーム費用", fmt_jpy(option_fee), "決済時", "任意工事・追加リフォーム等"])
moving_fee = number_input_commas("引越し費用（円）", 150_000, step=10_000)
if moving_fee > 0:
    option_rows.append(["引越し費用", fmt_jpy(moving_fee), "入居時", "距離・荷物量による"])
kaden_fee = number_input_commas("家具家電代（円）", 0, step=10_000)
if kaden_fee > 0:
    option_rows.append(["家具家電代", fmt_jpy(kaden_fee), "入居時", "新生活準備費用"])

# ============ 明細テーブル構築 ============
cost_rows = []
cost_rows.append(["◆ 登記費用・税金・精算金等", "", "", ""])
cost_rows.extend(
    [
        ["契約書 印紙代", fmt_jpy(stamp_fee), "契約時", "電子契約で削減可能"],
        ["登記費用", fmt_jpy(regist_fee), "決済時", "司法書士報酬＋登録免許税"],
        ["精算金", fmt_jpy(tax_clear), "決済時", "固都税・管理費等（日割り精算）"],
        ["表示登記", fmt_jpy(display_fee), "決済時", "新築戸建の場合必要（目安10万円）"],
    ]
)
cost_rows.append(["◆ 金融機関・火災保険", "", "", ""])
cost_rows.extend(
    [
        ["銀行事務手数料", fmt_jpy(loan_fee), "決済時", "借入金額概算として物件価格×2.2%"],
        ["金消契約 印紙税", fmt_jpy(kinko_stamp), "金消契約時", "電子契約は不要・金融機関により必要"],
        ["火災保険", fmt_jpy(fire_fee), "決済時", "5年の火災保険（概算）"],
        ["適合証明書", fmt_jpy(tekigo_fee), "相談", "フラット35の場合 必須"],
    ]
)
cost_rows.append(["◆ 仲介会社（TERASS）", "", "", ""])
cost_rows.append(["仲介手数料", fmt_jpy(brokerage), "契約時/決済時", "物件価格×3%＋6万＋税"])
if option_rows:
    cost_rows.append(["◆ 追加工事・引越し", "", "", ""])
    cost_rows.extend(option_rows)

# 合計（諸費用 → 総合計）
total_expenses = 0
for r in cost_rows:
    if r[1] and ("◆" not in r[0]):
        total_expenses += int(r[1].replace(" 円", "").replace(",", ""))
total = int(property_price + total_expenses)

# ============ 借入パターン ============
# ① 自己資金0：物件＋諸費用フル（基準金利・35年）
loan_amount_full = property_price + total_expenses

# ② 諸費用のみ自己資金：物件のみ（基準金利・35年）
loan_amount_only = property_price

# ③ 入力A（完全手動：借入額（万円）／金利／年数）
st.markdown("#### ③ 入力A（自由入力：借入・金利・年数）")
col_l3a_1, col_l3a_2, col_l3a_3 = st.columns(3)
with col_l3a_1:
    default_loan_A_man = max(0, property_price // 10_000)
    loan_amount_A_man = st.number_input("借入金額（万円：③）", min_value=0, max_value=300_000, value=int(default_loan_A_man), step=10)
    loan_amount_A = int(loan_amount_A_man) * 10_000  # 円
with col_l3a_2:
    loan_rate_A = st.number_input("金利（年%：③）", min_value=0.0, max_value=5.0, value=base_rate, step=0.01)
with col_l3a_3:
    loan_years_A = st.number_input("返済期間（年：③）", min_value=1, max_value=50, value=35, step=1)

# ④ 入力B（完全手動：借入額（万円）／金利／年数）
st.markdown("#### ④ 入力B（自由入力：借入・金利・年数）")
col_l4b_1, col_l4b_2, col_l4b_3 = st.columns(3)
with col_l4b_1:
    default_loan_B_man = int(property_price // 10_000)
    loan_amount_B_man = st.number_input("借入金額（万円：④）", min_value=0, max_value=300_000, value=default_loan_B_man, step=10)
    loan_amount_B = int(loan_amount_B_man) * 10_000  # 円
with col_l4b_2:
    loan_rate_B = st.number_input("金利（年%：④）", min_value=0.0, max_value=5.0, value=base_rate, step=0.01)
with col_l4b_3:
    loan_years_B = st.number_input("返済期間（年：④）", min_value=1, max_value=50, value=35, step=1)

# ============ 月々返済（4パターン計算） ============
monthly_full = monthly_payment(loan_amount_full, base_years, base_rate)   # ①
monthly_only = monthly_payment(loan_amount_only, base_years, base_rate)   # ②
monthly_A = monthly_payment(loan_amount_A, loan_years_A, loan_rate_A)     # ③
monthly_B = monthly_payment(loan_amount_B, loan_years_B, loan_rate_B)     # ④

# 契約時必要資金（手付金＋印紙代＋仲介半金）
brokerage_half = int(brokerage / 2)
need_at_contract = int(deposit + stamp_fee + brokerage_half)

# ============ 備考 ============
default_bikou = (
    "※諸費用は全て目安です。物件・契約形態・条件により変動します。\n"
    "登記費用・火災保険・精算金等も見積取得後に確定します。\n"
    "①②は『基準金利』を使用し、年数は35年固定で試算しています。\n"
    "③④は借入金額（万円）・金利（年%）・返済期間（年）を手動入力して試算します。\n"
    "銀行事務手数料は概算として『物件価格×2.2%』で計上しています（金融機関により異なります）。"
)
bikou = st.text_area("備考・注釈欄（自由編集）", value=default_bikou, height=120)

# ============ 画面側サマリー ============
st.subheader("サマリー")
st.write(f"- 物件名：**{st.session_state.get('property_name','（未入力）')}**")
st.write(f"- 物件価格：**{fmt_jpy(property_price)}**（入力：{price_man:,} 万円）")
st.write(f"- 諸費用合計：**{fmt_jpy(total_expenses)}**")
st.write(f"- 総合計（物件＋諸費用）：**{fmt_jpy(total)}**")
st.write(f"- 契約時必要資金（手付金＋印紙＋仲介半金）：**{fmt_jpy(need_at_contract)}**")
st.write(f"- 基準金利（①②）：**{base_rate:.2f}%／{base_years}年**")
st.write(
    f"- 月々返済額：①フル**{fmt_jpy(monthly_full)}**／②物件のみ**{fmt_jpy(monthly_only)}**／"
    f"③A **{fmt_jpy(monthly_A)}**／④B **{fmt_jpy(monthly_B)}**"
)
st.write(
    f"- 管理費込み：①**{fmt_jpy(monthly_full + kanri_month)}**／②**{fmt_jpy(monthly_only + kanri_month)}**／"
    f"③**{fmt_jpy(monthly_A + kanri_month)}**／④**{fmt_jpy(monthly_B + kanri_month)}**"
)

# ============ PDF 生成 ============
MY_NAME = "西山　直樹 / Naoki Nishiyama"
MY_COMPANY = "TERASS, Inc."
MY_ADDRESS = "〒105-0001 東京都港区虎ノ門二丁目2番1号　住友不動産虎ノ門タワー 13階"
MY_TEL = "TEL: 090-4399-2480 / FAX: 03-6369-3864"
MY_MAIL = "Email: naoki.nishiyama@terass.com"
MY_LINE = "LINE：naokiwm"

def build_pdf(
    customer_name: str,
    property_name: str,
    property_price: int,
    deposit: int,
    cost_rows: list[list[str]],
    total_expenses: int,
    total: int,
    kanri_month: int,
    # 4パターン（①②は基準金利）
    base_rate: float,
    base_years: int,
    loan_amount_full: int,
    monthly_full: int,
    loan_amount_only: int,
    monthly_only: int,
    # ③
    loan_amount_A: int,
    loan_rate_A: float,
    loan_years_A: int,
    monthly_A: int,
    # ④
    loan_amount_B: int,
    loan_rate_B: float,
    loan_years_B: int,
    monthly_B: int,
    need_at_contract: int,
    bikou: str,
) -> bytes:
    pdf = FPDF(unit="mm", format="A4")
    _register_jp_fonts(pdf)
    pdf.set_left_margin(13)
    pdf.set_top_margin(13)
    pdf.set_auto_page_break(False)
    pdf.add_page()

    # ===== ここから本文を描画 =====
    # 上部（タイトル・基本情報）
    if customer_name:
        pdf.set_font("IPAexGothic", "B", 12)
        pdf.cell(0, 8, f"{customer_name} 様", ln=1, align="L")

    pdf.set_font("IPAexGothic", "B", 11.5)
    pdf.cell(0, 7, f"物件名：{property_name}", ln=1, align="L")

    pdf.set_font("IPAexGothic", "B", 13)
    pdf.cell(0, 8, f"物件価格：{fmt_jpy(property_price)}", ln=1, align="L")

    pdf.set_font("IPAexGothic", "", 11)
    pdf.cell(0, 7, f"手付金：{fmt_jpy(deposit)}（物件価格の5%前後／契約時振込・物件価格に充当）", ln=1, align="L")
    pdf.ln(1)

    # 明細テーブル（見出し）
    headers = ["項目", "金額", "支払時期", "説明"]
    col_w = [46, 34, 33, 77]  # 合計190（余白考慮で若干オーバーでも描画可）
    pdf.set_font("IPAexGothic", "B", 10)
    pdf.set_fill_color(220, 230, 250)
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 7, h, 1, 0, "C", 1)
    pdf.ln(7)

    # 明細テーブル（中身）
    pdf.set_font("IPAexGothic", "", 10)
    for row in cost_rows:
        if "◆" in row[0]:
            # セクション見出し
            pdf.set_font("IPAexGothic", "B", 10)
            pdf.cell(sum(col_w), 7, row[0], 1, 1, "L")
            pdf.set_font("IPAexGothic", "", 10)
        else:
            pdf.cell(col_w[0], 7, row[0], 1, 0, "L")
            pdf.cell(col_w[1], 7, row[1], 1, 0, "R")
            pdf.cell(col_w[2], 7, row[2], 1, 0, "C")
            pdf.cell(col_w[3], 7, row[3], 1, 1, "L")

    pdf.ln(1)

    # 注意書き
    pdf.set_font("IPAexGothic", "", 9.5)
    pdf.set_text_color(80, 80, 80)
    bikou_clean = re.sub(r"。\n", "\n", bikou).strip()
    pdf.multi_cell(0, 6, bikou_clean)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    # 合計（諸費用・総合計）
    pdf.set_fill_color(220, 240, 255)
    sum_cols = [45, 50, 55, 40]
    pdf.set_font("IPAexGothic", "B", 12)
    pdf.cell(sum_cols[0], 9, "諸費用合計", 1, 0, "C", 1)
    pdf.cell(sum_cols[1], 9, fmt_jpy(total_expenses), 1, 0, "R", 1)
    pdf.cell(sum_cols[2], 9, "総合計（物件＋諸費用）", 1, 0, "C", 1)
    pdf.cell(sum_cols[3], 9, fmt_jpy(total), 1, 1, "R", 1)
    pdf.ln(3)

    # 支払例（4パターン）
    pdf.set_font("IPAexGothic", "B", 11)
    pdf.cell(0, 8, f"（支払例）①②は基準金利{base_rate:.2f}％／{base_years}年、③④は手動入力の条件", ln=1, align="L")

    # 4パターン表（列幅は4列で190mm程度）
    headers2 = ["借入パターン", "借入金額", "月々返済額", "総額（管理費含)"]
    col2_w = [90, 30, 35, 35]
    pdf.set_font("IPAexGothic", "B", 10)
    pdf.set_fill_color(220, 240, 255)
    for i, h in enumerate(headers2):
        pdf.cell(col2_w[i], 7, h, 1, 0, "C", 1)
    pdf.ln(7)

    # ① 自己資金0（物件＋諸費用フル）
    pdf.set_font("IPAexGothic", "", 10)
    title1 = f"①自己資金0（物件＋諸費用フル）"
    pdf.cell(col2_w[0], 8, title1, 1, 0, "L")
    pdf.cell(col2_w[1], 8, fmt_jpy(loan_amount_full), 1, 0, "R")
    pdf.cell(col2_w[2], 8, fmt_jpy(monthly_full), 1, 0, "R")
    pdf.set_font("IPAexGothic", "", 9.5)
    pdf.cell(col2_w[3], 8, fmt_jpy(monthly_full + kanri_month), 1, 1, "R")

    # ② 諸費用のみ自己資金（物件のみ）
    pdf.set_font("IPAexGothic", "", 10)
    title2 = f"②諸費用のみ自己資金（物件のみ借入）"
    pdf.cell(col2_w[0], 8, title2, 1, 0, "L")
    pdf.cell(col2_w[1], 8, fmt_jpy(loan_amount_only), 1, 0, "R")
    pdf.cell(col2_w[2], 8, fmt_jpy(monthly_only), 1, 0, "R")
    pdf.set_font("IPAexGothic", "", 9.5)
    pdf.cell(col2_w[3], 8, fmt_jpy(monthly_only + kanri_month), 1, 1, "R")

    # ③ 入力A（手動）
    pdf.set_font("IPAexGothic", "", 10)
    title3 = f"③パターンA　金利{loan_rate_A:.2f}%／{loan_years_A}年"
    pdf.cell(col2_w[0], 8, title3, 1, 0, "L")
    pdf.cell(col2_w[1], 8, fmt_jpy(loan_amount_A), 1, 0, "R")
    pdf.cell(col2_w[2], 8, fmt_jpy(monthly_A), 1, 0, "R")
    pdf.set_font("IPAexGothic", "", 9.5)
    pdf.cell(col2_w[3], 8, fmt_jpy(monthly_A + kanri_month), 1, 1, "R")

    # ④ 入力B（手動）
    pdf.set_font("IPAexGothic", "", 10)
    title4 = f"④パターンB 金利{loan_rate_B:.2f}%／{loan_years_B}年"
    pdf.cell(col2_w[0], 8, title4, 1, 0, "L")
    pdf.cell(col2_w[1], 8, fmt_jpy(loan_amount_B), 1, 0, "R")
    pdf.cell(col2_w[2], 8, fmt_jpy(monthly_B), 1, 0, "R")
    pdf.set_font("IPAexGothic", "", 9.5)
    pdf.cell(col2_w[3], 8, fmt_jpy(monthly_B + kanri_month), 1, 1, "R")
    pdf.ln(2)

    # 契約時必要資金（手付金＋印紙代＋仲介半金）
    pdf.set_font("IPAexGothic", "B", 11)
    pdf.cell(0, 7, f"契約時必要資金（手付金＋印紙代＋仲介半金）：{fmt_jpy(need_at_contract)}", ln=1, align="L")

    # フッター（連絡先）
    footer_y = 297 - 49  # A4の高さ - フッター領域
    pdf.set_y(footer_y)
    pdf.set_font("IPAexGothic", "B", 10)
    pdf.cell(0, 6, "西山　直樹 / Naoki Nishiyama", ln=1, align="L")
    pdf.set_font("IPAexGothic", "", 9)
    pdf.cell(0, 6, "TERASS, Inc.", ln=1, align="L")
    pdf.cell(0, 6, "〒105-0001 東京都港区虎ノ門二丁目2番1号　住友不動産虎ノ門タワー 13階", ln=1, align="L")
    pdf.cell(0, 6, "TEL: 090-4399-2480 / FAX: 03-6369-3864", ln=1, align="L")
    pdf.cell(0, 6, "Email: naoki.nishiyama@terass.com", ln=1, align="L")
    pdf.cell(0, 6, "LINE：naokiwm", ln=1, align="L")

    # ===== ここまで本文。bytes で返す =====
    out = pdf.output(dest="S")
    pdf_bytes = out.encode("latin-1") if isinstance(out, str) else bytes(out)
    return pdf_bytes

# ============ 出力（ワンクリックDL） ============
try:
    pdf_bytes = build_pdf(
        customer_name=st.session_state.get("customer_name", ""),
        property_name=st.session_state.get("property_name", ""),
        property_price=property_price,
        deposit=deposit,
        cost_rows=cost_rows,
        total_expenses=total_expenses,
        total=total,
        kanri_month=kanri_month,
        base_rate=base_rate,
        base_years=base_years,
        loan_amount_full=loan_amount_full,
        monthly_full=monthly_full,
        loan_amount_only=loan_amount_only,
        monthly_only=monthly_only,
        loan_amount_A=loan_amount_A,
        loan_rate_A=loan_rate_A,
        loan_years_A=loan_years_A,
        monthly_A=monthly_A,
        loan_amount_B=loan_amount_B,
        loan_rate_B=loan_rate_B,
        loan_years_B=loan_years_B,
        monthly_B=monthly_B,
        need_at_contract=need_at_contract,
        bikou=bikou,
    )
    st.download_button(
    label="📄 資金計画書.pdf をダウンロード",
    data=pdf_bytes,
    file_name=f"{st.session_state.get('property_name', '資金計画書')}　諸費用明細.pdf",
    mime="application/pdf",
)
except Exception as e:
    st.error(f"PDF生成エラー: {e}")