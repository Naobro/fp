# /pages/住宅ローン提案.py
# 住宅ローン 提案シミュレーター（reportlab不使用 / fpdf2版）
# 要件：
# - st.session_state は一切参照しない
# - “初期値に戻す” 概念なし（保存が無ければエラーで停止）
# - 保存は「金利を保存」ボタンでのみ
# - パスワード一致後に編集UIを表示（状態フラグ不使用）
# - 直感的な固定キー（ASCII）のみ使用

import os
import io
import json
from pathlib import Path

import streamlit as st
from fpdf import FPDF

# ===== 画面設定 =====
st.set_page_config(page_title="住宅ローン 提案シミュレーター", layout="wide")

# ===== フォント探索 =====
def _resolve_font_path() -> str | None:
    here = Path(__file__).resolve().parent
    candidates = [
        here / "NotoSansJP-Regular.ttf",
        here / "fonts" / "NotoSansJP-Regular.ttf",
        Path.cwd() / "NotoSansJP-Regular.ttf",
        Path.cwd() / "fonts" / "NotoSansJP-Regular.ttf",
    ]
    for p in candidates:
        try:
            if p.exists() and p.is_file():
                return str(p.resolve())
        except Exception:
            pass
    return None

# ===== 固定定義 =====
BANKS = ["SBI新生銀行", "三菱UFJ銀行", "PayPay銀行", "じぶん銀行", "住信SBI銀行"]
PLANS = ["一般団信", "がん50", "がん100", "三大疾病", "7大疾病", "全疾病"]

SPECIAL_NOTES = {
    "SBI新生銀行": ["125%ルールなし", "ZEH -0.1%"],
    "三菱UFJ銀行": ["三大疾病50%", "ワイド団信+0.3%"],
    "PayPay銀行":  ["がん50以上で全疾病・失業補償", "ソフトバンク割 最大-0.13%", "125%ルールなし"],
    "じぶん銀行":  ["ワイド団信+0.3%", "じぶん割 最大-0.15%"],
    "住信SBI銀行": ["全疾病保障+三大疾病50%標準付帯", "125%ルールなし"],
}

def extra_rate_percent(bank: str, plan: str, age: int) -> float:
    if bank == "SBI新生銀行":
        return 0.1 if plan == "がん100" else 0.0
    if bank == "三菱UFJ銀行":
        return {"がん50": 0.15, "7大疾病": 0.3, "全疾病": 0.5}.get(plan, 0.0)
    if bank == "PayPay銀行":
        return {"がん50": 0.05, "がん100": 0.15}.get(plan, 0.0)
    if bank == "じぶん銀行":
        return {"がん100": 0.054, "7大疾病": 0.1}.get(plan, 0.0)
    if bank == "住信SBI銀行":
        return (0.2 if age < 40 else 0.4) if plan == "三大疾病" else 0.0
    return 0.0

# ===== 保存（SQLite） =====
import sqlite3
from datetime import datetime

SAVE_DIR = "data"
os.makedirs(SAVE_DIR, exist_ok=True)
DB_PATH = os.path.join(SAVE_DIR, "manual_rates.sqlite3")

def _db_conn():
    return sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)

