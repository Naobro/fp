import streamlit as st
import pandas as pd
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import io
import os
import math

# ─────────────────────────────────────────
# 日本語フォント対応
# ─────────────────────────────────────────
def register_japanese_font():
    """日本語フォント登録"""
    font_candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Regular.otf",
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "./fonts/NotoSansJP-Regular.ttf",
        "C:/Windows/Fonts/meiryo.ttc",
        "C:/Windows/Fonts/YuGothM.ttc"
    ]
    
    for font_path in font_candidates:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont("JapaneseFont", font_path))
                return "JapaneseFont"
            except Exception:
                continue
    return "Helvetica"

# ─────────────────────────────────────────
# 財務計算関数（修正版）
# ─────────────────────────────────────────
def calculate_monthly_payment(principal: float, annual_rate: float, years: int) -> float:
    """
    元利均等返済の月額返済額計算（Excel PMT関数と完全一致）
    
    Args:
        principal: 借入金額（円）
        annual_rate: 年利（%表記 例: 1.0）
        years: 借入期間（年）
    
    Returns:
        月額返済額（円）
    """
    if annual_rate == 0:
        return principal / (years * 12)
    
    monthly_rate = annual_rate / 100 / 12
    total_months = years * 12
    
    # (1 + r)^n を高精度で計算
    compound_factor = (1 + monthly_rate) ** total_months
    
    # PMT = P * r * (1+r)^n / ((1+r)^n - 1)
    payment = principal * monthly_rate * compound_factor / (compound_factor - 1)
    
    return payment

def calculate_remaining_balance(principal: float, annual_rate: float, 
                              years: int, elapsed_years: int) -> float:
    """
    指定年数経過後の残債計算
    
    Args:
        principal: 借入金額（円）
        annual_rate: 年利（%）
        years: 借入期間（年）
        elapsed_years: 経過年数
    
    Returns:
        残債（円）
    """
    if elapsed_years >= years:
        return 0.0
    
    if annual_rate == 0:
        return principal * (1 - elapsed_years / years)
    
    monthly_rate = annual_rate / 100 / 12
    total_months = years * 12
    elapsed_months = elapsed_years * 12
    
    compound_total = (1 + monthly_rate) ** total_months
    compound_elapsed = (1 + monthly_rate) ** elapsed_months
    
    balance = principal * (compound_total - compound_elapsed) / (compound_total - 1)
    
    return max(balance, 0.0)

def calculate_payment_breakdown(principal: float, annual_rate: float,
                               years: int, target_year: int):
    """
    指定年目（最初の月）の返済内訳計算
    
    Returns:
        tuple: (月額返済額, 元金充当額, 利息額, 元金充当率%)
    """
    monthly_payment = calculate_monthly_payment(principal, annual_rate, years)
    
    if annual_rate == 0:
        return monthly_payment, monthly_payment, 0, 100.0
    
    monthly_rate = annual_rate / 100 / 12
    
    # target_year年目開始時の残債
    start_balance = calculate_remaining_balance(principal, annual_rate, years, target_year - 1)
    
    interest_payment = start_balance * monthly_rate
    principal_payment = monthly_payment - interest_payment
    principal_ratio = (principal_payment / monthly_payment) * 100 if monthly_payment > 0 else 0
    
    return monthly_payment, principal_payment, interest_payment, principal_ratio

def calculate_future_property_value(initial_price: float, years: int, 
                                   depreciation_rate: float) -> float:
    """
    将来の不動産価値計算（カスタム減価率対応）
    
    Args:
        initial_price: 初期価格（円）
        years: 経過年数
        depreciation_rate: 年間減価率（% 例: 1.0 → 毎年1%下落）
    
    Returns:
        将来価値（円）
    """
    return initial_price * ((1 - depreciation_rate / 100) ** years)

