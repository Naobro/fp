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
# ===== 共通ヘッダー（会社情報＋相談ボタン）=====
st.markdown("""
<style>
.header-box {
    background: linear-gradient(135deg, #1a4f8a 0%, #2563eb 100%);
    color: #fff;
    padding: 18px 22px;
    border-radius: 12px;
    margin-bottom: 18px;
    box-shadow: 0 3px 10px rgba(0,0,0,0.15);
    text-align: center;
}
.header-box .company { font-size: 14px; font-weight: 600; opacity: 0.95; margin-bottom: 4px; }
.header-box .agent { font-size: 18px; font-weight: 800; margin-bottom: 10px; letter-spacing: 0.5px; }
.header-box .catch { font-size: 15px; font-weight: 600; line-height: 1.6; margin-bottom: 14px; }
.header-box .catch .strong { font-size: 17px; font-weight: 800; color: #fff200; }
.header-cta {
    display: inline-block;
    background: #ff5722;
    color: #fff !important;
    font-size: 18px;
    font-weight: 900;
    padding: 12px 38px;
    border-radius: 50px;
    text-decoration: none !important;
    box-shadow: 0 4px 12px rgba(255,87,34,0.4);
    transition: all 0.2s;
    letter-spacing: 1px;
}
.header-cta:hover { background: #e64a19; transform: translateY(-2px); box-shadow: 0 6px 16px rgba(255,87,34,0.5); }
@media screen and (max-width: 768px) {
    .header-box { padding: 14px 16px; }
    .header-box .company { font-size: 12px; }
    .header-box .agent { font-size: 16px; }
    .header-box .catch { font-size: 13px; }
    .header-box .catch .strong { font-size: 15px; }
    .header-cta { font-size: 16px; padding: 10px 28px; }
}
</style>

<div class="header-box">
    <div class="company">株式会社 TERASS</div>
    <div class="agent">不動産エージェント　西山　作成</div>
    <div class="catch">
        <span class="strong">不動産売買</span><br>
        購入前相談・セカンドオピニオン<br>
        お気軽にご相談ください
    </div>
    <a class="header-cta" href="https://share-me.design/Naokiwm" target="_blank" rel="noopener">
        💬 相談する
    </a>
</div>
""", unsafe_allow_html=True)

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
# フラット35 S 金利引下げロジック
# ══════════════════════════════════════════════════════════════════════
def get_discount(total_p: int) -> dict:
    def tier(p: int, base: int) -> float:
        if p < base:
            return 0.0
        offset = p - base
        return min(0.25 * (offset + 1), 1.00)
    return {
        "5年":  tier(total_p, 1),
        "10年": tier(total_p, 5),
        "15年": tier(total_p, 9),
    }


