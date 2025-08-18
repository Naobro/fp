# fp/pages/諸費用.py  （単体完結版 / utils.py 依存なし）
import re
from pathlib import Path
import tempfile

import streamlit as st
from fpdf import FPDF

# =========================
# 設定
# =========================
A4_W = 210
A4_H = 297
TAX_RATE = 0.10  # 消費税10%

# ===== フォント検出（TTF絶対パス）=====
REG_NAME = "NotoSansJP-Regular.ttf"
BOLD_NAME = "NotoSansJP-Bold.ttf"

HERE = Path(__file__).resolve()       # .../fp/pages/諸費用.py
FP_DIR = HERE.parents[1]              # .../fp
REPO_ROOT = HERE.parents[2]           # .../ (= /mount/src)
CWD = Path.cwd()

SEARCH_DIRS = [
    REPO_ROOT / "fonts",              # 最優先: リポジトリ直下 /fonts
    FP_DIR / "fonts",                 # 次点: パッケージ直下 /fp/fonts
    CWD / "fonts",                    # 最後: CWD/fonts
]

def pick_font_files() -> tuple[Path, Path]:
    tried = []
    for d in SEARCH_DIRS:
        tried.append(str(d))
        if d.is_dir():
            reg = d / REG_NAME
            bold = d / BOLD_NAME
            if reg.exists() and bold.exists():
                return (reg.resolve(), bold.resolve())
    msg = [
        "日本語フォントが見つかりません。",
        "探した場所:",
        *[f"- {p}" for p in tried],
        "必要ファイル:",
        f"- {REG_NAME}",
        f"- {BOLD_NAME}",
        "例: リポジトリ直下 /fonts/ に NotoSansJP-*.ttf を置いてください。",
    ]
    raise FileNotFoundError("\n".join(msg))

FONT_REGULAR, FONT_BOLD = pick_font_files()

# =========================
# 共通ロジック
# =========================
def number_input_commas(label, value, step=1):
    s = st.text_input(label, f"{value:,}")
    s = re.sub(r"[^\d]", "", s)
    try:
        v = int(s)
    except Exception:
        v = value
    return v

def round_deposit(price_yen: int) -> int:
    """手付金=物件価格の5%を50万円単位で四捨五入"""
    base = price_yen * 0.05
    return int(round(base / 500_000) * 500_000)

def calc_stamp_tax(price_yen: int) -> int:
    """売買契約書の印紙税（現行の主な区分）"""
    if price_yen <= 5_000_000:
        return 5_000
    elif price_yen <= 10_000_000:
        return 10_000
    elif price_yen <= 50_000_000:
        return 10_000
    elif price_yen <= 100_000_000:
        return 30_000
    elif price_yen <= 500_000_000:
        return 60_000
    elif price_yen <= 1_000_000_000:
        return 160_000
    elif price_yen <= 5_000_000_000:
        return 320_000
    else:
        return 480_000

def monthly_payment(loan_amount_yen: int, years: int, annual_rate_pct: float) -> int:
    n = years * 12
    r = annual_rate_pct / 100.0 / 12.0
    if r == 0:
        return int(loan_amount_yen / n)
    return int(loan_amount_yen * r * (1 + r) ** n / ((1 + r) ** n - 1))

# =========================
# Streamlit 画面
# =========================
st.set_page_config(page_title="資金計画書（諸費用明細）", layout="centered")
st.title("資金計画書（諸費用明細）")

col0, col1 = st.columns([1, 2])
with col0:
    property_type = st.selectbox("物件種別", ["マンション", "戸建て"], index=0)
with col1:
    price_man = st.number_input("物件価格（万円）", min_value=100, max_value=100000, value=5800, step=10)
price_yen = int(price_man * 10_000)  # 万円→円

customer_name = st.text_input("お客様名（例：山田太郎）", "")
property_name = st.text_input("物件名", "")