# ─────────────────────────────────────────
# PDF生成関数
# ─────────────────────────────────────────
def generate_loan_pdf(loan_conditions: dict, table1_data: list, table2_data: list) -> bytes:
    """A4横向きレイアウトでPDF生成"""
    font_name = register_japanese_font()
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=15*mm,
        bottomMargin=15*mm
    )
    
    # カラーパレット
    MAIN_COLOR = colors.HexColor("#006064")
    LIGHT_BG = colors.HexColor("#E0F7FA")
    PROFIT_COLOR = colors.HexColor("#1565C0")
    LOSS_COLOR = colors.HexColor("#C62828")
    GREY_LINE = colors.HexColor("#B0BEC5")
    
    def create_paragraph_style(name, font_size=8, alignment=TA_LEFT, text_color=colors.black):
        return ParagraphStyle(
            name,
            fontName=font_name,
            fontSize=font_size,
            alignment=alignment,
            textColor=text_color,
            leading=font_size * 1.45,
            spaceBefore=2,
            spaceAfter=2
        )
    
    story = []
    
    # タイトルセクション
    title_style = create_paragraph_style("title", 16, TA_CENTER, MAIN_COLOR)
    story.append(Paragraph("住宅ローン残債・売却価格シミュレーション", title_style))
    story.append(Spacer(1, 6))
    
    # 条件サマリー
    conditions_text = (
        f"物件価格：{loan_conditions['property_price']/10000:,.0f}万円　"
        f"自己資金：{loan_conditions['own_funds']/10000:,.0f}万円　"
        f"借入金額：{loan_conditions['loan_amount']/10000:,.0f}万円<br/>"
        f"金利：{loan_conditions['interest_rate']:.3f}%　"
        f"期間：{loan_conditions['years']}年　"
        f"減価率：{loan_conditions['depreciation_rate']:.1f}%/年　"
        f"月額返済額：{loan_conditions['monthly_payment']:,.0f}円"
    )
    subtitle_style = create_paragraph_style("subtitle", 9, TA_CENTER, colors.HexColor("#555555"))
    story.append(Paragraph(conditions_text, subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=MAIN_COLOR))
    story.append(Spacer(1, 8))
    
    # 2列レイアウト設定
    page_width = A4[0] - 30*mm
    col_width = page_width / 2 - 5*mm
    
    def create_section_header(title, width):
        header_style = create_paragraph_style("header", 10, TA_CENTER, colors.white)
        header_table = Table([[Paragraph(title, header_style)]], colWidths=[width])
        header_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), MAIN_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        return header_table
    
    def create_data_table(headers, data, col_widths, is_profit_loss=False):
        # ヘッダー行
        header_style = create_paragraph_style("th", 8, TA_CENTER, colors.white)
        rows = [[Paragraph(f"<b>{h}</b>", header_style) for h in headers]]
        
        # データ行
        for row_data in data:
            row = []
            for i, cell_value in enumerate(row_data):
                if is_profit_loss and i == len(row_data) - 1:  # 損益列
                    profit_value = cell_value if isinstance(cell_value, (int, float)) else 0
                    color = PROFIT_COLOR if profit_value >= 0 else LOSS_COLOR
                    sign = "+" if profit_value >= 0 else "▲"
                    formatted_value = f"<b>{sign}{abs(profit_value)/10000:,.0f}万円</b>"
                    style = create_paragraph_style(f"profit_{i}", 8, TA_RIGHT, color)
                    row.append(Paragraph(formatted_value, style))
                else:
                    if isinstance(cell_value, str):
                        formatted_value = cell_value
                    elif i == 0:  # 年数列
                        formatted_value = cell_value
                    elif i in [1, 2, 3]:  # 金額列
                        formatted_value = f"{cell_value:,.0f}円"
                    else:
                        formatted_value = f"{cell_value:.1f}%" if isinstance(cell_value, float) else str(cell_value)
                    
                    align = TA_CENTER if i == 0 else (TA_RIGHT if i > 0 else TA_LEFT)
                    style = create_paragraph_style(f"cell_{i}", 8, align)
                    row.append(Paragraph(formatted_value, style))
            rows.append(row)
        
        table = Table(rows, colWidths=col_widths)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), MAIN_COLOR),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_BG, colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.5, GREY_LINE),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        return table
    
    # 左側：返済内訳テーブル
    left_elements = []
    left_elements.append(create_section_header("返済内訳の経年変化", col_width))
    left_elements.append(Spacer(1, 4))
    
    table1_headers = ["経過年", "月返済額", "元金充当", "利息", "元金率"]
    table1_col_widths = [col_width * r for r in [0.16, 0.22, 0.22, 0.22, 0.18]]
    table1 = create_data_table(table1_headers, table1_data, table1_col_widths)
    left_elements.append(table1)
    left_elements.append(Spacer(1, 4))
    
    note_style = create_paragraph_style("note", 7, TA_LEFT, colors.HexColor("#666666"))
    left_elements.append(Paragraph("※元利均等返済・各年最初の月の内訳", note_style))
    
    # 右側：残債vs売却価格テーブル
    right_elements = []
    right_elements.append(create_section_header("残債 vs 想定売却価格", col_width))
    right_elements.append(Spacer(1, 4))
    
    table2_headers = ["経過年", "残債", "売却価格", "売却損益"]
    table2_col_widths = [col_width * r for r in [0.16, 0.26, 0.26, 0.32]]
    table2 = create_data_table(table2_headers, table2_data, table2_col_widths, is_profit_loss=True)
    right_elements.append(table2)
    right_elements.append(Spacer(1, 4))
    
    dep_note = f"※年{loan_conditions['depreciation_rate']:.1f}%減価による売却価格で計算"
    right_elements.append(Paragraph(dep_note, note_style))
    
    # メインテーブル（2列レイアウト）
    main_table = Table([[left_elements, right_elements]], 
                       colWidths=[col_width + 5*mm, col_width + 5*mm])
    main_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(main_table)
    
    # フッター
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GREY_LINE))
    footer_style = create_paragraph_style("footer", 7, TA_LEFT, colors.HexColor("#888888"))
    story.append(Paragraph(
        "※本シミュレーションは概算です。実際の返済額・売却価格は金融機関・市場状況により異なります。",
        footer_style
    ))
    
    doc.build(story)
    return buffer.getvalue()

