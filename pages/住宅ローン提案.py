# /pages/住宅ローン提案.py
# 住宅ローン 提案シミュレーター（初期値なし・st.session_state未使用・手動保存のみ・パスワード一致で編集表示）

import os
import io
import json
from datetime import datetime

import streamlit as st
import pandas as pd

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ========== 画面設定 ==========
st.set_page_config(page_title="住宅ローン 提案シミュレーター", layout="wide")

# ========== フォント ==========
FONT_PATH = "NotoSansJP-Regular.ttf"
try:
    pdfmetrics.registerFont(TTFont('NotoSansJP', FONT_PATH))
except Exception as e:
    st.error(f"フォント読み込み失敗: {e}\n{FONT_PATH} をプロジェクト直下に置いてください。")
    st.stop()

def jp_style(size=11, font_name='NotoSansJP', align='CENTER', leading=15, bold=False, color=colors.black):
    am = {'LEFT': 0, 'CENTER': 1, 'RIGHT': 2}
    return ParagraphStyle(
        name=f'jps_{size}_{align}',
        fontName=font_name, fontSize=size, leading=leading,
        alignment=am.get(align, 1),
        fontWeight=("bold" if bold else "normal"),
        textColor=color, spaceAfter=2, spaceBefore=2
    )

# ========== 固定定義 ==========
BANKS = ["SBI新生銀行", "三菱UFJ銀行", "PayPay銀行", "じぶん銀行", "住信SBI銀行"]
PLANS = ["一般団信", "がん50", "がん100", "三大疾病", "7大疾病", "全疾病"]

SPECIAL_NOTES = {
    "SBI新生銀行": ["125%ルールなし", "ZEH -0.1%"],
    "三菱UFJ銀行": ["三大疾病50%", "ワイド団信+0.3%"],
    "PayPay銀行":  ["がん50以上で全疾病・失業補償", "ソフトバンク割 最大-0.13%", "125%ルールなし"],
    "じぶん銀行":  ["ワイド団信+0.3%", "じぶん割 最大-0.15%"],
    "住信SBI銀行": ["全疾病保障+三大疾病50%標準付帯", "125%ルールなし"],
}

def extra_rate(bank: str, plan: str, age: int) -> float:
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

# ========== 保存（JSON） ==========
SAVE_DIR = "data"
SAVE_PATH = os.path.join(SAVE_DIR, "manual_rates.json")
os.makedirs(SAVE_DIR, exist_ok=True)

