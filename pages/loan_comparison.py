# pages/loan_comparison.py
import streamlit as st
st.set_page_config(
    page_title="変動・固定金利比較",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="collapsed"
)
st.markdown(
    "<style>section[data-testid='stSidebar']{display:none;}</style>",
    unsafe_allow_html=True
)

import pandas as pd
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# ── フォント登録（日本語対応）
pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
JP = "HeiseiKakuGo-W5"

# ══════════════════════════════════════════════════════════════════════
# 計算ユーティリティ
# ══════════════════════════════════════════════════════════════════════
def monthly_payment(balance: float, annual_rate: float, months: int) -> float:
    r = (annual_rate / 100) / 12
    if months <= 0:
        return 0.0
    if abs(r) < 1e-12:
        return balance / months
    return balance * r * (1 + r) ** months / ((1 + r) ** months - 1)


def simulate(principal_man: int, years: int, rate_schedule: dict, checkpoints: list):
    balance = principal_man * 10_000
    total_paid = 0.0
    results = {}
    total_months = years * 12
    monthly = 0.0
    current_rate = None
    for m in range(1, total_months + 1):
        year = (m - 1) // 12 + 1
        if year in rate_schedule and (m - 1) % 12 == 0:
            current_rate = rate_schedule[year]
            monthly = monthly_payment(balance, current_rate, total_months - m + 1)
        interest = balance * (current_rate / 100 / 12)
        principal_pay = monthly - interest
        balance -= principal_pay
        total_paid += monthly
        if m % 12 == 0 and year in checkpoints:
            results[year] = {
                "金利": round(current_rate, 3),
                "月額": round(monthly / 10_000, 2),
                "累計": round(total_paid / 10_000, 0),
            }
    return results


def compound_investment(monthly: float, annual_rate: float, years: int) -> float:
    r = (annual_rate / 100) / 12
    months = years * 12
    if months <= 0:
        return 0.0
    if abs(r) < 1e-12:
        return monthly * months
    return monthly * (((1 + r) ** months - 1) / r)


# ══════════════════════════════════════════════════════════════════════
# フラット35 S ポイント定義
# ══════════════════════════════════════════════════════════════════════
FLAT35S_GROUPS = {
    "1. 家族": {
        "若夫婦世帯 または 子ども1人": 1,
        "子ども2人": 2,
        "子ども3人": 3,
        "子どもN人（手入力）": None,
    },
    "2. 性能": {
        "S（ZEH）": 3,
        "S（Aプラン）": 2,
        "S（Bプラン）": 1,
        "リノベ（Aプラン）": 4,
        "リノベ（Bプラン）": 2,
    },
    "3. 管理・修繕": {
        "長期優良住宅": 1,
        "予備認定マンション": 1,
        "管理計画認定マンション": 1,
        "安心R住宅": 1,
        "インスペクション実施住宅": 1,
        "既存住宅売買瑕疵保険付住宅": 1,
    },
    "4. エリア": {
        "子育て支援・老齢化対策": 2,
        "地域活性化": 1,
        "地方移住支援型": 4,
    },
    "5. 劣化状況": {
        "中古住宅（既存住宅性能評価等）": 1,
    },
}


# ══════════════════════════════════════════════════════════════════════
# フラット35 S 金利引下げロジック（修正済）
#
#  当初1〜5年  : 1P→▲0.25 / 2P→▲0.50 / 3P→▲0.75 / 4P以上→▲1.00
#  6〜10年目   : 5P→▲0.25 / 6P→▲0.50 / 7P→▲0.75 / 8P以上→▲1.00
#  11〜15年目  : 9P→▲0.25 / 10P→▲0.50 / 11P→▲0.75 / 12P以上→▲1.00
# ══════════════════════════════════════════════════════════════════════
def get_discount(total_p: int) -> dict:
    def tier(p: int, base: int) -> float:
        if p < base:
            return 0.0
        offset = p - base   # 0,1,2,3,4...
        return min(0.25 * (offset + 1), 1.00)

    return {
        "5年":  tier(total_p, 1),   # 1P起点
        "10年": tier(total_p, 5),   # 5P起点
        "15年": tier(total_p, 9),   # 9P起点
    }