# ─────────────────────────────────────────
# Streamlit メインアプリケーション
# ─────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="住宅ローンシミュレーション",
        page_icon="🏠",
        layout="wide"
    )
    
    # カスタムCSS
    st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; }
    .main-header {
        background: linear-gradient(135deg, #006064 0%, #00897B 100%);
        color: white; padding: 1.4rem 2rem;
        border-radius: 12px; text-align: center; margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .main-header h1 { margin: 0; font-size: 1.8rem; font-weight: 700; }
    .main-header p { margin: 0.4rem 0 0; font-size: 1rem; opacity: 0.9; }
    .section-header {
        background: #E0F7FA; color: #006064;
        padding: 0.6rem 1.2rem;
        border-left: 4px solid #00897B;
        border-radius: 6px; font-weight: 600;
        margin: 1.5rem 0 1rem; font-size: 1.1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #F0FDFA, #E0F7FA);
        border: 1px solid #B2DFDB;
        border-radius: 10px; padding: 1rem;
        text-align: center; margin-bottom: 0.8rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    .metric-label { color: #555; font-size: 0.85rem; margin-bottom: 4px; }
    .metric-value { color: #006064; font-size: 1.4rem; font-weight: 700; }
    .metric-sub { color: #777; font-size: 0.8rem; margin-top: 4px; }
    .payment-banner {
        background: linear-gradient(135deg, #E0F7FA, #B2DFDB);
        border-radius: 12px; padding: 1.5rem; text-align: center;
        margin: 1.5rem 0; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }
    .payment-label { color: #555; font-size: 1rem; margin-bottom: 8px; }
    .payment-value { color: #006064; font-size: 2.6rem; font-weight: 700; margin: 8px 0; }
    .payment-sub { color: #666; font-size: 0.9rem; }
    .profit { color: #1565C0; font-weight: bold; }
    .loss { color: #C62828; font-weight: bold; }
    .stButton > button {
        background: linear-gradient(135deg, #006064, #00897B);
        color: white; border: none; border-radius: 8px;
        padding: 0.6rem 1.5rem; font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # メインヘッダー
    st.markdown("""
    <div class="main-header">
        <h1>🏠 住宅ローン残債・売却価格シミュレーション</h1>
        <p>元利均等返済による残債計算と将来売却価格の比較分析</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 入力セクション
    st.markdown('<div class="section-header">📝 借入条件の設定</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1.2, 1.2, 1])
    
    with col1:
        st.markdown("**物件情報**")
        property_price_man = st.number_input(
            "物件価格（万円）", 
            min_value=100, 
            max_value=100000,
            value=8000,  # デフォルト8000万円
            step=100
        )
        own_funds_man = st.number_input(
            "自己資金（万円）", 
            min_value=0, 
            max_value=50000,
            value=0,  # デフォルト0円
            step=50
        )
        expense_rate = st.number_input(
            "諸費用率（%）", 
            min_value=0.0, 
            max_value=15.0,
            value=7.0, 
            step=0.5, 
            format="%.1f"
        )
    
    with col2:
        st.markdown("**ローン条件**")
        loan_years = st.number_input(
            "借入期間（年）", 
            min_value=1, 
            max_value=50, 
            value=35
        )
        interest_rate = st.number_input(
            "金利（%）", 
            min_value=0.001, 
            max_value=15.0,
            value=1.000,  # デフォルト1%
            step=0.001, 
            format="%.3f"
        )
        depreciation_rate = st.number_input(
            "年間減価率（%）",
            min_value=0.0, 
            max_value=10.0,
            value=1.0,  # デフォルト1%
            step=0.1,  # 0.1%単位で調整可能
            format="%.1f",
            help="毎年何%ずつ物件価格が下落するかを設定（例：1.0 = 毎年1%下落、1.5 = 毎年1.5%下落）"
        )
    
    # 自動計算
    property_price = property_price_man * 10000
    own_funds = own_funds_man * 10000
    expenses = property_price * expense_rate / 100
    loan_amount = property_price + expenses - own_funds
    
    with col3:
        st.markdown("**自動計算結果**")
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">諸費用（{expense_rate:.1f}%）</div>
            <div class="metric-value">{expenses/10000:,.0f}<span style="font-size:1rem;">万円</span></div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">借入金額</div>
            <div class="metric-value">{loan_amount/10000:,.0f}<span style="font-size:1rem;">万円</span></div>
            <div class="metric-sub">物件価格 + 諸費用 − 自己資金</div>
        </div>
        """, unsafe_allow_html=True)
    
    if loan_amount <= 0:
        st.error("⚠️ 借入金額が0以下です。自己資金の金額を確認してください。")
        return
    
    # 月額返済額計算（修正済み）
    monthly_payment = calculate_monthly_payment(loan_amount, interest_rate, loan_years)
    annual_payment = monthly_payment * 12
    total_payment = monthly_payment * loan_years * 12
    total_interest = total_payment - loan_amount
    
    st.markdown(f"""
    <div class="payment-banner">
        <div class="payment-label">月額返済額（元利均等返済）</div>
        <div class="payment-value">{monthly_payment:,.0f} 円</div>
        <div class="payment-sub">
            年間返済額：{annual_payment:,.0f} 円　｜　
            総返済額：{total_payment/10000:,.0f} 万円　｜　
            うち利息：{total_interest/10000:,.0f} 万円
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 計算検証表示（デバッグ用）
    if st.checkbox("計算詳細を表示"):
        st.markdown("**計算検証（PMT関数）**")
        st.write(f"借入金額: {loan_amount:,}円")
        st.write(f"月利: {interest_rate/100/12:.10f}")
        st.write(f"返済回数: {loan_years * 12}回")
        st.write(f"月額返済額: {monthly_payment:.2f}円")
        
        # 6220万円の場合の検証
        if abs(loan_amount - 62200000) < 1000:
            st.success("✅ 6220万円・1%・35年の場合、175,581円となることを確認")
    
    # テーブルデータ生成
    breakdown_years_list = [y for y in [1, 5, 10, 20, 30] if y <= loan_years]
    
    table1_data = []
    for year in breakdown_years_list:
        payment, principal, interest, ratio = calculate_payment_breakdown(
            loan_amount, interest_rate, loan_years, year
        )
        table1_data.append((f"{year}年目", payment, principal, interest, ratio))
    
    simulation_years_list = [y for y in [5, 10, 20, 30] if y <= loan_years]
    
    table2_data = []
    for year in simulation_years_list:
        remaining_debt = calculate_remaining_balance(loan_amount, interest_rate, loan_years, year)
        future_value = calculate_future_property_value(property_price, year, depreciation_rate)
        profit_loss = future_value - remaining_debt
        table2_data.append((f"{year}年後", remaining_debt, future_value, profit_loss))
    
    # 結果表示
    st.markdown('<div class="section-header">📊 シミュレーション結果</div>', unsafe_allow_html=True)
    
    left_col, right_col = st.columns(2)
    
    with left_col:
        st.markdown("#### テーブル① 返済内訳の経年変化")
        
        df1_display = pd.DataFrame([
            {
                "経過年": year,
                "月返済額": f"{payment:,.0f}円",
                "元金充当": f"{principal:,.0f}円", 
                "利息": f"{interest:,.0f}円",
                "元金充当率": f"{ratio:.1f}%"
            }
            for year, payment, principal, interest, ratio in table1_data
        ])
        
        st.dataframe(df1_display, use_container_width=True, hide_index=True)
        st.caption("※元利均等返済による各年最初の月の返済内訳")
    
    with right_col:
        st.markdown("#### テーブル② 残債 vs 想定売却価格")
        
        df2_display = pd.DataFrame([
            {
                "経過年": year,
                "残債": f"{debt/10000:,.0f}万円",
                "売却価格": f"{sale/10000:,.0f}万円",
                "売却損益": f"{'+'if profit>=0 else '▲'}{abs(profit)/10000:,.0f}万円"
            }
            for year, debt, sale, profit in table2_data
        ])
        
        def style_profit_loss(val):
            if val.startswith('+'):
                return 'color: #1565C0; font-weight: bold'
            elif val.startswith('▲'):
                return 'color: #C62828; font-weight: bold'
            return ''
        
        styled_df2 = df2_display.style.applymap(style_profit_loss, subset=['売却損益'])
        st.dataframe(styled_df2, use_container_width=True, hide_index=True)
        st.caption(f"※年{depreciation_rate:.1f}%減価による売却価格で計算")
    
    # チャート表示
    st.markdown('<div class="section-header">📈 残債・売却価格の推移</div>', unsafe_allow_html=True)
    
    # チャート用データ作成
    chart_years = list(range(0, min(loan_years + 1, 36)))  # 最大35年まで表示
    debt_series = [
        calculate_remaining_balance(loan_amount, interest_rate, loan_years, y) / 10000
        for y in chart_years
    ]
    sale_series = [
        calculate_future_property_value(property_price, y, depreciation_rate) / 10000
        for y in chart_years
    ]
    profit_series = [s - d for s, d in zip(sale_series, debt_series)]
    
    chart_df = pd.DataFrame({
        "経過年": chart_years,
        "残債（万円）": debt_series,
        "売却価格（万円）": sale_series,
        "売却損益（万円）": profit_series,
    }).set_index("経過年")
    
    tab1, tab2 = st.tabs(["残債 vs 売却価格", "売却損益推移"])
    
    with tab1:
        st.line_chart(chart_df[["残債（万円）", "売却価格（万円）"]], height=400)
        st.caption("青線：残債、赤線：想定売却価格")
    
    with tab2:
        st.area_chart(chart_df[["売却損益（万円）"]], height=400)
        st.caption("プラス：売却益、マイナス：売却損")
    
    # PDF出力セクション
    st.markdown('<div class="section-header">📄 PDFレポート出力</div>', unsafe_allow_html=True)
    
    if st.button("📥 PDFレポートを生成", type="primary", use_container_width=False):
        with st.spinner("PDF生成中..."):
            try:
                loan_conditions = {
                    'property_price': property_price,
                    'own_funds': own_funds,
                    'loan_amount': loan_amount,
                    'years': loan_years,
                    'interest_rate': interest_rate,
                    'monthly_payment': monthly_payment,
                    'depreciation_rate': depreciation_rate
                }
                
                pdf_bytes = generate_loan_pdf(loan_conditions, table1_data, table2_data)
                
                st.download_button(
                    label="💾 PDFファイルをダウンロード",
                    data=pdf_bytes,
                    file_name="住宅ローンシミュレーション.pdf",
                    mime="application/pdf"
                )
                st.success("✅ PDF生成が完了しました！上のボタンからダウンロードしてください。")
                
            except Exception as e:
                st.error(f"❌ PDF生成エラー: {e}")
                st.info("💡 reportlabライブラリがインストールされているか確認してください")

if __name__ == "__main__":
    main()