def flat35s_schedule(base: float, total_p: int, years: int) -> dict:
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
    total_var, total_bad, total_flat,
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=10*mm, rightMargin=10*mm,
        topMargin=8*mm, bottomMargin=8*mm,
    )
    styles = getSampleStyleSheet()
    jp_h1 = ParagraphStyle(
        "jp_h1", fontName=JP, fontSize=12, leading=16, spaceAfter=2*mm,
        textColor=colors.HexColor("#1a4f8a"), parent=styles["Heading1"]
    )
    jp_h2 = ParagraphStyle(
        "jp_h2", fontName=JP, fontSize=8, leading=11, spaceBefore=2*mm,
        textColor=colors.HexColor("#1a4f8a"), parent=styles["Heading2"]
    )
    jp_small = ParagraphStyle(
        "jp_small", fontName=JP, fontSize=6, leading=9, parent=styles["Normal"]
    )
    jp_body = ParagraphStyle(
        "jp_body", fontName=JP, fontSize=7.5, leading=12, parent=styles["Normal"]
    )

    story = []

    # ── タイトル ──
    story.append(Paragraph("住宅ローン比較レポート（変動金利 vs フラット35）", jp_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1a4f8a")))
    story.append(Spacer(1, 2*mm))

    # ── 借入条件 ──
    story.append(Paragraph("■ 借入条件", jp_h2))
    cond_data = [
        ["項目", "内容"],
        ["借入金額",                    f"{loan_amount_man:,} 万円"],
        ["自己資金",                    f"{own_funds_man:,} 万円"],
        ["頭金率",                      f"{chokkin_rate:.1f} ％"],
        ["返済期間",                    f"{years} 年"],
        ["①変動金利（現状維持）",       f"{var_rate:.3f} ％"],
        ["②変動金利BAD（年+0.2%上昇）", f"{var_rate:.3f}％ スタート → 年0.2%上昇"],
        ["③フラット35 基準金利",        f"{flat_base:.3f} ％"],
        ["③フラット35 S 合計ポイント",  f"{flat_total_p} P"],
        ["③引下げ（当初1〜5年）",
         f"▲{disc['5年']:.2f}％ → 適用金利 {max(flat_base - disc['5年'], 0):.3f}％"],
        ["③引下げ（6〜10年目）",
         f"▲{disc['10年']:.2f}％ → 適用金利 {max(flat_base - disc['10年'], 0):.3f}％"],
        ["③引下げ（11〜15年目）",
         f"▲{disc['15年']:.2f}％ → 適用金利 {max(flat_base - disc['15年'], 0):.3f}％"],
    ]
    t_cond = Table(cond_data, colWidths=[65*mm, 120*mm])
    t_cond.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#1a4f8a")),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, -1), JP),
        ("FONTSIZE",      (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#eef3fb")]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.grey),
        ("TOPPADDING",    (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]))
    story.append(t_cond)
    story.append(Spacer(1, 2*mm))

    # ── シミュレーション結果（フォント2回り小さく） ──
    story.append(Paragraph("■ 返済シミュレーション結果", jp_h2))
    chk_filtered = [y for y in checkpoints if y <= years]
    header = ["シナリオ"] + [f"{y}年末" for y in chk_filtered]
    rows_pdf = [header]
    for name, data in scenarios_data.items():
        row = [name]
        for y in chk_filtered:
            if y in data:
                d = data[y]
                # 改行区切りで3行
                row.append(f"金利{d['金利']}%\n月{d['月額']}万\n累計{d['累計']}万")
            else:
                row.append("-")
        rows_pdf.append(row)

    ncols = len(header)
    total_w = 185  # mm
    name_w  = 32   # シナリオ列
    rest_w  = (total_w - name_w) / max(ncols - 1, 1)
    col_w   = [name_w * mm] + [rest_w * mm] * (ncols - 1)

    t_sim = Table(rows_pdf, colWidths=col_w, repeatRows=1)
    t_sim.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#1a4f8a")),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, -1), JP),
        ("FONTSIZE",      (0, 0), (-1, -1), 5),   # ← 2回り小さく（7→5）
        ("LEADING",       (0, 0), (-1, -1), 7),   # ← 行間も縮小
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#eef3fb")]),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.grey),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    story.append(t_sim)
    story.append(Spacer(1, 2*mm))

    # ── 返済総額サマリー ──
    story.append(Paragraph("■ 返済総額まとめ", jp_h2))
    summary_data = [
        ["シナリオ", "返済総額", "①との差額"],
        ["①変動 現状維持",           f"{total_var:,.0f} 万円",  "―"],
        ["②変動 BAD（年+0.2%上昇）", f"{total_bad:,.0f} 万円",  f"+{total_bad - total_var:,.0f} 万円"],
        ["③固定 フラット35 S",        f"{total_flat:,.0f} 万円", f"+{total_flat - total_var:,.0f} 万円"],
    ]
    t_sum = Table(summary_data, colWidths=[70*mm, 55*mm, 60*mm])
    t_sum.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#1a4f8a")),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, -1), JP),
        ("FONTSIZE",      (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#eef3fb")]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.grey),
        ("TOPPADDING",    (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]))
    story.append(t_sum)
    story.append(Spacer(1, 2*mm))

    # ── 差額投資シミュレーション ──
    story.append(Paragraph("■ 差額投資シミュレーション（①変動現状維持 vs ③固定）", jp_h2))
    mv = monthly_payment(loan_amount_man * 10_000, var_rate, years * 12)
    mf = monthly_payment(loan_amount_man * 10_000, flat_base, years * 12)
    inv_data = [
        ["項目", "金額"],
        ["①変動 月額返済",         f"{mv:,.0f} 円"],
        ["③フラット35 月額返済",   f"{mf:,.0f} 円"],
        ["差額（月）",             f"{diff_monthly:,.0f} 円"],
        [f"差額を年利{invest_rate:.1f}%で{invest_years}年運用",
         f"{future_value / 10_000:,.1f} 万円"],
    ]
    t_inv = Table(inv_data, colWidths=[105*mm, 80*mm])
    t_inv.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#1a4f8a")),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, -1), JP),
        ("FONTSIZE",      (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#eef3fb")]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.grey),
        ("TOPPADDING",    (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]))
    story.append(t_inv)
    story.append(Spacer(1, 2*mm))

    # ── どちらを選ぶ？ ──
    story.append(Paragraph("■ どちらを選ぶ？", jp_h2))
    choice_data = [
        ["", "選択理由"],
        ["変動金利を選ぶ方",
         "固定金利を支払っているつもりで差額を毎月運用する。\n"
         f"差額（月 {diff_monthly:,.0f}円）を年利{invest_rate:.1f}%で{invest_years}年運用 → "
         f"{future_value/10_000:,.1f}万円の資産形成が期待できる。"],
        ["固定金利を選ぶ方",
         "金利上昇リスク・運用失敗リスク・精神的ストレスを避けたい方。\n"
         "返済額が全期間固定で、家計設計が安定する安心感を重視。"],
    ]
    t_choice = Table(choice_data, colWidths=[35*mm, 150*mm])
    t_choice.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#1a4f8a")),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, -1), JP),
        ("FONTSIZE",      (0, 0), (-1, -1), 7),
        ("BACKGROUND",    (0, 1), (0, 1), colors.HexColor("#dbeafe")),
        ("BACKGROUND",    (0, 2), (0, 2), colors.HexColor("#dcfce7")),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(t_choice)
    story.append(Spacer(1, 2*mm))

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
    t_merit = Table(merit_data, colWidths=[16*mm, 84*mm, 85*mm])
    t_merit.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#1a4f8a")),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, -1), JP),
        ("FONTSIZE",      (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#eef3fb")]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(t_merit)

    # ── フッター ──
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
# ① フラット35 S ポイント入力
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
                labels_fixed = {lb: pt for lb, pt in items.items() if pt is not None}
                labels_none  = {lb: pt for lb, pt in items.items() if pt is None}
                radio_options = ["選択なし（0P）"] + [
                    f"{lb}（+{pt}P）" for lb, pt in labels_fixed.items()
                ]
                selected_family = st.radio(
                    "選択", radio_options, index=0,
                    key=f"radio_{gname}",
                    label_visibility="collapsed"
                )
                for lb, pt in labels_fixed.items():
                    if selected_family == f"{lb}（+{pt}P）":
                        total_points += pt
                st.markdown("**または**")
                for lb, pt in labels_none.items():
                    n = st.number_input(
                        f"{lb}（N×1P）",
                        min_value=0, max_value=10, value=0, step=1,
                        key=f"flat35s_{gname}_{lb}"
                    )
                    total_points += n
            else:
                option_labels = {lb: pt for lb, pt in items.items()}
                radio_options = ["選択なし（0P）"] + [
                    f"{lb}（+{pt}P）" for lb, pt in option_labels.items()
                ]
                selected = st.radio(
                    "選択", radio_options, index=0,
                    key=f"radio_{gname}",
                    label_visibility="collapsed"
                )
                for lb, pt in option_labels.items():
                    if selected == f"{lb}（+{pt}P）":
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
# シナリオ構築
# ──────────────────────────────────────────────────────────────────────
checkpoints = [1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50]

scenarios = {}
scenarios["①変動 現状維持"] = {
    y: var_rate for y in range(1, years + 1)
}
scenarios["②変動 BAD（年+0.2%上昇）"] = {
    y: round(var_rate + 0.2 * (y - 1), 3) for y in range(1, years + 1)
}
flat_s_schedule = flat35s_schedule(flat_base, total_points, years)
scenarios[f"③固定 フラット35 S（{total_points}P）"] = flat_s_schedule

sim_results = {}
for name, sched in scenarios.items():
    sim_results[name] = simulate(loan_amount, years, sched, checkpoints)

# ──────────────────────────────────────────────────────────────────────
# 返済総額計算
# ──────────────────────────────────────────────────────────────────────
def calc_total(principal_man, years, rate_schedule):
    balance = principal_man * 10_000
    total = 0.0
    total_months = years * 12
    monthly = 0.0
    current_rate = None
    for m in range(1, total_months + 1):
        year = (m - 1) // 12 + 1
        if year in rate_schedule and (m - 1) % 12 == 0:
            current_rate = rate_schedule[year]
            monthly = monthly_payment(balance, current_rate, total_months - m + 1)
        interest = balance * (current_rate / 100 / 12)
        balance -= (monthly - interest)
        total += monthly
    return round(total / 10_000, 0)

total_var  = calc_total(loan_amount, years, scenarios["①変動 現状維持"])
total_bad  = calc_total(loan_amount, years, scenarios["②変動 BAD（年+0.2%上昇）"])
total_flat = calc_total(loan_amount, years, flat_s_schedule)

# ──────────────────────────────────────────────────────────────────────
# 結果テーブル
# ──────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<h3 style='font-size:20px;'>📊 返済シミュレーション結果</h3>",
    unsafe_allow_html=True
)
st.caption(
    f"②BAD金利推移：{var_rate:.3f}%（1年目）→ "
    f"{var_rate + 0.2*4:.3f}%（5年目）→ "
    f"{var_rate + 0.2*9:.3f}%（10年目）→ "
    f"{var_rate + 0.2*19:.3f}%（20年目）→ "
    f"{var_rate + 0.2*(years-1):.3f}%（{years}年目）"
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

# 返済総額サマリー
st.markdown("**返済総額まとめ**")
summary_df = pd.DataFrame([
    {"シナリオ": "①変動 現状維持",
     "返済総額（万円）": f"{total_var:,.0f}",
     "①との差額（万円）": "―"},
    {"シナリオ": "②変動 BAD（年+0.2%上昇）",
     "返済総額（万円）": f"{total_bad:,.0f}",
     "①との差額（万円）": f"+{total_bad - total_var:,.0f}"},
    {"シナリオ": f"③固定 フラット35 S（{total_points}P）",
     "返済総額（万円）": f"{total_flat:,.0f}",
     "①との差額（万円）": f"+{total_flat - total_var:,.0f}"},
])
st.dataframe(summary_df, use_container_width=True, hide_index=True)

# ──────────────────────────────────────────────────────────────────────
# フラット35 S 引下げ対応表
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
    "<h3 style='font-size:20px;'>📈 差額投資シミュレーション（①変動現状維持 vs ③固定）</h3>",
    unsafe_allow_html=True
)

monthly_var  = monthly_payment(loan_amount * 10_000, var_rate,  years * 12)
monthly_flat = monthly_payment(loan_amount * 10_000, flat_base, years * 12)
diff_monthly = monthly_flat - monthly_var

c9, c10 = st.columns(2)
with c9:
    st.metric("①変動 月額返済",       f"{monthly_var:,.0f} 円")
    st.metric("③フラット35 月額返済", f"{monthly_flat:,.0f} 円")
with c10:
    st.metric("差額（月）",   f"{diff_monthly:,.0f} 円")
    st.metric("差額（総額）", f"{diff_monthly * years * 12:,.0f} 円")

c11, c12 = st.columns(2)
with c11:
    invest_rate = st.number_input(
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
# どちらを選ぶ？（差額投資の下に追加）
# ──────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<h3 style='font-size:20px;'>🤔 変動 vs 固定　どちらを選ぶ？</h3>",
    unsafe_allow_html=True
)

col_a, col_b = st.columns(2)
with col_a:
    st.markdown("""
<div style="background:#dbeafe; border-radius:10px; padding:16px; height:100%;">
<h4 style="color:#1d4ed8; margin-top:0;">📈 変動金利を選ぶ方</h4>
<p>
固定金利を支払っているつもりで<br>
<b>差額を毎月運用する</b><br><br>
変動金利で借りて、固定との差額を積立投資に回すことで、
長期的に大きな資産形成が期待できます。<br><br>
ただし、<b>金利上昇リスク・運用リスク</b>を
自己管理できる方向けです。
</p>
</div>
""", unsafe_allow_html=True)

with col_b:
    st.markdown("""
<div style="background:#dcfce7; border-radius:10px; padding:16px; height:100%;">
<h4 style="color:#15803d; margin-top:0;">🛡️ 固定金利を選ぶ方</h4>
<p>
金利上昇リスク・運用失敗リスク・<br>
<b>精神的ストレスを避けたい方</b><br><br>
返済額が全期間固定で、家計設計が安定します。
金利がどう動いても毎月の支払いは変わらず、
安心して生活できます。<br><br>
<b>安定・安心を最優先する方</b>向けです。
</p>
</div>
""", unsafe_allow_html=True)

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
            total_var=total_var,
            total_bad=total_bad,
            total_flat=total_flat,
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
# ===== 公式LINEバナー（×で閉じられる） =====
import urllib.parse as _url

def render_line_banner():
    if "line_banner_closed" not in st.session_state:
        st.session_state.line_banner_closed = False

    try:
        qp = st.query_params
        close_flag = str(qp.get("close_banner", "0")) == "1"
        qp_dict = dict(qp)
    except Exception:
        qp = st.experimental_get_query_params()
        close_flag = (qp.get("close_banner", ["0"])[0] == "1")
        qp_dict = {k: (v[0] if isinstance(v, list) else v) for k, v in qp.items()}

    if close_flag:
        st.session_state.line_banner_closed = True

    if st.session_state.line_banner_closed:
        return

    qp_dict = {k: (v if not isinstance(v, list) else v[0]) for k, v in qp_dict.items()}
    qp_dict["close_banner"] = "1"
    qs = _url.urlencode(qp_dict)
    close_url = "?" + qs if qs else "?close_banner=1"

    st.markdown(f"""
    <style>
    .line-banner-wrap {{
      position: fixed;
      bottom: 100px; right: 18px; z-index: 9999;
    }}
    .line-banner {{
      background: #06C755; color: #fff;
      padding: 14px 18px 20px; border-radius: 12px;
      box-shadow: 0 4px 10px rgba(0,0,0,0.25);
      font-size: 15px; text-align: center; position: relative;
    }}
    .line-banner:hover {{ transform: scale(1.02); background:#05b34d; }}
    .line-banner .ttl {{ font-size: 17px; font-weight: 800; line-height: 1.4; }}
    .line-banner .id  {{ font-size: 20px; font-weight: 900; margin: 6px 0 6px; }}
    .line-banner img  {{
      width: 130px; display:block; margin: 8px auto 10px;
      border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.3);
      background:#fff;
    }}
    .line-banner .cta {{ display:inline-block; font-weight: 800; text-decoration: underline; color:#fff; }}
    .line-banner .close-btn {{
      position:absolute; top:6px; right:10px; width:24px; height:24px;
      border-radius:50%; background: rgba(0,0,0,0.25);
      color:#fff; text-align:center; line-height:24px;
      font-size:16px; font-weight:700; text-decoration:none;
    }}
    .line-banner .close-btn:hover {{ background: rgba(0,0,0,0.4); }}
    @media (max-width: 768px){{
      .line-banner-wrap {{ bottom: 100px; right: 14px; }}
      .line-banner {{ padding: 12px 14px 18px; }}
      .line-banner img {{ width: 110px; }}
      .line-banner .id {{ font-size: 18px; }}
    }}
    </style>

    <div class="line-banner-wrap" id="line-banner">
      <div class="line-banner" role="region" aria-label="LINE公式バナー">
        <a class="close-btn" href="{close_url}" aria-label="バナーを閉じる">×</a>
        <a href="https://lin.ee/m40HEqN" target="_blank" rel="noopener" style="text-decoration:none; color:#fff;">
          <div class="ttl">📲 シミュレーション利用は<br>LINEで簡単・不動産相談</div>
          <div class="id">LINE ID：@fudo3</div>
          <img src="https://qr-official.line.me/gs/M_277qthwd_GW.png?oat_content=qr" alt="LINE公式QRコード">
          <span class="cta">▶ 公式LINEで相談する</span>
        </a>
      </div>
    </div>
    """, unsafe_allow_html=True)

render_line_banner()