def _init_db():
    try:
        with _db_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mortgage_rates (
                    bank TEXT PRIMARY KEY,
                    rate REAL NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
    except Exception:
        pass

_init_db()

def load_manual_rates() -> dict:
    """
    DBから現在の金利を読み込む（Streamlit無関係）。
    戻り値: {銀行名: 金利(％のfloat)}
    """
    try:
        with _db_conn() as conn:
            cur = conn.execute("SELECT bank, rate FROM mortgage_rates")
            rows = cur.fetchall()
        out: dict[str, float] = {}
        for bank, rate in rows:
            try:
                out[str(bank)] = float(rate)
            except Exception:
                continue
        return out
    except Exception:
        return {}

def save_manual_rates(d: dict) -> bool:
    """
    『金利を保存』押下時のみ保存。
    - 空欄/None は無視（既存値を保持）
    - 0.000 を含む有効な数値は保存
    - 既存レコードと比較し、変更があればUPSERT
    """
    try:
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"

        # 既存の取得
        existing: dict[str, float] = {}
        with _db_conn() as conn:
            cur = conn.execute("SELECT bank, rate FROM mortgage_rates")
            for bank, rate in cur.fetchall():
                try:
                    existing[str(bank)] = float(rate)
                except Exception:
                    continue

        # 変更検出とUPSERT
        updates: list[tuple[str, float, str]] = []
        for b in BANKS:
            if b not in d:
                continue
            v = d[b]
            if v is None:
                continue
            try:
                fv = float(v)
            except Exception:
                continue
            if (b not in existing) or (existing[b] != fv):
                updates.append((b, fv, now))

        if not updates:
            return False

        with _db_conn() as conn:
            conn.executemany(
                """
                INSERT INTO mortgage_rates (bank, rate, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(bank) DO UPDATE SET
                    rate=excluded.rate,
                    updated_at=excluded.updated_at
                """,
                updates,
            )
        return True
    except Exception:
        return False

# ===== 計算 =====
# ===== 計算 =====
def monthly_payment(principal: float, annual_rate: float, years: int) -> float:
    r = annual_rate / 12.0
    n = years * 12
    if r == 0:
        return principal / n
    return principal * r / (1 - (1 + r) ** (-n))

def sbi_effective_percent(base_percent: float, ltv: float, years: int) -> float:
    rate = float(base_percent)
    if ltv <= 0.80:
        rate += -0.09
    elif ltv > 1.00:
        rate += 0.07
    if 36 <= years <= 40:
        rate += 0.07
    elif years >= 41:
        rate += 0.15
    return rate

def borrowing_limit(income: float, exam_rate: float, ratio: float, age_now: int) -> int:
    exam_years = min(35, 79 - age_now)
    annual = income * ratio
    m = annual / 12
    r = exam_rate / 12
    n = exam_years * 12
    raw = (m * n) if r == 0 else (m * (1 - (1 + r) ** -n) / r)
    return int(raw // 100000 * 100000)

# ===== UI：基本入力 =====
st.title("住宅ローン 提案シミュレーター")

col1, col2, col3, col4 = st.columns(4)
with col1:
    principal = st.number_input("借入額 (万円)", min_value=500, max_value=100000, value=5000, key="inp_principal") * 10000
with col2:
    self_fund = st.number_input("自己資金 (万円)", min_value=0, max_value=100000, value=200, key="inp_self_fund") * 10000
with col3:
    annual_income = st.number_input("年収 (万円)", min_value=100, max_value=10000, value=1000, key="inp_income") * 10000
with col4:
    age = st.number_input("年齢", min_value=18, max_value=80, value=35, key="inp_age")

max_year = max(1, 79 - int(age))
years = st.slider("返済期間 (年)", min_value=1, max_value=max_year, value=min(35, max_year), key="inp_years")

# LTV概算
property_price_guess = (principal + self_fund) / 1.07 if 1.07 != 0 else (principal + self_fund)
ltv = principal / property_price_guess if property_price_guess else 1.0

# ===== 金利の読込 =====
rates = load_manual_rates()
_missing = [b for b in BANKS if b not in rates or str(rates.get(b, "")).strip() == ""]
if _missing:
    st.warning("未設定の金利があるため、該当銀行のセルは空欄になります： " + " / ".join(_missing))

# ===== 借入上限額 =====
banks_exam = {
    "SBI新生銀行": {"審査金利": 0.03,   "返済比率": 0.40},
    "三菱UFJ銀行": {"審査金利": 0.0354, "返済比率": 0.35},
    "PayPay銀行":  {"審査金利": 0.03,   "返済比率": 0.40},
    "じぶん銀行":  {"審査金利": 0.0257, "返済比率": 0.35},
    "住信SBI銀行": {"審査金利": 0.0325, "返済比率": 0.35},
}
limits = {}
rows_limit_html = []
for bank, info in banks_exam.items():
    lim = borrowing_limit(annual_income, info["審査金利"], info["返済比率"], int(age))
    limits[bank] = lim
    rows_limit_html.append((bank, f"{int(lim // 10000):,} 万円"))

st.subheader("💰 年収からの借入上限額")
st.markdown(
    "<style>.blimit th, .blimit td {border:1.2px solid #aaa; padding:12px; font-size:18px;} .blimit th{background:#F2F6FA;} .blimit{border-collapse:collapse; width:480px; margin-bottom:20px;}</style>",
    unsafe_allow_html=True
)
tbl = "<table class='blimit'><thead><tr><th style='width:250px;text-align:center'>銀行名</th><th style='width:230px;text-align:center'>借入上限額</th></tr></thead><tbody>"
for bank, val in rows_limit_html:
    tbl += f"<tr><td align='center'>{bank}</td><td align='right'>{val}</td></tr>"
tbl += "</tbody></table>"
st.markdown(tbl, unsafe_allow_html=True)

# ===== 返済額テーブル計算 =====
def build_table(principal: float, years_req: int, age_now: int):
    def cap_years(bank_name: str, req: int) -> int:
        y = min(79 - age_now, req)
        if bank_name in ["SBI新生銀行", "三菱UFJ銀行"]:
            y = min(y, 35)
        return y

    table_rows_local = []
    highlights_local = []

    for plan in PLANS:
        row = []
        vals = []
        for bank in BANKS:
            if principal > limits.get(bank, 0):
                row.append({"rate": None, "monthly": None, "years": None})
                continue
            if bank not in rates:
                row.append({"rate": None, "monthly": None, "years": None})
                continue
            if plan != "一般団信" and extra_rate_percent(bank, plan, age_now) == 0.0:
                row.append({"rate": None, "monthly": None, "years": None})
                continue

            y = cap_years(bank, years_req)
            try:
                base_percent_saved = float(rates[bank])
            except Exception:
                row.append({"rate": None, "monthly": None, "years": None})
                continue

            if bank == "住信SBI銀行":
                eff_pct = sbi_effective_percent(base_percent_saved, ltv, y)
                base = eff_pct / 100.0
            else:
                base = base_percent_saved / 100.0
                if bank in ["PayPay銀行", "じぶん銀行"] and y > 35:
                    base += 0.10 / 100.0

            add = extra_rate_percent(bank, plan, age_now) / 100.0
            m = monthly_payment(principal, base + add, y)
            row.append({"rate": base + add, "monthly": m, "years": y})
            vals.append((len(row) - 1, m))

        mins = set()
        if vals:
            mv = min(v for _, v in vals)
            for idx, v in vals:
                if abs(v - mv) < 0.5:
                    mins.add(idx)

        table_rows_local.append(row)
        highlights_local.append(mins)

    # 最長50年行
    row50_local = []
    vals50 = []
    for bank in BANKS:
        if principal > limits.get(bank, 0) or bank in ["SBI新生銀行", "三菱UFJ銀行"]:
            row50_local.append({"rate": None, "monthly": None, "years": None})
            continue
        if bank not in rates:
            row50_local.append({"rate": None, "monthly": None, "years": None})
            continue

        y = min(79 - age_now, 50)
        try:
            base_percent_saved = float(rates[bank])
        except Exception:
            row50_local.append({"rate": None, "monthly": None, "years": None})
            continue

        if bank == "住信SBI銀行":
            eff_pct = sbi_effective_percent(base_percent_saved, ltv, y)
            base = eff_pct / 100.0
        else:
            base = base_percent_saved / 100.0
            if bank in ["PayPay銀行", "じぶん銀行"] and y > 35:
                base += 0.10 / 100.0

        add = extra_rate_percent(bank, "一般団信", age_now) / 100.0
        m = monthly_payment(principal, base + add, y)
        row50_local.append({"rate": base + add, "monthly": m, "years": y})
        vals50.append((len(row50_local) - 1, m))

    mins50 = set()
    if vals50:
        mv = min(v for _, v in vals50)
        for idx, v in vals50:
            if abs(v - mv) < 0.5:
                mins50.add(idx)

    return table_rows_local, highlights_local, row50_local, mins50

table_rows, highlights, row50, mins50 = build_table(principal, int(years), int(age))

# ===== HTMLテーブル（画面表示） =====
def td_cell(d: dict, is_min: bool, wcss: str) -> str:
    r, m, y = d["rate"], d["monthly"], d["years"]
    base = "text-align:center;vertical-align:middle;"
    bg = "background-color:#FFF8C8;" if is_min else ""
    if r is None:
        return f"<td style='{wcss}{base}'></td>"
    return (
        f"<td style='{wcss}height:68px;{base}{bg}'>"
        f"<div style='font-size:22px;font-weight:bold;color:#1B232A'>{r*100:.3f}%</div>"
        f"<div style='font-size:22px;font-weight:bold;color:#226BB3'>¥{m:,.0f}</div>"
        f"<div style='font-size:14px;color:#666;'>({y}年返済)</div>"
        f"</td>"
    )

plan_w = "min-width:220px;max-width:220px;width:220px;"
bank_w = "min-width:180px;max-width:180px;width:180px;"
html = """
<style>
.loan-table, .loan-table th, .loan-table td {border:1.2px solid #aaa; border-collapse: collapse;}
.loan-table th, .loan-table td {padding: 13px;}
.loan-table {background-color:#fff; width:100%; table-layout:fixed;}
.loan-table th {background-color:#F2F6FA; font-size:18px;}
.loan-table td {font-size:18px;}
</style>
<table class="loan-table">
<thead><tr>
"""
html += f"<th style='{plan_w}text-align:center;font-size:18px;'>プラン</th>"
for b in BANKS:
    html += f"<th style='{bank_w}text-align:center;font-size:18px'>{b}</th>"
html += "</tr></thead><tbody>"

for i, plan in enumerate(PLANS):
    html += f"<tr><td style='{plan_w}text-align:center;font-weight:bold;font-size:18px;'>{plan}</td>"
    for col_idx, _ in enumerate(BANKS):
        cell = table_rows[i][col_idx]
        html += td_cell(cell, (col_idx in highlights[i] and cell["monthly"] is not None), bank_w)
    if plan == "一般団信":
        html += f"<tr><td style='{plan_w}text-align:center;font-weight:bold;font-size:17px;background-color:#F9F6EF;'>最長50年</td>"
        for col_idx, _ in enumerate(BANKS):
            cell = row50[col_idx]
            html += td_cell(cell, (col_idx in mins50 and cell["monthly"] is not None), bank_w)
        html += "</tr>"

html += f"<tr><td style='{plan_w}text-align:center;font-weight:bold;font-size:14px;background-color:#FCF9F0;'>特記事項</td>"
for bank in BANKS:
    html += f"<td style='{bank_w}font-size:12px;text-align:left;vertical-align:top;background-color:#FCF9F0;'>{'<br>'.join(SPECIAL_NOTES[bank])}</td>"
html += "</tr></tbody></table>"
st.markdown(html, unsafe_allow_html=True)

# ===== PDFヘルパ =====
def _pdf_to_bytesio(pdf) -> io.BytesIO:
    pdf_bytes = pdf.output(dest="S")
    if isinstance(pdf_bytes, memoryview):
        pdf_bytes = pdf_bytes.tobytes()
    elif not isinstance(pdf_bytes, (bytes, bytearray)):
        pdf_bytes = bytes(pdf_bytes)
    out = io.BytesIO(pdf_bytes)
    out.seek(0)
    return out

# ===== PDF出力（罫線を先描画→テキスト流し込みでズレ防止） =====
def create_pdf() -> io.BytesIO:
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()

    resolved = _resolve_font_path()
    if not resolved:
        searched = [
            "NotoSansJP-Regular.ttf",
            "fonts/NotoSansJP-Regular.ttf",
            "./NotoSansJP-Regular.ttf",
            "./fonts/NotoSansJP-Regular.ttf",
        ]
        raise FileNotFoundError("PDF用フォントが見つかりません：\n - " + "\n - ".join(searched))

    pdf.add_font("NotoSansJP", "", resolved, uni=True)
    pdf.set_font("NotoSansJP", size=14)

    # タイトル
    pdf.cell(0, 10, txt="住宅ローン提案書", ln=1, align="C")
    pdf.set_font("NotoSansJP", size=11)
    pdf.cell(0, 8, txt=f"■ 借入金額：¥{principal:,.0f}", ln=1, align="C")
    pdf.ln(2)

    # 列幅・高さ
    plan_w_mm = 45
    bank_w_mm = 40
    line_h = 5.4                 # 本体セルの1行高
    cell_h = line_h * 3          # 本体セルは3行固定（% / 月額 / (年)）
    x_left = 10
    y_top = pdf.get_y()

    # ヘッダ行
    pdf.set_font("NotoSansJP", size=10)
    pdf.set_fill_color(242, 246, 250)
    pdf.rect(x_left, y_top, plan_w_mm, 10, style="F")
    pdf.rect(x_left, y_top, plan_w_mm, 10)
    pdf.set_xy(x_left, y_top)
    pdf.multi_cell(plan_w_mm, 10, "プラン", align="C", border=0)

    x = x_left + plan_w_mm
    for b in BANKS:
        pdf.rect(x, y_top, bank_w_mm, 10, style="F")
        pdf.rect(x, y_top, bank_w_mm, 10)
        pdf.set_xy(x, y_top)
        pdf.multi_cell(bank_w_mm, 10, b, align="C", border=0)
        x += bank_w_mm

    y_cursor = y_top + 10  # ヘッダの下から本体

    def _cell_text(d: dict):
        if d["rate"] is None:
            return ["", "", ""]
        return [f"{d['rate']*100:.3f}%", f"¥{d['monthly']:,.0f}", f"({d['years']}年)"]

    def _draw_row(label: str, cells: list[dict], y: float, fill_rgb: tuple | None = None, label_fill: tuple | None = None):
        # 見出しセル
        if label_fill:
            pdf.set_fill_color(*label_fill)
            pdf.rect(x_left, y, plan_w_mm, cell_h, style="F")
        pdf.rect(x_left, y, plan_w_mm, cell_h)
        pdf.set_xy(x_left, y + (cell_h - line_h) / 2)  # 真ん中行に寄せ
        pdf.multi_cell(plan_w_mm, line_h, label, align="C", border=0)

        # 銀行セル：枠線→テキスト
        x = x_left + plan_w_mm
        if fill_rgb:
            pdf.set_fill_color(*fill_rgb)
        for d in cells:
            if fill_rgb:
                pdf.rect(x, y, bank_w_mm, cell_h, style="F")
            pdf.rect(x, y, bank_w_mm, cell_h)
            t1, t2, t3 = _cell_text(d)
            pdf.set_xy(x, y)
            pdf.multi_cell(bank_w_mm, line_h, t1, align="C", border=0)
            pdf.set_xy(x, y + line_h)
            pdf.multi_cell(bank_w_mm, line_h, t2, align="C", border=0)
            pdf.set_xy(x, y + line_h * 2)
            pdf.multi_cell(bank_w_mm, line_h, t3, align="C", border=0)
            x += bank_w_mm

    # 本体6行＋「最長50年」行
    pdf.set_font("NotoSansJP", size=10)
    for i, plan in enumerate(PLANS):
        _draw_row(plan, table_rows[i], y_cursor)
        y_cursor += cell_h
        if plan == "一般団信":
            _draw_row("最長50年", row50, y_cursor, fill_rgb=(249, 246, 239), label_fill=(249, 246, 239))
            y_cursor += cell_h

    # 特記事項行（内容に合わせて高さを自動調整）
    pdf.set_font("NotoSansJP", size=9)
    notes_line_h = 5.2      # 1行の高さ（必要なら 4.8〜5.2 で微調整）
    pad_v = 1.5             # 上下の余白
    max_lines = max(len(SPECIAL_NOTES[b]) for b in BANKS)
    notes_h = max_lines * notes_line_h + pad_v * 2
    y_notes = y_cursor + 2  # 本体テーブルとの間に少し余白

    # 見出しセル
    pdf.set_fill_color(252, 249, 240)
    pdf.rect(x_left, y_notes, plan_w_mm, notes_h, style="F")
    pdf.rect(x_left, y_notes, plan_w_mm, notes_h)
    pdf.set_xy(x_left, y_notes + (notes_h - notes_line_h) / 2)
    pdf.multi_cell(plan_w_mm, notes_line_h, "特記事項", align="C", border=0)

    # 各銀行セル（全列を最大行数の高さで統一）
    x = x_left + plan_w_mm
    for b in BANKS:
        txt = "\n".join(SPECIAL_NOTES[b])   # 行ごと改行
        pdf.rect(x, y_notes, bank_w_mm, notes_h)        # 先に枠線
        pdf.set_xy(x + 1, y_notes + pad_v)              # 少し内側に文字
        pdf.multi_cell(bank_w_mm - 2, notes_line_h, txt, align="L", border=0)
        x += bank_w_mm

    # 次要素のためのカーソル整理
    pdf.set_xy(x_left, y_notes + notes_h + 2)

    return _pdf_to_bytesio(pdf)

# ===== ダウンロードUI =====
if st.button("📄 PDFを作成", key="btn_make_pdf"):
    try:
        pdf_buf = create_pdf()
        st.download_button(
            "📥 PDFをダウンロード",
            data=pdf_buf,
            file_name="住宅ローン提案書.pdf",
            mime="application/pdf",
            key="btn_dl_pdf",
        )
    except FileNotFoundError as e:
        st.error(str(e))
    except Exception as e:
        st.error(f"PDFの作成でエラー：{e}")

# ===== 金利修正（パスワード一致で表示） =====
st.markdown("---")
pwd = st.text_input("🔒 営業担当パスワード", type="password", key="pwd_rates_edit")
exp_open = (pwd == "naoki0510")

with st.expander("🔧 金利を修正する（営業担当専用）", expanded=exp_open):
    if not exp_open:
        st.info("パスワードが一致すると編集欄が開きます。")
    else:
        bank_key_map = {
            "SBI新生銀行": "mortgage_rate_sbi_shinsei",
            "三菱UFJ銀行": "mortgage_rate_mufg",
            "PayPay銀行":  "mortgage_rate_paypay",
            "じぶん銀行":  "mortgage_rate_jibun",
            "住信SBI銀行": "mortgage_rate_sumishin_sbi",
        }

        current_saved = load_manual_rates()
        cols = st.columns(len(BANKS))
        new_rates_dict = {}

        for bank, col in zip(BANKS, cols):
            with col:
                key = bank_key_map[bank]
                # 保存済みがあればその値を文字列で初期化、なければ空欄（0.000を入れない）
                init_str = "" if bank not in current_saved else f"{float(current_saved[bank]):.3f}"
                s = st.text_input(
                    f"{bank}（年利％）",
                    value=init_str,
                    key=key,
                    placeholder="未設定（例: 0.389）"
                )
                # 文字列→float（空欄や不正は None 扱い＝保存時に無視）
                try:
                    new_rates_dict[bank] = float(s) if s.strip() != "" else None
                except Exception:
                    new_rates_dict[bank] = None

        st.markdown("")
        if st.button("💾 金利を保存", type="primary", key="btn_rates_save"):
            if save_manual_rates(new_rates_dict):
                st.success("✅ 金利を保存しました（上部の表にも反映されます）")
            else:
                st.error("❌ 保存に失敗しました")