# 手付金（自動）
default_deposit = round_deposit(price_yen)
deposit = number_input_commas("手付金（円・物件価格5%/50万円単位で四捨五入）", default_deposit, step=500_000)

# 管理費（マンションは入力、戸建ては通常0）
default_kanri = 18_000 if property_type == "マンション" else 0
kanri_month = number_input_commas("管理費・修繕積立金（月額円）", default_kanri, step=1_000)

# ローン条件
c1, c2, c3 = st.columns(3)
with c1:
    loan_amount_man = st.number_input("借入金額（万円・シミュ用）", min_value=0, max_value=200000, value=price_man, step=10)
    loan_amount_yen = int(loan_amount_man * 10_000)
with c2:
    loan_rate = st.number_input("金利（年%・シミュ用）", min_value=0.0, max_value=5.0, value=0.7, step=0.05)
with c3:
    loan_years = st.number_input("返済期間（年・シミュ用）", min_value=1, max_value=50, value=35)

# 諸費用自動算出
brokerage = int((price_yen * 0.03 + 60_000) * (1 + TAX_RATE))  # 仲介手数料(3%+6万)+税
stamp_fee = calc_stamp_tax(price_yen)                           # 契約書印紙税
regist_fee = number_input_commas("登記費用（円・司法書士報酬＋登録免許税）", 400_000, step=10_000)
tax_clear  = number_input_commas("精算金（固都税・管理費等・日割り精算）", 100_000, step=10_000)
display_fee = number_input_commas(
    "表示登記（新築戸建のみ／10万円前後・戸建で必要なら入力）", 0 if property_type == "マンション" else 0, step=10_000
)
loan_fee = int(loan_amount_yen * 0.022)                         # 銀行事務手数料（2.2%想定）
kinko_stamp = number_input_commas("金銭消費貸借 印紙税（通常0円）", 0, step=1_000)
fire_fee = number_input_commas("火災保険料（円・5年分概算）", 200_000, step=10_000)
tekigo_fee = number_input_commas("適合証明書（フラット35の場合必須）", 0, step=10_000)
option_reform = number_input_commas("リフォーム・追加工事費（円）", 0, step=10_000)
option_moving = number_input_commas("引越し費用（円）", 150_000, step=10_000)
option_kagu   = number_input_commas("家具家電代（円）", 0, step=10_000)

# 明細テーブル
cost_rows = []
cost_rows.append(["◆ 登記費用・税金・精算金等", "", "", ""])
cost_rows.extend([
    ["契約書 印紙代", f"{stamp_fee:,} 円", "契約時", "電子契約で削減可能"],
    ["登記費用", f"{regist_fee:,} 円", "決済時", "司法書士報酬＋登録免許税"],
    ["精算金", f"{tax_clear:,} 円", "決済時", "固都税・管理費等（日割り精算）"],
])
if property_type == "戸建て":
    cost_rows.append(["表示登記", f"{display_fee:,} 円", "決済時", "新築戸建の場合必要（目安10万円）"])

cost_rows.append(["◆ 金融機関・火災保険", "", "", ""])
cost_rows.extend([
    ["銀行事務手数料", f"{loan_fee:,} 円", "決済時", "借入金額2.2%程度"],
    ["金消契約 印紙税", f"{kinko_stamp:,} 円", "金消契約時", "電子契約は不要・金融機関により必要"],
    ["火災保険", f"{fire_fee:,} 円", "決済時", "5年の火災保険（概算）"],
    ["適合証明書", f"{tekigo_fee:,} 円", "相談", "フラット35の場合 必須"],
])

cost_rows.append(["◆ 仲介会社（TERASS）", "", "", ""])
cost_rows.append(["仲介手数料", f"{brokerage:,} 円", "契約時/決済時", "物件価格×3%＋6万＋税"])