def load_manual_rates() -> dict:
    """
    保存済み金利のみ読む。無ければ空{}（初期値ゼロも出さない）。
    """
    try:
        if os.path.exists(SAVE_PATH):
            with open(SAVE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            out = {}
            if isinstance(data, dict):
                for k, v in data.items():
                    try:
                        out[k] = float(v)
                    except Exception:
                        pass
            return out
    except Exception:
        pass
    return {}

def save_manual_rates(d: dict) -> bool:
    """
    『金利を保存』を押した時だけ、入力された数値を保存（上書き）。
    """
    try:
        purified = {b: float(d[b]) for b in BANKS if b in d and str(d[b]).strip() != ""}
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(purified, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

# ========== 計算関数 ==========
def monthly_payment(principal, annual_rate, years):
    r = annual_rate / 12.0
    n = years * 12
    if r == 0:
        return principal / n
    return principal * r / (1 - (1 + r) ** -n)

def sbi_effective_percent(base_percent: float, ltv: float, years: int) -> float:
    rate = float(base_percent)
    if ltv <= 0.80: rate += -0.09
    elif ltv > 1.00: rate += 0.07
    if 36 <= years <= 40: rate += 0.07
    elif years >= 41: rate += 0.15
    return rate

def borrowing_limit(income, exam_rate, ratio, age_now):
    exam_years = min(35, 79 - age_now)
    annual = income * ratio
    m = annual / 12
    r = exam_rate / 12
    n = exam_years * 12
    raw = (m * n) if r == 0 else (m * (1 - (1 + r) ** -n) / r)
    return int(raw // 100000 * 100000)

# ========== UI：基本入力（ASCIIキー固定） ==========
st.title("住宅ローン 提案シミュレーター")

c1, c2, c3, c4 = st.columns(4)
with c1:
    principal = st.number_input("借入額 (万円)", min_value=500, max_value=100000, value=5000, key="inp_principal") * 10000
with c2:
    self_fund = st.number_input("自己資金 (万円)", min_value=0, max_value=100000, value=200, key="inp_self_fund") * 10000
with c3:
    annual_income = st.number_input("年収 (万円)", min_value=100, max_value=10000, value=1000, key="inp_income") * 10000
with c4:
    age = st.number_input("年齢", min_value=18, max_value=80, value=35, key="inp_age")

max_year = max(1, 79 - int(age))
years = st.slider("返済期間 (年)", min_value=1, max_value=max_year, value=min(35, max_year), key="inp_years")

# 概算LTV
property_price_guess = (principal + self_fund) / 1.07 if 1.07 != 0 else (principal + self_fund)
ltv = principal / property_price_guess if property_price_guess else 1.0

# ========== 金利の読込 ==========
rates = load_manual_rates()  # 空なら空dictのまま

# ========== 認証：一致時のみ編集UI（セッション状態は参照しない） ==========
ADMIN_PASSWORD = "naoki0510"

st.markdown("---")
with st.expander("🔧 金利を修正する（営業担当専用）", expanded=False):
    st.warning("🔒 営業担当者専用。パスワード一致で編集欄が表示されます。")
    pw = st.text_input("パスワード", type="password", key="pw_input_inline")

    if pw == ADMIN_PASSWORD:
        st.success("✅ 認証成功 - 入力値は『金利を保存』ボタンでのみ保存（自動保存なし）")
        edited = {}
        cols = st.columns(5)
        for i, bank in enumerate(BANKS):
            with cols[i]:
                current = float(rates[bank]) if bank in rates else 0.0  # 未保存なら0.000表示（初期値の概念なし）
                edited[bank] = st.number_input(f"{bank}（％）", value=current, step=0.001, format="%.3f", key=f"rate_{i}")

        if st.button("💾 金利を保存", type="primary", key="btn_save_rates"):
            if save_manual_rates(edited):
                st.success("✅ 保存しました。以後の計算に反映されます。")
            else:
                st.error("❌ 保存に失敗しました。権限やパスをご確認ください。")
    elif pw:
        st.error("❌ パスワードが違います。")

# ========== 金利が未設定の銀行があれば停止 ==========
missing = [b for b in BANKS if b not in rates]
if missing:
    st.error("金利未設定の銀行があります。『金利を修正する』で **全行** の金利（％）を入力し、保存してください。")
    st.write("未設定：", "、".join(missing))
    st.stop()

# ========== 借入上限 ==========
banks_info = {
    "SBI新生銀行": {"審査金利": 0.03,   "返済比率": 0.40},
    "三菱UFJ銀行": {"審査金利": 0.0354, "返済比率": 0.35},
    "PayPay銀行":  {"審査金利": 0.03,   "返済比率": 0.40},
    "じぶん銀行":  {"審査金利": 0.0257, "返済比率": 0.35},
    "住信SBI銀行": {"審査金利": 0.0325, "返済比率": 0.35},
}
limit_amounts, limit_rows = {}, []
for bank, info in banks_info.items():
    limit = borrowing_limit(annual_income, info["審査金利"], info["返済比率"], int(age))
    limit_amounts[bank] = limit
    limit_rows.append([bank, f"{int(limit // 10000):,} 万円"])
st.subheader("💰 年収からの借入上限額")
st.markdown(
    "<style>.blimit th, .blimit td {border:1.2px solid #aaa; padding:12px; font-size:18px;} .blimit th{background:#F2F6FA;} .blimit{border-collapse:collapse; width:480px; margin-bottom:20px;}</style>",
    unsafe_allow_html=True
)
tbl = "<table class='blimit'><thead><tr><th style='width:250px;text-align:center'>銀行名</th><th style='width:230px;text-align:center'>借入上限額</th></tr></thead><tbody>"
for bank, val in limit_rows:
    tbl += f"<tr><td align='center'>{bank}</td><td align='right'>{val}</td></tr>"
tbl += "</tbody></table>"
st.markdown(tbl, unsafe_allow_html=True)

# ========== 返済額テーブル計算 ==========
def build_table():
    rows, highlights = [], []

    def cap_years(bank_name: str, req: int) -> int:
        y = min(79 - int(age), req)
        if bank_name in ["SBI新生銀行", "三菱UFJ銀行"]:
            y = min(y, 35)
        return y

    for plan in PLANS:
        row, vals = [], []
        for bank in BANKS:
            if principal > limit_amounts.get(bank, 0):
                row.append({"rate": None, "monthly": None, "years": None}); continue

            # 一般団信以外は extra_rate が0でも提供無しとして空欄にする
            if plan != "一般団信" and extra_rate(bank, plan, int(age)) == 0.0:
                row.append({"rate": None, "monthly": None, "years": None}); continue

            y = cap_years(bank, int(years))

            if bank == "住信SBI銀行":
                eff_pct = sbi_effective_percent(float(rates[bank]), ltv, y)  # ％
                base = eff_pct / 100.0
            else:
                base = float(rates[bank]) / 100.0
                if bank in ["PayPay銀行", "じぶん銀行"] and y > 35:
                    base += 0.10 / 100.0

            add = extra_rate(bank, plan, int(age)) / 100.0
            m = monthly_payment(principal, base + add, y)
            row.append({"rate": base + add, "monthly": m, "years": y})
            vals.append((len(row) - 1, m))

        mins = set()
        if vals:
            mv = min(v for _, v in vals)
            for idx, v in vals:
                if abs(v - mv) < 0.5:
                    mins.add(idx)

        rows.append(row); highlights.append(mins)

    # 最長50年（一般団信の下段）
    row50, vals50 = [], []
    for bank in BANKS:
        if principal > limit_amounts.get(bank, 0) or bank in ["SBI新生銀行", "三菱UFJ銀行"]:
            row50.append({"rate": None, "monthly": None, "years": None}); continue

        y = min(79 - int(age), 50)
        if bank == "住信SBI銀行":
            eff_pct = sbi_effective_percent(float(rates[bank]), ltv, y)
            base = eff_pct / 100.0
        else:
            base = float(rates[bank]) / 100.0
            if bank in ["PayPay銀行", "じぶん銀行"] and y > 35:
                base += 0.10 / 100.0

        add = extra_rate(bank, "一般団信", int(age)) / 100.0
        m = monthly_payment(principal, base + add, y)
        row50.append({"rate": base + add, "monthly": m, "years": y})
        vals50.append((len(row50) - 1, m))

    mins50 = set()
    if vals50:
        mv = min(v for _, v in vals50)
        for idx, v in vals50:
            if abs(v - mv) < 0.5:
                mins50.add(idx)

    return rows, highlights, row50, mins50

table_rows, highlights, row50, mins50 = build_table()

# ========== HTMLテーブル描画 ==========
def td_cell(d, is_min, wcss):
    r, m, y = d["rate"], d["monthly"], d["years"]
    base = "text-align:center;vertical-align:middle;"
    bg = "background-color:#FFF8C8;" if is_min else ""
    if r is None:
        return f"<td style='{wcss}{base}'></td>"
    return (f"<td style='{wcss}height:68px;{base}{bg}'>"
            f"<div style='font-size:22px;font-weight:bold;color:#1B232A'>{r*100:.3f}%</div>"
            f"<div style='font-size:22px;font-weight:bold;color:#226BB3'>¥{m:,.0f}</div>"
            f"<div style='font-size:14px;color:#666;'>({y}年返済)</div></td>")

plan_w = "min-width:220px;max-width:220px;width:220px;"
bank_w = "min-width:180px;max-width:180px;width:180px;"
html = f"""
<style>
.loan-table, .loan-table th, .loan-table td {{border:1.2px solid #aaa; border-collapse: collapse;}}
.loan-table th, .loan-table td {{padding: 13px;}}
.loan-table {{background-color:#fff; width:100%; table-layout:fixed;}}
.loan-table th {{background-color:#F2F6FA; font-size:18px;}}
.loan-table td {{font-size:18px;}}
</style>
<table class="loan-table">
<thead><tr><th style='{plan_w}text-align:center;font-size:18px;'>プラン</th>""" + \
"".join([f"<th style='{bank_w}text-align:center;font-size:18px'>{b}</th>" for b in BANKS]) + \
"</tr></thead><tbody>"

for i, plan in enumerate(PLANS):
    html += f"<tr><td style='{plan_w}text-align:center;font-weight:bold;font-size:18px;'>{plan}</td>"
    for col_idx, bank in enumerate(BANKS):
        cell = table_rows[i][col_idx]
        html += td_cell(cell, (col_idx in highlights[i] and cell["monthly"] is not None), bank_w)
    if plan == "一般団信":
        html += f"<tr><td style='{plan_w}text-align:center;font-weight:bold;font-size:17px;background-color:#F9F6EF;'>最長50年</td>"
        for col_idx, bank in enumerate(BANKS):
            cell = row50[col_idx]
            html += td_cell(cell, (col_idx in mins50 and cell["monthly"] is not None), bank_w)
        html += "</tr>"

html += f"<tr><td style='{plan_w}text-align:center;font-weight:bold;font-size:14px;background-color:#FCF9F0;'>特記事項</td>"
for bank in BANKS:
    html += f"<td style='{bank_w}font-size:12px;text-align:left;vertical-align:top;background-color:#FCF9F0;'>{'<br>'.join(SPECIAL_NOTES[bank])}</td>"
html += "</tr></tbody></table>"
st.markdown(html, unsafe_allow_html=True)

# ========== PDF出力 ==========
def create_pdf():
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=10*mm, rightMargin=10*mm,
                            topMargin=13*mm, bottomMargin=13*mm)
    st_title = jp_style(size=21, align='CENTER', leading=31, bold=True)
    st_head  = jp_style(size=13, align='CENTER', leading=24, bold=True, color=colors.HexColor('#226BB3'))
    st_cell  = jp_style(size=12, align='CENTER', leading=24)
    st_cellb = jp_style(size=15, align='CENTER', leading=19, bold=True, color=colors.HexColor('#1B232A'))

    elems = []
    elems.append(Paragraph("住宅ローン提案書", st_title))
    elems.append(Spacer(1, 5*mm))
    elems.append(Paragraph(f"<b>■ 借入金額：¥{principal:,.0f}</b>", st_head))
    elems.append(Spacer(1, 8*mm))

    data = []
    header = [Paragraph("プラン", st_head)] + [Paragraph(b, st_head) for b in BANKS]
    data.append(header)

    for i, plan in enumerate(PLANS):
        r = [Paragraph(plan, st_cell)]
        for col_idx, bank in enumerate(BANKS):
            d = table_rows[i][col_idx]
            if d["rate"] is None:
                r.append(Paragraph("", st_cell))
            else:
                txt = f"<b>{d['rate']*100:.3f}%</b><br/><b>¥{d['monthly']:,.0f}</b><br/><font size=10>({d['years']}年返済)</font>"
                r.append(Paragraph(txt, st_cellb))
        data.append(r)

        if plan == "一般団信":
            r50 = [Paragraph("最長50年", st_cell)]
            for col_idx, bank in enumerate(BANKS):
                d = row50[col_idx]
                if d["rate"] is None:
                    r50.append(Paragraph("", st_cell))
                else:
                    txt = f"<b>{d['rate']*100:.3f}%</b><br/><b>¥{d['monthly']:,.0f}</b><br/><font size=10>({d['years']}年返済)</font>"
                    r50.append(Paragraph(txt, st_cellb))
            data.append(r50)

    nrows = len(data)
    rh = [36*mm]*nrows
    cw = [58*mm] + [43*mm]*len(BANKS)

    ts = TableStyle([
        ('GRID', (0,0), (-1,-1), 0.9, colors.HexColor("#bbb")),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F2F6FA")),
        ('LEFTPADDING', (0,0), (-1,-1), 14),
        ('RIGHTPADDING', (0,0), (-1,-1), 14),
        ('TOPPADDING', (0,0), (-1,-1), 13),
        ('BOTTOMPADDING', (0,0), (-1,-1), 13),
    ])

    # ハイライト
    row_cursor = 1
    for i, mins in enumerate(highlights):
        for col_idx in mins:
            ts.add('BACKGROUND', (col_idx+1, row_cursor), (col_idx+1, row_cursor), colors.HexColor('#FFF8C8'))
        row_cursor += 1
        if PLANS[i] == "一般団信":
            for col_idx in mins50:
                ts.add('BACKGROUND', (col_idx+1, row_cursor), (col_idx+1, row_cursor), colors.HexColor('#FFF8C8'))
            row_cursor += 1

    tb = Table(data, colWidths=cw, rowHeights=rh)
    tb.setStyle(ts)
    elems.append(tb)
    doc.build(elems)
    buf.seek(0)
    return buf

if st.button("📄 PDFを作成", key="btn_make_pdf"):
    pdf_buf = create_pdf()
    st.download_button("📥 PDFをダウンロード", data=pdf_buf,
                       file_name="住宅ローン提案書.pdf", mime="application/pdf", key="btn_dl_pdf")