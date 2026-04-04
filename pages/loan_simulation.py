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

# ─────────────────────────────────────────
# 日本語フォント対応
# ─────────────────────────────────────────
def register_japanese_font():
    """日本語フォントを登録する"""
    font_candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Regular.otf", 
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "./fonts/NotoSansJP-Regular.ttf"
    ]
    
    for font_path in font_candidates:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont("JapaneseFont", font_path))
                return "JapaneseFont"
            except Exception:
                continue
    return "Helvetica"  # フォールバック

# ─────────────────────────────────────────
# 財務計算関数
# ─────────────────────────────────────────
def calculate_monthly_payment(principal: float, annual_rate: float, years: int) -> float:
    """
    元利均等返済の月額返済額を計算（PMT関数相当）
    
    Args:
        principal: 借入金額（円）
        annual_rate: 年利（%）
        years: 借入期間（年）
    
    Returns:
        月額返済額（円）
    """
    monthly_rate = annual_rate / 100 / 12
    total_months = years * 12
    
    if monthly_rate == 0:
        return principal / total_months
    
    payment = principal * monthly_rate * (1 + monthly_rate) ** total_months / (
        (1 + monthly_rate) ** total_months - 1
    )
    return payment

def calculate_remaining_balance(principal: float, annual_rate: float, 
                              years: int, elapsed_years: int) -> float:
    """
    指定年数経過時点の残債を計算
    
    Args:
        principal: 借入金額（円）
        annual_rate: 年利（%）
        years: 借入期間（年）
        elapsed_years: 経過年数
    
    Returns:
        残債（円）
    """
    monthly_rate = annual_rate / 100 / 12
    total_months = years * 12
    elapsed_months = elapsed_years * 12
    
    if monthly_rate == 0:
        return principal * (1 - elapsed_months / total_months)
    
    balance = principal * (
        (1 + monthly_rate) ** total_months - (1 + monthly_rate) ** elapsed_months
    ) / ((1 + monthly_rate) ** total_months - 1)
    
    return max(balance, 0)

def calculate_payment_breakdown(principal: float, annual_rate: float,
                               years: int, target_year: int):
    """
    指定年目の返済内訳を計算
    
    Args:
        principal: 借入金額（円）
        annual_rate: 年利（%）
        years: 借入期間（年）
        target_year: 対象年（1年目、5年目など）
    
    Returns:
        tuple: (月額返済額, 元金充当額, 利息額, 元金充当率)
    """
    monthly_payment = calculate_monthly_payment(principal, annual_rate, years)
    monthly_rate = annual_rate / 100 / 12
    
    # その年の開始時点での残債を計算
    start_balance = calculate_remaining_balance(principal, annual_rate, years, target_year - 1)
    
    # その年の利息と元金を計算
    interest_payment = start_balance * monthly_rate
    principal_payment = monthly_payment - interest_payment
    principal_ratio = (principal_payment / monthly_payment) * 100
    
    return monthly_payment, principal_payment, interest_payment, principal_ratio

def calculate_future_property_value(initial_price: float, years: int, 
                                   depreciation_rate: float = 1.0) -> float:
    """
    年1%減価計算による将来の不動産価値
    
    Args:
        initial_price: 初期価格（円）
        years: 経過年数
        depreciation_rate: 年間減価率（%）
    
    Returns:
        将来価値（円）
    """
    return initial_price * (1 - depreciation_rate / 100) ** years