# オプション類
if any([option_reform, option_moving, option_kagu]):
    cost_rows.append(["◆ 追加工事・引越し", "", "", ""])
    if option_reform:
        cost_rows.append(["リフォーム費用", f"{option_reform:,} 円", "決済時", "任意工事・追加リフォーム等"])
    if option_moving:
        cost_rows.append(["引越し費用", f"{option_moving:,} 円", "入居時", "距離・荷物量による"])
    if option_kagu:
        cost_rows.append(["家具家電代", f"{option_kagu:,} 円", "入居時", "新生活準備費用"])

# 集計
total_expenses = sum(
    int(r[1].replace(" 円", "").replace(",", "")) for r in cost_rows if r[1] and ("◆" not in r[0])
)
grand_total = int(price_yen + total_expenses)

monthly1 = monthly_payment(price_yen + total_expenses, loan_years, loan_rate)
monthly2 = monthly_payment(price_yen, loan_years, loan_rate)

# 契約時必要資金（手付＋印紙＋仲介半金）
contract_need = int(deposit + stamp_fee + brokerage / 2)

default_bikou = (
    "※諸費用は全て目安です。物件・契約形態・条件により変動します。\n"
    "登記費用・火災保険・精算金等も見積取得後に確定します。\n"
    "銀行事務手数料は、借入金額を基準に2.2%で算出しています。"
)
bikou = st.text_area("備考・注釈欄（自由編集）", value=default_bikou, height=80)

# 画面サマリ
st.subheader("サマリ")
cA, cB, cC = st.columns(3)
with cA:
    st.metric("諸費用合計", f"{total_expenses:,} 円")
with cB:
    st.metric("総合計（物件＋諸費用）", f"{grand_total:,} 円")
with cC:
    st.metric("契約時必要資金（概算）", f"{contract_need:,} 円")

st.caption(f"月々返済（物件＋諸費用借入）: {monthly1:,} 円 / 月")
st.caption(f"月々返済（物件価格のみ借入）: {monthly2:,} 円 / 月")
if property_type == "マンション":
    st.caption(f"管理費・修繕積立金（月額）: {kanri_month:,} 円 → 想定総額: {(monthly1+kanri_month):,} 円 / 月")

