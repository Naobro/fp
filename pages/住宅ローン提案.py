# 住宅ローン 提案シミュレーター（基準金利を月次管理：方法A）
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

from utils.rates import get_base_rates_for_current_month, month_label

# ======================================
# 画面設定
# ======================================
st.set_page_config(page_title="住宅ローン 提案シミュレーター", layout="wide")

# ========= フォント ==========
FONT_PATH = "NotoSansJP-Regular.ttf"
try:
    pdfmetrics.registerFont(TTFont('NotoSansJP', FONT_PATH))
except Exception as e:
    st.error(f"フォント読み込み失敗: {e}\n{FONT_PATH} をプロジェクト直下に置いてください。")
    st.stop()

def get_japanese_style(size=11, font_name='NotoSansJP', alignment='CENTER', leading=15, bold=False, color=colors.black):
    align_map = {'LEFT': 0, 'CENTER': 1, 'RIGHT': 2}
    return ParagraphStyle(
        name=f'japanese_style_{size}_{alignment}',
        fontName=font_name,
        fontSize=size,
        leading=leading,
        alignment=align_map.get(alignment, 1),
        fontWeight="bold" if bold else "normal",
        textColor=color,
        spaceAfter=2, spaceBefore=2
    )

def calc_monthly_payment(principal, annual_rate, years):
    r = annual_rate / 12
    n = years * 12
    if r == 0:
        return principal / n
    return principal * r / (1 - (1 + r) ** -n)

# 今月の基準金利（%）を共通モジュールから取得
BASE_THIS_MONTH = get_base_rates_for_current_month()

# ========= パスワード設定（営業担当者専用）=========
ADMIN_PASSWORD = "naoki0510"  # 必要に応じて secrets へ移動可

# ========= 手動基準金利の永続保存（JSON） =========
SAVE_DIR = "data"
SAVE_PATH = os.path.join(SAVE_DIR, "manual_rates.json")
os.makedirs(SAVE_DIR, exist_ok=True)