def flat35s_schedule(base: float, total_p: int, years: int) -> dict:
    """ポイントに応じた引下げを反映したフラット35Sの年別金利スケジュール"""
    disc = get_discount(total_p)
    schedule = {}
    for y in range(1, years + 1):
        if y <= 5:
            schedule[y] = max(base - disc["5年"],  0.0)
        elif y <= 10:
            schedule[y] = max(base - disc["10年"], 0.0)
        elif y <= 15:
            schedule[y] = max(base - disc["15年"], 0.0)
        else:
            schedule[y] = base
    return schedule


# ══════════════════════════════════════════════════════════════════════
# PDF 生成
# ══════════════════════════════════════════════════════════════════════
def build_pdf(
    loan_amount_man, years, own_funds_man, chokkin_rate,
    var_rate, flat_base, flat_total_p, disc,
    checkpoints, scenarios_data,
    diff_monthly, invest_rate, invest_years, future_value,
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=12*mm, rightMargin=12*mm,
        topMargin=10*mm, bottomMargin=10*mm,
    )
    styles = getSampleStyleSheet()
    jp_normal = ParagraphStyle(
        "jp_normal", fontName=JP, fontSize=8, leading=12, parent=styles["Normal"]
    )
    jp_h1 = ParagraphStyle(
        "jp_h1", fontName=JP, fontSize=13, leading=18, spaceAfter=2*mm,
        textColor=colors.HexColor("#1a4f8a"), parent=styles["Heading1"]
    )
    jp_h2 = ParagraphStyle(
        "jp_h2", fontName=JP, fontSize=9, leading=13, spaceBefore=3*mm,
        textColor=colors.HexColor("#1a4f8a"), parent=styles["Heading2"]
    )
    jp_small = ParagraphStyle(
        "jp_small", fontName=JP, fontSize=7, leading=10, parent=styles["Normal"]
    )

    story = []

    # タイトル
    story.append(Paragraph("住宅ローン比較レポート（変動金利 vs フラット35）", jp_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1a4f8a")))
    story.append(Spacer(1, 3*mm))

    # ── 借入条件 ──
    story.append(Paragraph("■ 借入条件", jp_h2))
    cond_data = [
        ["項目", "内容"],
        ["借入金額",           f"{loan_amount_man:,} 万円"],
        ["自己資金",           f"{own_funds_man:,} 万円"],
        ["頭金率",             f"{chokkin_rate:.1f} ％"],
        ["返済期間",           f"{years} 年"],
        ["変動金利（初期）",   f"{var_rate:.3f} ％"],
        ["フラット35 基準金利", f"{flat_base:.3f} ％"],
        ["フラット35 S 合計ポイント", f"{flat_total_p} P"],
        ["引下げ（当初1〜5年）",
         f"▲{disc['5年']:.2f}％  →  適用金利 {max(flat_base - disc['5年'],  0):.3f}％"],
        ["引下げ（6〜10年目）",
         f"▲{disc['10年']:.2f}％  →  適用金利 {max(flat_base - disc['10年'], 0):.3f}％"],
        ["引下げ（11〜15年目）",
         f"▲{disc['15年']:.2f}％  →  適用金利 {max(flat_base - disc['15年'], 0):.3f}％"],
    ]
    t = Table(cond_data, colWidths=[65*mm, 105*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#1a4f8a")),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, -1), JP),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#eef3fb")]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.grey),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(t)
    story.append(Spacer(1, 3*mm))

    # ── シミュレーション結果 ──
    story.append(Paragraph("■ 返済シミュレーション結果", jp_h2))
    chk_filtered = [y for y in checkpoints if y <= years]
    header = ["シナリオ"] + [f"{y}年末" for y in chk_filtered]
    rows_pdf = [header]
    for name, data in scenarios_data.items():
        row = [name]
        for y in chk_filtered:
            if y in data:
                d = data[y]
                row.append(f"金利{d['金利']}%\n月{d['月額']}万\n累計{d['累計']}万")
            else:
                row.append("-")
        rows_pdf.append(row)
    ncols = len(header)
    col_w = [40*mm] + [(186 - 40) / max(ncols - 1, 1) * mm] * (ncols - 1)
    t2 = Table(rows_pdf, colWidths=col_w, repeatRows=1)
    t2.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#1a4f8a")),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, -1), JP),
        ("FONTSIZE",      (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#eef3fb")]),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.grey),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]))
    story.append(t2)
    story.append(Spacer(1, 3*mm))

    # ── 差額投資シミュレーション ──
    story.append(Paragraph("■ 差額投資シミュレーション", jp_h2))
    mv = monthly_payment(loan_amount_man * 10_000, var_rate, years * 12)
    mf = monthly_payment(loan_amount_man * 10_000, flat_base, years * 12)
    inv_data = [
        ["項目", "金額"],
        ["変動 月額返済",   f"{mv:,.0f} 円"],
        ["フラット35 月額返済", f"{mf:,.0f} 円"],
        ["差額（月）",      f"{diff_monthly:,.0f} 円"],
        [f"差額を年利{invest_rate:.1f}%で{invest_years}年運用",
         f"{future_value / 10_000:,.1f} 万円"],
    ]
    t3 = Table(inv_data, colWidths=[105*mm, 65*mm])
    t3.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#1a4f8a")),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, -1), JP),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#eef3fb")]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.grey),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(t3)
    story.append(Spacer(1, 3*mm))

    # ── メリット・デメリット ──
    story.append(Paragraph("■ 変動金利 vs フラット35 メリット・デメリット", jp_h2))
    merit_data = [
        ["", "変動金利", "フラット35（固定）"],
        ["メリット",
         "・借入時の金利が低く月々返済を抑えやすい\n・金利低下時に返済負担が軽減\n・団信の選択肢が多い",
         "・返済額固定で家計設計が安定\n・金利上昇リスクなし\n・団信加入が任意（健康不安でも可）"],
        ["デメリット",
         "・金利上昇で返済額が増えるリスク\n・125%ルールによる未払利息リスク\n・家計設計が不安定",
         "・初期金利が変動より高い\n・市場金利低下の恩恵なし\n・借入上限8,000万円\n・適合証明が必要"],
    ]
    t4 = Table(merit_data, colWidths=[18*mm, 84*mm, 84*mm])
    t4.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#1a4f8a")),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, -1), JP),
        ("FONTSIZE",      (0, 0), (-1, -1), 7.5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#eef3fb")]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(t4)

    # フッター
    story.append(Spacer(1, 2*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Paragraph(
        "※本シミュレーションは概算です。実際の返済額・金利は金融機関にご確認ください。"
        "　フラット35Sポイント引下げは住宅金融支援機構の審査が必要です。",
        jp_small
    ))

    doc.build(story)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════
# ページ本体
# ══════════════════════════════════════════════════════════════════════
st.markdown(
    "<h2 style='font-size:22px;'>🏠 住宅ローン比較（変動金利 vs フラット35）</h2>",
    unsafe_allow_html=True
)

# ──────────────────────────────────────────────────────────────────────
# ① フラット35 S ポイント入力（各グループ1つのみ選択可）
# ──────────────────────────────────────────────────────────────────────
with st.expander("① フラット35 S ポイント入力（各グループから1つ選択）", expanded=True):
    total_points = 0
    cols_g = st.columns(5)
    group_names = list(FLAT35S_GROUPS.keys())

    for gi, gname in enumerate(group_names):
        with cols_g[gi]:
            st.markdown(f"**{gname}**")
            items = FLAT35S_GROUPS[gname]

            if gname == "1. 家族":
                # 家族グループのみ：子どもN人手入力あり
                options_family = ["選択なし（0P）"] + [
                    f"{label}（+{pt}P）" if pt is not None else label
                    for label, pt in items.items()
                ]
                # ラジオ（子どもN人以外）
                labels_fixed = {
                    label: pt for label, pt in items.items() if pt is not None
                }
                labels_none  = {
                    label: pt for label, pt in items.items() if pt is None
                }

                # 固定ポイント選択肢をラジオで
                radio_options = ["選択なし（0P）"] + [
                    f"{label}（+{pt}P）" for label, pt in labels_fixed.items()
                ]
                selected_family = st.radio(
                    "選択",
                    radio_options,
                    index=0,
                    key=f"radio_{gname}",
                    label_visibility="collapsed"
                )
                for label, pt in labels_fixed.items():
                    if selected_family == f"{label}（+{pt}P）":
                        total_points += pt

                # 子どもN人は手入力（別途加算）
                st.markdown("**または**")
                for label, pt in labels_none.items():
                    n = st.number_input(
                        f"{label}（N×1P）",
                        min_value=0, max_value=10, value=0, step=1,
                        key=f"flat35s_{gname}_{label}"
                    )
                    total_points += n

            else:
                # その他グループ：ラジオで1つのみ選択
                option_labels = {label: pt for label, pt in items.items()}
                radio_options = ["選択なし（0P）"] + [
                    f"{label}（+{pt}P）" for label, pt in option_labels.items()
                ]
                selected = st.radio(
                    "選択",
                    radio_options,
                    index=0,
                    key=f"radio_{gname}",
                    label_visibility="collapsed"
                )
                for label, pt in option_labels.items():
                    if selected == f"{label}（+{pt}P）":
                        total_points += pt

    disc = get_discount(total_points)
    st.markdown("---")
    st.markdown(
        f"### 合計ポイント：{total_points} P　→　"
        f"当初1〜5年 **▲{disc['5年']:.2f}%**　／　"
        f"6〜10年目 **▲{disc['10年']:.2f}%**　／　"
        f"11〜15年目 **▲{disc['15年']:.2f}%**"
    )

# ──────────────────────────────────────────────────────────────────────
# ② 金利設定
# ──────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("**② 金利設定**")
c1, c2 = st.columns(2)
with c1:
    var_rate = st.number_input(
        "変動金利 初期値（％）", value=0.894, step=0.001, format="%.3f"
    )
with c2:
    flat_base = st.number_input(
        "フラット35 基準金利（％）", value=2.820, step=0.001, format="%.3f"
    )

# ──────────────────────────────────────────────────────────────────────
# ③ 物件価格・諸費用・自己資金
# ──────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("**③ 物件価格・諸費用・自己資金**")
c3, c4, c5 = st.columns(3)
with c3:
    property_price = st.number_input(
        "物件価格（万円）", value=5000, step=100, min_value=0
    )
with c4:
    misc_cost = st.number_input(
        "諸費用（万円）", value=200, step=10, min_value=0
    )
with c5:
    own_funds = st.number_input(
        "自己資金（万円）", value=500, step=50, min_value=0
    )

# ──────────────────────────────────────────────────────────────────────
# ④ 借入金額・頭金率 自動計算
# ──────────────────────────────────────────────────────────────────────
loan_amount = max(property_price + misc_cost - own_funds, 0)
down_payment = property_price - loan_amount
chokkin_rate = (down_payment / property_price * 100) if property_price > 0 else 0.0

st.markdown("**④ 借入金額・頭金率（自動計算）**")
c6, c7, c8 = st.columns(3)
with c6:
    st.metric("借入金額（万円）", f"{loan_amount:,}")
with c7:
    st.metric("頭金（万円）", f"{down_payment:,}")
with c8:
    st.metric("頭金率", f"{chokkin_rate:.1f} ％")

st.caption(
    "借入金額 ＝ 物件価格 ＋ 諸費用 − 自己資金　／　"
    "頭金率 ＝（物件価格 − 借入金額）÷ 物件価格 × 100"
)

# ──────────────────────────────────────────────────────────────────────
# 返済期間
# ──────────────────────────────────────────────────────────────────────
st.markdown("---")
years = st.number_input("返済期間（年）", value=35, min_value=1, max_value=50)

# ──────────────────────────────────────────────────────────────────────
# シミュレーション実行
# ──────────────────────────────────────────────────────────────────────
checkpoints = [1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50]

scenarios = {}

# 変動：現状維持
scenarios["変動 現状維持"] = {y: var_rate for y in range(1, years + 1)}

# 変動：GOOD（毎年-0.01%、下限0.25%）
scenarios["変動 GOOD（毎年-0.01%）"] = {
    y: max(var_rate - 0.01 * (y - 1), 0.25) for y in range(1, years + 1)
}

# 変動：BAD（金利上昇シナリオ）
bad_tbl = {
    1: 0.52,  2: 0.686, 3: 0.852, 4: 1.018, 5: 1.184,
    6: 1.35,  7: 1.44,  8: 1.53,  9: 1.62,  10: 1.71,
    11: 1.80, 12: 1.89, 13: 1.98, 14: 2.07, 15: 2.16,
    16: 2.25, 17: 2.30, 18: 2.35, 19: 2.40, 20: 2.45,
    21: 2.50, 22: 2.55, 23: 2.60, 24: 2.65, 25: 2.70,
    26: 2.75, 27: 2.80, 28: 2.85, 29: 2.90, 30: 2.95,
    31: 3.00, 32: 3.05, 33: 3.10, 34: 3.15, 35: 3.20,
}
scenarios["変動 BAD（金利上昇）"] = {
    y: bad_tbl.get(y, 3.25) for y in range(1, years + 1)
}

# フラット35 S（ポイント反映・割引金利で計算）
flat_s_schedule = flat35s_schedule(flat_base, total_points, years)
scenarios[f"フラット35 S（{total_points}P）"] = flat_s_schedule

# フラット35 基準（引下なし）
scenarios["フラット35 基準（0P）"] = {y: flat_base for y in range(1, years + 1)}

# シミュレーション実行
sim_results = {}
for name, sched in scenarios.items():
    sim_results[name] = simulate(loan_amount, years, sched, checkpoints)

# ──────────────────────────────────────────────────────────────────────
# 結果テーブル表示
# ──────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<h3 style='font-size:20px;'>📊 返済シミュレーション結果</h3>",
    unsafe_allow_html=True
)
chk_show = [y for y in checkpoints if y <= years]
rows = []
for name, data in sim_results.items():
    row = {"シナリオ": name}
    for y in chk_show:
        if y in data:
            d = data[y]
            row[f"{y}年末"] = f"金利{d['金利']}% / 月{d['月額']}万 / 累計{d['累計']}万"
        else:
            row[f"{y}年末"] = "-"
    rows.append(row)

st.dataframe(pd.DataFrame(rows), use_container_width=True)

# ──────────────────────────────────────────────────────────────────────
# フラット35 S 引下げ対応表（参考）
# ──────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("**フラット35 S 金利引下げ対応表（参考）**")
disc_rows = []
for p in range(1, 13):
    d = get_discount(p)
    disc_rows.append({
        "合計ポイント": f"{p}P",
        "当初1〜5年":  f"▲{d['5年']:.2f}%"  if d['5年']  > 0 else "±0%",
        "6〜10年目":   f"▲{d['10年']:.2f}%" if d['10年'] > 0 else "±0%",
        "11〜15年目":  f"▲{d['15年']:.2f}%" if d['15年'] > 0 else "±0%",
    })
st.dataframe(pd.DataFrame(disc_rows), use_container_width=True, hide_index=True)

# ──────────────────────────────────────────────────────────────────────
# 差額投資シミュレーション
# ──────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<h3 style='font-size:20px;'>📈 差額投資シミュレーション</h3>",
    unsafe_allow_html=True
)

monthly_var  = monthly_payment(loan_amount * 10_000, var_rate,  years * 12)
monthly_flat = monthly_payment(loan_amount * 10_000, flat_base, years * 12)
diff_monthly = monthly_flat - monthly_var

c9, c10 = st.columns(2)
with c9:
    st.metric("変動 月額返済",    f"{monthly_var:,.0f} 円")
    st.metric("フラット35 月額返済", f"{monthly_flat:,.0f} 円")
with c10:
    st.metric("差額（月）", f"{diff_monthly:,.0f} 円")
    st.metric("差額（総額）", f"{diff_monthly * years * 12:,.0f} 円")

c11, c12 = st.columns(2)
with c11:
    invest_rate  = st.number_input(
        "想定利回り（年率 ％）", value=4.0, step=0.1, format="%.1f"
    )
with c12:
    invest_years = st.number_input(
        "運用期間（年）", value=int(years), step=1, min_value=1, max_value=50
    )

future_value = compound_investment(diff_monthly, invest_rate, invest_years)
st.success(
    f"差額（月 {diff_monthly:,.0f}円）を年利 {invest_rate:.1f}% で "
    f"{invest_years} 年間複利運用 → **{future_value / 10_000:,.1f} 万円**"
)

# ──────────────────────────────────────────────────────────────────────
# メリット・デメリット
# ──────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<h3 style='font-size:20px;'>📋 変動・固定 メリット・デメリット</h3>",
    unsafe_allow_html=True
)
st.markdown("""
<div style="font-size:14px; line-height:1.8;">
<table style="width:100%; border-collapse:collapse;">
<tr style="background:#1a4f8a; color:white;">
  <th style="padding:6px 10px; width:12%;">　</th>
  <th style="padding:6px 10px; width:44%;">変動金利</th>
  <th style="padding:6px 10px; width:44%;">フラット35（固定）</th>
</tr>
<tr style="background:#eef3fb;">
  <td style="padding:6px 10px; font-weight:bold;">メリット</td>
  <td style="padding:6px 10px;">
    ・借入時の金利が低く月々返済を抑えやすい<br>
    ・金利低下時に返済負担が軽減<br>
    ・団信の選択肢が多い
  </td>
  <td style="padding:6px 10px;">
    ・返済額固定で家計設計が安定<br>
    ・金利上昇リスクなし<br>
    ・団信加入が任意（健康不安でも利用可）
  </td>
</tr>
<tr>
  <td style="padding:6px 10px; font-weight:bold;">デメリット</td>
  <td style="padding:6px 10px;">
    ・金利上昇で返済額増のリスク<br>
    ・125%ルールによる未払利息リスク<br>
    ・家計設計が不安定
  </td>
  <td style="padding:6px 10px;">
    ・初期金利が変動より高い<br>
    ・市場金利低下の恩恵なし<br>
    ・借入上限8,000万円<br>
    ・適合証明（フラット35適合）が必要
  </td>
</tr>
</table>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────
# ⑤ PDF ダウンロード
# ──────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<h3 style='font-size:20px;'>⬇️ PDF レポートダウンロード（A4 1枚）</h3>",
    unsafe_allow_html=True
)

if st.button("📄 PDF を生成してダウンロード"):
    with st.spinner("PDF を生成中..."):
        pdf_bytes = build_pdf(
            loan_amount_man=loan_amount,
            years=years,
            own_funds_man=own_funds,
            chokkin_rate=chokkin_rate,
            var_rate=var_rate,
            flat_base=flat_base,
            flat_total_p=total_points,
            disc=disc,
            checkpoints=checkpoints,
            scenarios_data=sim_results,
            diff_monthly=diff_monthly,
            invest_rate=invest_rate,
            invest_years=invest_years,
            future_value=future_value,
        )
    st.download_button(
        label="⬇️ PDF をダウンロード",
        data=pdf_bytes,
        file_name="住宅ローン比較レポート.pdf",
        mime="application/pdf",
    )

st.caption(
    "※本シミュレーションは概算です。実際の返済額・金利は金融機関にご確認ください。"
    "　フラット35Sポイント引下げは住宅金融支援機構の審査・認定が必要です。"
)