# =========================
# PDF 出力
# =========================
def make_pdf() -> bytes:
    pdf = FPDF(unit="mm", format="A4")
    # フォント登録
    pdf.add_font("NotoSans", "", str(FONT_REGULAR), uni=True)
    pdf.add_font("NotoSans", "B", str(FONT_BOLD),    uni=True)

    pdf.set_left_margin(13)
    pdf.set_top_margin(13)
    pdf.add_page()
    pdf.set_auto_page_break(False)

    # ヘッダ
    pdf.set_font("NotoSans", "B", 12)
    if customer_name:
        pdf.cell(0, 8, f"{customer_name} 様", ln=1, align="L")
    pdf.set_font("NotoSans", "B", 11.5)
    pdf.cell(0, 7, f"物件名：{property_name}", ln=1, align="L")
    pdf.set_font("NotoSans", "B", 13)
    pdf.cell(0, 8, f"物件価格：{price_yen:,} 円（{property_type}）", ln=1, align="L")
    pdf.set_font("NotoSans", "", 11)
    pdf.cell(0, 7, f"手付金：{deposit:,} 円（物件価格の5%前後／契約時振込・物件価格に充当）", ln=1, align="L")
    pdf.ln(1)

    # 明細テーブル
    headers = ["項目", "金額", "支払時期", "説明"]
    col_w = [46, 34, 33, 77]
    pdf.set_font("NotoSans", "B", 10)
    pdf.set_fill_color(220, 230, 250)
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 7, h, 1, 0, "C", 1)
    pdf.ln(7)
    pdf.set_font("NotoSans", "", 10)
    for row in cost_rows:
        if "◆" in row[0]:
            pdf.set_font("NotoSans", "B", 10)
            pdf.cell(sum(col_w), 7, row[0], 1, 1, "L", 0)
            pdf.set_font("NotoSans", "", 10)
        else:
            pdf.cell(col_w[0], 7, row[0], 1, 0, "L")
            pdf.cell(col_w[1], 7, row[1], 1, 0, "R")
            pdf.cell(col_w[2], 7, row[2], 1, 0, "C")
            pdf.cell(col_w[3], 7, row[3], 1, 1, "L")
    pdf.ln(1)

    # 注意書き
    pdf.set_font("NotoSans", "", 9.5)
    pdf.set_text_color(80, 80, 80)
    bikou_clean = re.sub(r"。\n", "\n", bikou).strip()
    pdf.multi_cell(0, 6, bikou_clean)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    # 合計
    pdf.set_fill_color(220, 240, 255)
    sum_cols = [45, 50, 55, 40]
    pdf.set_font("NotoSans", "B", 12)
    pdf.cell(sum_cols[0], 9, "諸費用合計", 1, 0, "C", 1)
    pdf.cell(sum_cols[1], 9, f"{total_expenses:,} 円", 1, 0, "R", 1)
    pdf.cell(sum_cols[2], 9, "総合計（物件＋諸費用）", 1, 0, "C", 1)
    pdf.cell(sum_cols[3], 9, f"{grand_total:,} 円", 1, 1, "R", 1)
    pdf.ln(3)

    # 支払例
    pdf.set_font("NotoSans", "B", 11)
    pdf.cell(0, 8, f"（支払例）※金利{loan_rate:.2f}％／{loan_years}年返済の場合", ln=1, align="L")
    headers2 = ["借入パターン", "借入金額", "月々返済額", "総額（管理費含)"]
    col2_w = [90, 30, 35, 35]
    pdf.set_font("NotoSans", "B", 10)
    pdf.set_fill_color(220, 240, 255)
    for i, h in enumerate(headers2):
        pdf.cell(col2_w[i], 7, h, 1, 0, "C", 1)
    pdf.ln(7)
    pdf.set_font("NotoSans", "", 10)
    pdf.cell(col2_w[0], 8, "①物件価格＋諸費用フルローン", 1, 0, "L")
    pdf.cell(col2_w[1], 8, f"{(price_yen+total_expenses):,} 円", 1, 0, "R")
    pdf.cell(col2_w[2], 8, f"{monthly1:,} 円", 1, 0, "R")
    pdf.set_font("NotoSans", "", 9.5)
    pdf.cell(col2_w[3], 8, f"{(monthly1+kanri_month):,} 円", 1, 1, "R")
    pdf.set_font("NotoSans", "", 10)
    pdf.cell(col2_w[0], 8, "②物件価格のみ借入", 1, 0, "L")
    pdf.cell(col2_w[1], 8, f"{price_yen:,} 円", 1, 0, "R")
    pdf.cell(col2_w[2], 8, f"{monthly2:,} 円", 1, 0, "R")
    pdf.set_font("NotoSans", "", 9.5)
    pdf.cell(col2_w[3], 8, f"{(monthly2+kanri_month):,} 円", 1, 1, "R")
    pdf.ln(2)

    # 契約時必要資金表示
    pdf.set_font("NotoSans", "B", 11)
    pdf.cell(0, 8, f"契約時必要資金（概算）＝ 手付金 ＋ 契約書印紙代 ＋ 仲介手数料(半金) ＝ {contract_need:,} 円",
             ln=1, align="L")

    return pdf.output(dest="S").encode("latin1")

# ダウンロードボタン
if st.button("📄 PDFダウンロード"):
    try:
        pdf_bytes = make_pdf()
        st.download_button(
            label="資金計画書（諸費用明細）.pdf をダウンロード",
            data=pdf_bytes,
            file_name="資金計画書_諸費用明細.pdf",
            mime="application/pdf",
        )
        st.success("PDFを生成しました。")
    except Exception as e:
        st.error(f"PDF生成エラー: {e}")