def load_manual_rates():
    """保存済み基準金利を読み込む。存在しなければ今月の基準値を返す。"""
    try:
        if os.path.exists(SAVE_PATH):
            with open(SAVE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {k: float(v) for k, v in data.items()}
    except Exception:
        pass
    # ファイルがない場合のみ今月の基準値を返す
    return BASE_THIS_MONTH.copy()

def save_manual_rates(d):
    """現在の金利辞書 d を JSON に保存。成功→True, 失敗→False"""
    try:
        os.makedirs(SAVE_DIR, exist_ok=True)
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump({k: float(v) for k, v in d.items()}, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

# ========= 入力UI ==========
st.title("住宅ローン 提案シミュレーター")

c1, c2, c3, c4 = st.columns(4)
with c1:
    principal = st.number_input("借入額 (万円)", 500, 100000, 5000) * 10000
with c2:
    self_fund = st.number_input("自己資金 (万円)", 0, 100000, 200) * 10000
with c3:
    annual_income = st.number_input("年収 (万円)", 100, 10000, 1000) * 10000
with c4:
    age = st.number_input("年齢", 18, 80, 35)

max_year = max(1, 79 - age)
years = st.slider("返済期間 (年)", 1, max_year, min(35, max_year))

# ========= 現在の金利を取得（保存済み優先、なければ初回のみ基準値） =========
rates = load_manual_rates()
bank_order = list(rates.keys())
plans_order = ["一般団信", "がん50", "がん100", "三大疾病", "7大疾病", "全疾病"]

# 物件価格概算・LTVに応じた住信SBIの帯調整（従来ロジックを維持）
property_price_guess = (principal + self_fund) / 1.07 if 1.07 != 0 else (principal + self_fund)
ltv = principal / property_price_guess if property_price_guess else 1
base_rate_sbi_percent = float(rates.get("住信SBI銀行", 0.0))

# ── 住信SBI：LTV帯＋返済年数の段階加算（％単位で返す）──
def sbi_effective_rate_percent(base_percent, ltv_value, years_value):
    rate = float(base_percent)  # ％
    # LTV帯
    if ltv_value <= 0.80:
        rate += -0.09   # 80%以下
    elif ltv_value > 1.00:
        rate += 0.07    # 100%超（諸費用まで借入）
    # 返済年数の加算（36〜40年／41〜）
    if 36 <= years_value <= 40:
        rate += 0.07
    elif years_value >= 41:
        rate += 0.15
    return rate  # ％

# 団信・付帯の金利差（％）
rate_diff = {
    "SBI新生銀行": {"がん100": 0.1},
    "三菱UFJ銀行": {"がん50": 0.15, "7大疾病": 0.3, "全疾病": 0.5},
    "PayPay銀行": {"がん50": 0.05, "がん100": 0.15},
    "じぶん銀行": {"がん100": 0.054, "7大疾病": 0.1},
    "住信SBI銀行": {"三大疾病": 0.2 if age < 40 else 0.4},
}

special_notes = {
    "SBI新生銀行": ["125%ルールなし", "ZEH -0.1%"],
    "三菱UFJ銀行": ["三大疾病50%", "ワイド団信+0.3%"],
    "PayPay銀行": ["がん50以上で全疾病・失業補償", "ソフトバンク割 最大-0.13%", "125%ルールなし"],
    "じぶん銀行": ["ワイド団信+0.3%", "じぶん割 最大-0.15%"],
    "住信SBI銀行": ["全疾病保障+三大疾病50%標準付帯", "125%ルールなし"],
}

# ========= 金利修正欄（パスワード認証付き／セッション不使用） =========
st.markdown("---")
with st.expander("🔧 金利を修正する（営業担当専用）", expanded=False):
    st.warning("🔒 営業担当者専用機能です。正しいパスワード入力時のみ、修正UIが表示されます。")
    col1, col2 = st.columns([2, 1])
    with col1:
        password_input = st.text_input("パスワード", type="password")
    with col2:
        auth_ok = st.button("🔓 認証", type="primary")

    if auth_ok and password_input == ADMIN_PASSWORD:
        st.success("✅ 認証成功 - 金利修正が可能です")
        st.info("💾 **注意**：『金利を保存』ボタンを押した時だけ保存されます。自動保存は一切行いません。")

                # 金利修正UI（rates が空でも落ちない安全版）
        if not bank_order:
            st.error("金利マスターが空です。utils.rates.get_base_rates_for_current_month() の返り値をご確認ください。")
            st.info("一時的に手入力で初期値を保存する場合は、下の『基準金利に戻す』を押すと、今月の基準値（空なら何も変わりません）を保存します。")
            updated_rates = rates.copy()
        else:
            updated_rates = rates.copy()
            # 銀行を複数行に分けて描画（1行あたり最大4列）
            MAX_COLS = 4
            for start in range(0, len(bank_order), MAX_COLS):
                chunk = bank_order[start:start+MAX_COLS]
                cols = st.columns(len(chunk))
                for j, bank in enumerate(chunk):
                    with cols[j]:
                        st.caption(f"基準: {BASE_THIS_MONTH.get(bank, 0):.3f}%")
                        new_val = st.number_input(
                            f"{bank} (%)",
                            value=float(rates[bank]),
                            format="%.3f",
                            step=0.001
                        )
                        updated_rates[bank] = new_val

        # 保存ボタン
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            if st.button("💾 金利を保存", type="primary"):
                if save_manual_rates(updated_rates):
                    st.success("✅ 金利を保存しました（次回の計算からこの値を使用）")
                else:
                    st.error("❌ 保存に失敗しました")
        with col_s2:
            if st.button("🔄 基準金利に戻す", type="secondary"):
                if save_manual_rates(BASE_THIS_MONTH):
                    st.success("✅ 基準金利にリセットしました（次回の計算から反映）")
                else:
                    st.error("❌ リセットに失敗しました")

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            if st.button("💾 金利を保存", type="primary"):
                if save_manual_rates(updated_rates):
                    st.success("✅ 金利を保存しました（次回の計算からこの値を使用）")
                else:
                    st.error("❌ 保存に失敗しました")
        with col_s2:
            if st.button("🔄 基準金利に戻す", type="secondary"):
                if save_manual_rates(BASE_THIS_MONTH):
                    st.success("✅ 基準金利にリセットしました（次回の計算から反映）")
                else:
                    st.error("❌ リセットに失敗しました")

    elif auth_ok and password_input != ADMIN_PASSWORD:
        st.error("❌ パスワードが間違っています")
    else:
        st.info("💡 認証に成功すると金利修正欄が表示されます")

# ========= 借入上限額（10万円単位切り捨て・右揃え）==========
def calc_borrowing_limit(income, exam_rate, limit_ratio, age_now):
    exam_years = min(35, 79 - age_now)
    annual_payment = income * limit_ratio
    monthly_payment = annual_payment / 12
    r = exam_rate / 12
    n = exam_years * 12
    if r == 0:
        raw_limit = monthly_payment * n
    else:
        raw_limit = monthly_payment * (1 - (1 + r) ** -n) / r
    return int(raw_limit // 100000 * 100000)

banks_info = {
    "SBI新生銀行": {"審査金利": 0.03,   "返済比率": 0.40},
    "三菱UFJ銀行": {"審査金利": 0.0354, "返済比率": 0.35},
    "PayPay銀行":  {"審査金利": 0.03,   "返済比率": 0.40},
    "じぶん銀行":  {"審査金利": 0.0257, "返済比率": 0.35},
    "住信SBI銀行": {"審査金利": 0.0325, "返済比率": 0.35},
}
limit_amounts, limit_data = {}, []
for bank, info in banks_info.items():
    limit = calc_borrowing_limit(annual_income, info["審査金利"], info["返済比率"], age)
    limit_amounts[bank] = limit
    man = int(limit // 10000)
    limit_data.append([bank, f"{man:,} 万円"])
limit_df = pd.DataFrame(limit_data, columns=["銀行名", "借入上限額"])

st.subheader("💰 年収からの借入上限額")
table_html = """
<style>
.blimit th, .blimit td {border:1.2px solid #aaa; padding:12px; font-size:18px;}
.blimit th {background:#F2F6FA;}
.blimit {border-collapse:collapse; width:480px; margin-bottom:20px;}
</style>
<table class="blimit">
<thead><tr><th align="center" style="width:250px;">銀行名</th><th align="center" style="width:230px;">借入上限額</th></tr></thead>
<tbody>
"""
for _, row in limit_df.iterrows():
    table_html += f"<tr><td align='center'>{row['銀行名']}</td><td align='right'>{row['借入上限額']}</td></tr>"
table_html += "</tbody></table>"
st.markdown(table_html, unsafe_allow_html=True)

# ========= テーブル計算（Web/PDF 共通） =========
def make_table_data_and_highlight(current_rates):
    rows, highlights = [], []

    def years_cap_for_bank(bank_name, req_years):
        cap = min(79 - age, req_years)
        if bank_name in ["SBI新生銀行", "三菱UFJ銀行"]:
            cap = min(cap, 35)
        return cap

    for plan in plans_order:
        row, row_vals = [], []

        for bank in bank_order:
            # 借入上限で弾く
            if principal > limit_amounts.get(bank, 0):
                row.append({"rate": None, "monthly": None, "years": None})
                continue

            # プラン可否
            available = (plan == "一般団信" or plan in rate_diff.get(bank, {}))
            if not available:
                row.append({"rate": None, "monthly": None, "years": None})
                continue

            calc_years = years_cap_for_bank(bank, years)

            # 基準金利
            if bank == "住信SBI銀行":
                eff_percent = sbi_effective_rate_percent(base_rate_sbi_percent, ltv, calc_years)  # ％
                base_rate = eff_percent / 100.0
            else:
                base_rate = float(current_rates[bank]) / 100.0
                # 長期加算：PayPay/じぶん は 36年以上 +0.10%
                if bank in ["PayPay銀行", "じぶん銀行"] and calc_years > 35:
                    base_rate += 0.10 / 100.0

            # 団信・付帯の加算（％ → 実数）
            add = rate_diff.get(bank, {}).get(plan, 0) / 100.0

            monthly = calc_monthly_payment(principal, base_rate + add, calc_years)
            row.append({"rate": base_rate + add, "monthly": monthly, "years": calc_years})
            row_vals.append((len(row) - 1, monthly))

        # 最小返済額セルのハイライト
        min_idxs = set()
        if row_vals:
            minval = min(v for _, v in row_vals)
            for col_idx, v in row_vals:
                if abs(v - minval) < 0.5:
                    min_idxs.add(col_idx)

        rows.append(row)
        highlights.append(min_idxs)

    # ── 「最長50年」（一般団信の下段）──
    row_50, row_50_vals = [], []
    for bank in bank_order:
        # SBI新生・三菱は 35年までなので最長行は空欄
        if principal > limit_amounts.get(bank, 0) or bank in ["SBI新生銀行", "三菱UFJ銀行"]:
            row_50.append({"rate": None, "monthly": None, "years": None})
            continue

        current_bank_max_years = min(79 - age, 50)

        if bank == "住信SBI銀行":
            eff_percent = sbi_effective_rate_percent(base_rate_sbi_percent, ltv, current_bank_max_years)  # ％
            base_rate = eff_percent / 100.0
        else:
            base_rate = float(current_rates[bank]) / 100.0
            if bank in ["PayPay銀行", "じぶん銀行"] and current_bank_max_years > 35:
                base_rate += 0.10 / 100.0

        add = rate_diff.get(bank, {}).get("一般団信", 0) / 100.0

        monthly_longest = calc_monthly_payment(principal, base_rate + add, current_bank_max_years)
        row_50.append({"rate": base_rate + add, "monthly": monthly_longest, "years": current_bank_max_years})
        row_50_vals.append((len(row_50) - 1, monthly_longest))

    min_idxs_50 = set()
    if row_50_vals:
        minval = min(v for _, v in row_50_vals)
        for col_idx, v in row_50_vals:
            if abs(v - minval) < 0.5:
                min_idxs_50.add(col_idx)

    return rows, highlights, row_50, min_idxs_50

table_rows, highlight_rows, row_50, highlight_50 = make_table_data_and_highlight(rates)

# ========= 金利比較HTMLテーブル（Web UI）==========
def make_html_cell(rate_data, is_min_monthly, width_css):
    rate = rate_data["rate"]; monthly = rate_data["monthly"]; years_val = rate_data["years"]
    base_style = "text-align:center;vertical-align:middle;"
    bg = "background-color:#FFF8C8;" if is_min_monthly else ""
    if rate is None:
        return f"<td style='{width_css}{base_style}'></td>"
    return (f"<td style='{width_css}height:68px;{base_style}{bg}'>"
            f"<div style='font-size:22px;font-weight:bold;color:#1B232A'>{rate*100:.3f}%</div>"
            f"<div style='font-size:22px;font-weight:bold;color:#226BB3'>¥{monthly:,.0f}</div>"
            f"<div style='font-size:14px;color:#666;'>({years_val}年返済)</div></td>")

plan_width = "min-width:220px;max-width:220px;width:220px;"
bank_width = "min-width:180px;max-width:180px;width:180px;"

html_table_output = f"""
<style>
.loan-table, .loan-table th, .loan-table td {{border:1.2px solid #aaa; border-collapse: collapse;}}
.loan-table th, .loan-table td {{padding: 13px;}}
.loan-table {{background-color:#fff; width:100%; table-layout:fixed;}}
.loan-table th {{background-color:#F2F6FA; font-size:18px;}}
.loan-table td {{font-size:18px;}}
</style>
<table class="loan-table">
<thead><tr>
<th style='{plan_width}text-align:center;font-size:18px;'>プラン</th>""" + "".join(
    [f"<th style='{bank_width}text-align:center;font-size:18px'>{b}</th>" for b in bank_order]
) + "</tr></thead><tbody>"

for i, plan in enumerate(plans_order):
    html_table_output += f"<tr><td style='{plan_width}text-align:center;font-weight:bold;font-size:18px;'>{plan}</td>"
    for col_idx, bank in enumerate(bank_order):
        rate_data = table_rows[i][col_idx]
        is_min = (col_idx in highlight_rows[i] and rate_data["monthly"] is not None)
        html_table_output += make_html_cell(rate_data, is_min, bank_width)
    html_table_output += "</tr>"
    if plan == "一般団信":
        html_table_output += f"<tr><td style='{plan_width}text-align:center;font-weight:bold;font-size:17px;background-color:#F9F6EF;'>最長50年</td>"
        for col_idx, bank in enumerate(bank_order):
            rate_data = row_50[col_idx]
            is_min = (col_idx in highlight_50 and rate_data["monthly"] is not None)
            html_table_output += make_html_cell(rate_data, is_min, bank_width)
        html_table_output += "</tr>"

# 特記事項（左寄せ、上詰め）
html_table_output += f"<tr><td style='{plan_width}text-align:center;font-weight:bold;font-size:14px;background-color:#FCF9F0;'>特記事項</td>"
for bank in bank_order:
    notes = special_notes.get(bank, [])
    html_table_output += f"<td style='{bank_width}font-size:12px;text-align:left;vertical-align:top;background-color:#FCF9F0;'>{'<br>'.join(notes)}</td>"
html_table_output += "</tr></tbody></table>"

is_modified = any(abs(rates[b] - BASE_THIS_MONTH.get(b, 0.0)) > 0.0005 for b in bank_order)
st.markdown(f"### {month_label()} " + ("**現在適用中の金利（修正済み）**" if is_modified else "基準金利（初期値）"))
st.markdown(html_table_output, unsafe_allow_html=True)

# ========= PDF出力：UIテーブルの完全コピー ==========
def create_pdf_reportlab():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        leftMargin=10*mm, rightMargin=10*mm, topMargin=13*mm, bottomMargin=13*mm
    )
    style_title = get_japanese_style(size=21, font_name='NotoSansJP', alignment='CENTER', leading=31, bold=True)
    style_header = get_japanese_style(size=13, font_name='NotoSansJP', alignment='CENTER', leading=24, bold=True, color=colors.HexColor('#226BB3'))
    style_cell = get_japanese_style(size=12, font_name='NotoSansJP', alignment='CENTER', leading=24)
    style_cellcontent = get_japanese_style(size=15, font_name='NotoSansJP', alignment='CENTER', leading=19, bold=True, color=colors.HexColor('#1B232A'))

    elements = []
    elements.append(Paragraph("住宅ローン提案書", style_title))
    elements.append(Spacer(1, 5*mm))
    elements.append(Paragraph(f"<b>■ 借入金額：¥{principal:,.0f}</b>", style_header))
    elements.append(Spacer(1, 8*mm))

    table_data_pdf = []
    header_row = [Paragraph("プラン", style_header)] + [Paragraph(b, style_header) for b in bank_order]
    table_data_pdf.append(header_row)

    for i, plan in enumerate(plans_order):
        row = [Paragraph(plan, style_cell)]
        for col_idx, bank in enumerate(bank_order):
            rate_data = table_rows[i][col_idx]
            if rate_data["rate"] is None:
                row.append(Paragraph("", style_cell))
            else:
                cell_content = (
                    f"<b>{rate_data['rate']*100:.3f}%</b>"
                    f"<br/><b>¥{rate_data['monthly']:,.0f}</b>"
                    f"<br/><font size=10>({rate_data['years']}年返済)</font>"
                )
                row.append(Paragraph(cell_content, style_cellcontent))
        table_data_pdf.append(row)

        if plan == "一般団信":
            row_50_pdf = [Paragraph("最長50年", style_cell)]
            for col_idx, bank in enumerate(bank_order):
                rate_data = row_50[col_idx]
                if rate_data["rate"] is None:
                    row_50_pdf.append(Paragraph("", style_cell))
                else:
                    cell_content = (
                        f"<b>{rate_data['rate']*100:.3f}%</b>"
                        f"<br/><b>¥{rate_data['monthly']:,.0f}</b>"
                        f"<br/><font size=10>({rate_data['years']}年返済)</font>"
                    )
                    row_50_pdf.append(Paragraph(cell_content, style_cellcontent))
            table_data_pdf.append(row_50_pdf)

    nrows = len(table_data_pdf)
    row_heights = [36*mm]*nrows
    col_widths = [58*mm] + [43*mm]*len(bank_order)

    table_style = TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.9, colors.HexColor("#bbb")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F2F6FA")),
        ('LEFTPADDING', (0,0), (-1,-1), 14),
        ('RIGHTPADDING', (0,0), (-1,-1), 14),
        ('TOPPADDING', (0,0), (-1,-1), 13),
        ('BOTTOMPADDING', (0,0), (-1,-1), 13),
    ])
    row_cursor = 1
    for i, min_idxs in enumerate(highlight_rows):
        for col_idx in min_idxs:
            table_style.add('BACKGROUND', (col_idx+1, row_cursor), (col_idx+1, row_cursor), colors.HexColor('#FFF8C8'))
        row_cursor += 1
        if plans_order[i] == "一般団信":
            for col_idx in highlight_50:
                table_style.add('BACKGROUND', (col_idx+1, row_cursor), (col_idx+1, row_cursor), colors.HexColor('#FFF8C8'))
            row_cursor += 1

    table = Table(table_data_pdf, colWidths=col_widths, rowHeights=row_heights)
    table.setStyle(table_style)
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer

if st.button("📄 PDFを作成"):
    pdf_buffer = create_pdf_reportlab()
    st.download_button(
        label="📥 PDFをダウンロード",
        data=pdf_buffer,
        file_name="住宅ローン提案書.pdf",
        mime="application/pdf"
    )