# ─────────────────────────────────────────
# PDF生成関数
# ─────────────────────────────────────────
def generate_loan_pdf(loan_conditions: dict, table1_data: list, table2_data: list) -> bytes:
    """
    住宅ローンシミュレーション結果のPDFを生成
    
    Args:
        loan_conditions: ローン条件の辞書
        table1_data: テーブル①のデータ
        table2_data: テーブル②のデータ
    
    Returns:
        PDF バイトデータ
    """
    font_name = register_japanese_font()
    buffer = io.BytesIO()
    
    # A4サイズでドキュメント作成
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=15*mm,
        bottomMargin=15*mm
    )
    
    # スタイル定義
    styles = getSampleStyleSheet()
    
    def create_style(name, font_size=9, alignment=TA_LEFT, text_color=colors.black, bold=False):
        return ParagraphStyle(
            name,
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=font_size,
            alignment=alignment,
            textColor=text_color,
            leading=font_size * 1.4,
            spaceBefore=2,
            spaceAfter=4
        )
    
    title_style = create_style("Title", 16, TA_CENTER, colors.HexColor("#006064"), True)
    subtitle_style = create_style("Subtitle", 10, TA_CENTER, colors.HexColor("#555555"))
    header_style = create_style("Header", 11, TA_LEFT, colors.white, True)
    body_style = create_style("Body", 9)
    note_style = create_style("Note", 8, text_color=colors.HexColor("#666666"))
    
    # カラー定義
    MAIN_COLOR = colors.HexColor("#006064")
    LIGHT_BG = colors.HexColor("#F0F8FF")
    PROFIT_COLOR = colors.HexColor("#1565C0")
    LOSS_COLOR = colors.HexColor("#C62828")
    
    story = []
    
    # タイトル
    story.append(Paragraph("住宅ローン残債・売却価格シミュレーション", title_style))
    story.append(Spacer(1, 8))
    
    # ローン条件サマリー
    conditions_text = (
        f"物件価格：{loan_conditions['property_price']/10000:,.0f}万円　"
        f"自己資金：{loan_conditions['own_funds']/10000:,.0f}万円　"
        f"借入金額：{loan_conditions['loan_amount']/10000:,.0f}万円<br/>"
        f"金利：{loan_conditions['interest_rate']:.3f}%　"
        f"期間：{loan_conditions['years']}年　"
        f"月額返済額：{loan_conditions['monthly_payment']:,.0f}円"
    )
    story.append(Paragraph(conditions_text, subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=MAIN_COLOR))
    story.append(Spacer(1, 10))
    
    # 左右2列レイアウト用のテーブル作成
    page_width = A4[0] - 30*mm  # 左右マージンを除いた幅
    col_width = page_width / 2 - 5*mm
    
    # テーブル①（左側）
    def create_table1():
        elements = []
        
        # ヘッダー
        header_para = Paragraph("返済内訳の経年変化", header_style)
        header_table = Table([[header_para]], colWidths=[col_width])
        header_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), MAIN_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 5))
        
        # データテーブル
        headers = ["経過年", "月返済額", "元金充当", "利息", "元金率"]
        col_widths = [col_width * r for r in [0.18, 0.23, 0.23, 0.23, 0.13]]
        
        header_row = [Paragraph(f"<b>{h}</b>", create_style(f"th{i}", 8, TA_CENTER, colors.white)) 
                     for i, h in enumerate(headers)]
        
        rows = [header_row]
        for i, (year, payment, principal, interest, ratio) in enumerate(table1_data):
            row_cells = [
                Paragraph(year, create_style(f"td{i}0", 8, TA_CENTER)),
                Paragraph(f"{payment:,.0f}円", create_style(f"td{i}1", 8, TA_RIGHT)),
                Paragraph(f"{principal:,.0f}円", create_style(f"td{i}2", 8, TA_RIGHT)),
                Paragraph(f"{interest:,.0f}円", create_style(f"td{i}3", 8, TA_RIGHT)),
                Paragraph(f"{ratio:.1f}%", create_style(f"td{i}4", 8, TA_CENTER))
            ]
            rows.append(row_cells)
        
        table1 = Table(rows, colWidths=col_widths)
        table1.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), MAIN_COLOR),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_BG, colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elements.append(table1)
        
        elements.append(Spacer(1, 5))
        elements.append(Paragraph("※元利均等返済による計算", note_style))
        
        return elements
    
    # テーブル②（右側）
    def create_table2():
        elements = []
        
        # ヘッダー
        header_para = Paragraph("残債 vs 想定売却価格", header_style)
        header_table = Table([[header_para]], colWidths=[col_width])
        header_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), MAIN_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 5))
        
        # データテーブル
        headers2 = ["経過年", "残債", "売却価格", "売却損益"]
        col_widths2 = [col_width * r for r in [0.18, 0.27, 0.27, 0.28]]
        
        header_row2 = [Paragraph(f"<b>{h}</b>", create_style(f"t2h{i}", 8, TA_CENTER, colors.white)) 
                      for i, h in enumerate(headers2)]
        
        rows2 = [header_row2]
        for i, (year, debt, sale_price, profit) in enumerate(table2_data):
            profit_color = PROFIT_COLOR if profit >= 0 else LOSS_COLOR
            sign = "+" if profit >= 0 else "▲"
            
            row_cells2 = [
                Paragraph(year, create_style(f"t2d{i}0", 8, TA_CENTER)),
                Paragraph(f"{debt/10000:,.0f}万円", create_style(f"t2d{i}1", 8, TA_RIGHT)),
                Paragraph(f"{sale_price/10000:,.0f}万円", create_style(f"t2d{i}2", 8, TA_RIGHT)),
                Paragraph(f"<b>{sign}{abs(profit)/10000:,.0f}万円</b>", 
                         create_style(f"t2d{i}3", 8, TA_RIGHT, profit_color))
            ]
            rows2.append(row_cells2)
        
        table2 = Table(rows2, colWidths=col_widths2)
        table2.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), MAIN_COLOR),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_BG, colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elements.append(table2)
        
        elements.append(Spacer(1, 5))
        elements.append(Paragraph("※年1%減価で計算", note_style))
        
        return elements
    
    # 左右配置
    left_content = create_table1()
    right_content = create_table2()
    
    main_table = Table([[left_content, right_content]], colWidths=[col_width + 5*mm, col_width + 5*mm])
    main_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    
    story.append(main_table)
    
    # フッター
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Paragraph(
        "※本シミュレーションは概算です。実際の返済額・売却価格は金融機関・市場状況により異なります。",
        note_style
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
    .main-header {
        background: linear-gradient(135deg, #006064, #00897B);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        background: #E0F7FA;
        color: #006064;
        padding: 0.8rem 1rem;
        border-left: 4px solid #00897B;
        border-radius: 5px;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    .metric-box {
        background: #F0FDFA;
        border: 1px solid #B2DFDB;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
    }
    .profit { color: #1565C0; font-weight: bold; }
    .loss { color: #C62828; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)
    
    # メインヘッダー
    st.markdown("""
    <div class="main-header">
        <h1>🏠 住宅ローン残債・売却価格シミュレーション</h1>
        <p>元利均等返済による残債計算と年1%減価による売却価格を比較分析</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 入力セクション
    st.markdown('<div class="section-header">📝 借入条件の設定</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("物件情報")
        property_price_man = st.number_input(
            "物件価格（万円）", 
            min_value=100, 
            max_value=50000, 
            value=6280, 
            step=50
        )
        own_funds_man = st.number_input(
            "自己資金（万円）", 
            min_value=0, 
            max_value=20000, 
            value=500, 
            step=50
        )
    
    with col2:
        st.subheader("ローン条件")
        loan_years = st.number_input(
            "借入期間（年）", 
            min_value=1, 
            max_value=50, 
            value=35
        )
        interest_rate = st.number_input(
            "金利（%）", 
            min_value=0.001, 
            max_value=10.0, 
            value=1.000, 
            step=0.001, 
            format="%.3f"
        )
    
    # 自動計算
    property_price = property_price_man * 10000
    own_funds = own_funds_man * 10000
    expenses = property_price * 0.07  # 諸費用7%
    loan_amount = property_price + expenses - own_funds
    
    with col3:
        st.subheader("計算結果")
        st.markdown(f"""
        <div class="metric-box">
            <div style="color: #555; font-size: 0.9rem;">諸費用（7%）</div>
            <div style="color: #006064; font-size: 1.2rem; font-weight: 600;">
                {expenses/10000:,.0f} 万円
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="metric-box">
            <div style="color: #555; font-size: 0.9rem;">借入金額</div>
            <div style="color: #006064; font-size: 1.5rem; font-weight: 700;">
                {loan_amount/10000:,.0f} 万円
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    if loan_amount <= 0:
        st.error("⚠️ 借入金額が0以下です。自己資金の金額を確認してください。")
        return
    
    # 月額返済額計算
    monthly_payment = calculate_monthly_payment(loan_amount, interest_rate, loan_years)
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #E0F7FA, #B2DFDB); 
                padding: 1.5rem; border-radius: 10px; text-align: center; margin: 2rem 0;">
        <div style="color: #555; font-size: 1rem;">月額返済額（元利均等）</div>
        <div style="color: #006064; font-size: 2.5rem; font-weight: 700;">
            {monthly_payment:,.0f} 円
        </div>
        <div style="color: #777; font-size: 0.9rem;">
            年間 {monthly_payment * 12:,.0f} 円
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # テーブルデータ生成
    breakdown_years = [1, 5, 10, 20, 30]
    breakdown_years = [y for y in breakdown_years if y <= loan_years]
    
    table1_data = []
    for year in breakdown_years:
        payment, principal, interest, ratio = calculate_payment_breakdown(
            loan_amount, interest_rate, loan_years, year
        )
        table1_data.append((f"{year}年目", payment, principal, interest, ratio))
    
    simulation_years = [5, 10, 20, 30]
    simulation_years = [y for y in simulation_years if y <= loan_years]
    
    table2_data = []
    for year in simulation_years:
        remaining_debt = calculate_remaining_balance(loan_amount, interest_rate, loan_years, year)
        future_value = calculate_future_property_value(property_price, year)
        profit_loss = future_value - remaining_debt
        table2_data.append((f"{year}年後", remaining_debt, future_value, profit_loss))
    
    # 結果表示
    st.markdown('<div class="section-header">📊 シミュレーション結果</div>', unsafe_allow_html=True)
    
    left_col, right_col = st.columns(2)
    
    with left_col:
        st.subheader("テーブル① 返済内訳の経年変化")
        
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
        st.caption("※元利均等返済による各年の返済内訳")
    
    with right_col:
        st.subheader("テーブル② 残債 vs 想定売却価格")
        
        df2_display = pd.DataFrame([
            {
                "経過年": year,
                "残債": f"{debt/10000:,.0f}万円",
                "売却価格": f"{sale/10000:,.0f}万円",
                "売却損益": f"{'+'if profit>=0 else '▲'}{abs(profit)/10000:,.0f}万円"
            }
            for year, debt, sale, profit in table2_data
        ])
        
        # 売却損益に色付け
        def style_profit_loss(val):
            if val.startswith('+'):
                return 'color: #1565C0; font-weight: bold'
            elif val.startswith('▲'):
                return 'color: #C62828; font-weight: bold'
            return ''
        
        styled_df2 = df2_display.style.applymap(style_profit_loss, subset=['売却損益'])
        st.dataframe(styled_df2, use_container_width=True, hide_index=True)
        st.caption("※年1%減価による売却価格で計算")
    
    # PDF出力セクション
    st.markdown('<div class="section-header">📄 PDF出力</div>', unsafe_allow_html=True)
    
    if st.button("📥 PDFレポートを生成", type="primary", use_container_width=False):
        with st.spinner("PDF生成中..."):
            try:
                loan_conditions = {
                    'property_price': property_price,
                    'own_funds': own_funds,
                    'loan_amount': loan_amount,
                    'years': loan_years,
                    'interest_rate': interest_rate,
                    'monthly_payment': monthly_payment
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
                st.info("💡 reportlabライブラリがインストールされているか確認してください: `pip install reportlab`")

if __name__ == "__main__":
    main()
