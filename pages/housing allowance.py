import math
from typing import Literal, Dict
import pandas as pd
import streamlit as st

# ================= ユーティリティ =================
def man_to_yen(v_man: float) -> float:
    return float(v_man) * 10_000.0

def yen_to_man(v_yen: float) -> float:
    return float(v_yen) / 10_000.0

def man(n_yen: float, digits: int = 1) -> str:
    return f"{yen_to_man(n_yen):,.{digits}f}万円"

def man_int(n_yen: float) -> str:
    return f"{yen_to_man(n_yen):,.0f}万円"

def annuity_payment(principal: float, annual_rate: float, years: int) -> float:
    """元利均等（年払い, 円）"""
    if years <= 0:
        return 0.0
    if annual_rate == 0:
        return principal / years
    r = annual_rate
    n = years
    return principal * r / (1 - (1 + r) ** (-n))

def amortization_schedule(
    principal: float,
    annual_rate: float,
    years: int,
    method: Literal["元利均等", "元金均等"] = "元利均等",
) -> pd.DataFrame:
    """年次返済表（円, 年払い）"""
    rows = []
    balance = principal
    years = max(1, years)
    if method == "元利均等":
        pmt = annuity_payment(principal, annual_rate, years)
        for y in range(1, years + 1):
            interest = balance * annual_rate
            principal_pay = min(pmt - interest, balance)
            payment = interest + principal_pay
            balance = max(0.0, balance - principal_pay)
            rows.append([y, payment, interest, principal_pay, balance])
    else:  # 元金均等
        principal_pay_const = principal / years
        for y in range(1, years + 1):
            interest = balance * annual_rate
            payment = principal_pay_const + interest
            principal_pay = min(principal_pay_const, balance)
            balance = max(0.0, balance - principal_pay)
            rows.append([y, payment, interest, principal_pay, balance])
    return pd.DataFrame(rows, columns=["年", "返済額", "利息", "元金", "期末残債"])

# 建物構造→定率法償却率（概算）
DEPR_RATE_MAP: Dict[str, float] = {
    "木造（住宅・耐用22年）": 0.091,
    "S造（耐用34年）": 0.059,
    "RC造（耐用47年）": 0.046,
}

def estimated_combined_tax_rate(income_yen: float) -> float:
    """
    年収→概算の合計税率（国税の限界税率 + 住民税10%）の近似。
    ※控除等は考慮しない簡易モデル。実務調整は別途対応。
    """
    i = income_yen
    # ざっくり年収ベース：195/330/695/900/1800/4000 万円の区分に対応
    if i <= 1_950_000:   return 0.15   # 5%+10%
    if i <= 3_300_000:   return 0.20   # 10%+10%
    if i <= 6_950_000:   return 0.30   # 20%+10%
    if i <= 9_000_000:   return 0.33   # 23%+10%
    if i <= 18_000_000:  return 0.43   # 33%+10%
    if i <= 40_000_000:  return 0.50   # 40%+10%
    return 0.55                          # 45%+10%（上限想定）

# ================= 画面設定 =================
st.set_page_config(page_title="社宅 vs 購入 シミュレーター（名目累計）", layout="wide")
st.title("🏠 社宅 vs 不動産購入 シミュレーター（ローン・売却・税・仲介｜名目累計）")

with st.expander("使い方 / 前提（クリックで展開）", expanded=False):
    st.markdown(
        """
- **上段＝社宅（賃貸扱い）**、**下段＝購入**で条件を入力。  
- 売却は「指定年後」。※“お子さん25歳”連動は削除済み。  
- 売却時は **仲介手数料（3%+6万+消費税）**、**3,000万円特別控除**（居住用）を考慮。  
- 建物は**定率法**で減価（構造に応じた償却率）。売却価格はデフォで**土地のみ**。  
- 本ツールは**現在価値を使わず**「名目の累計額」で比較します。  
        """
    )

# ===== 売却タイミング =====
st.subheader("⏱ 売却タイミング")
years_until_sale = st.number_input("売却までの年数", min_value=1, max_value=60, value=20, step=1)

st.markdown("---")

# ===== 上段：社宅（賃貸扱い） =====
st.header("🔼 上段：社宅（賃貸扱い）")
cc1, cc2, cc3, cc4 = st.columns(4)
with cc1:
    income_man = st.number_input("年収（万円）", min_value=0, value=2000, step=10)
with cc2:
    company_rent_month_man = st.number_input("会社負担の家賃（月・万円）", min_value=0.0, value=35.0, step=0.1, format="%.1f")
with cc3:
    self_rent_month_man = st.number_input("自己負担の家賃（月・万円）", min_value=0.0, value=3.5, step=0.1, format="%.1f")
with cc4:
    auto_tax_rate = estimated_combined_tax_rate(man_to_yen(income_man))
    st.metric("自動計算された節税率（所得税+住民税）", f"{auto_tax_rate*100:.1f}%")

# 社宅の年間メリット（節税） = (会社負担-自己負担) × 税率
company_rent_year_yen = man_to_yen(company_rent_month_man) * 12
self_rent_year_yen    = man_to_yen(self_rent_month_man) * 12
annual_tax_saving_yen = max(company_rent_year_yen - self_rent_year_yen, 0.0) * auto_tax_rate

# 累計（名目）= 年間メリット × 年数
sum_rent_nominal_yen = annual_tax_saving_yen * years_until_sale

colA, colB = st.columns(2)
with colA:
    st.write("**社宅の年間メリット（節税）**：", man(annual_tax_saving_yen))
with colB:
    st.success(f"■ 社宅の累計メリット（名目）：**{man(sum_rent_nominal_yen, digits=0)}**（{years_until_sale}年）")

# 年次表（参考）
rows_rent = [[y, annual_tax_saving_yen, annual_tax_saving_yen * y] for y in range(1, years_until_sale + 1)]
df_rent = pd.DataFrame(rows_rent, columns=["年", "年メリット（円）", "累計メリット（円）"])
df_rent_disp = df_rent.copy()
df_rent_disp["年メリット（万円）"] = (df_rent["年メリット（円）"] / 10_000).round(1)
df_rent_disp["累計メリット（万円）"] = (df_rent["累計メリット（円）"] / 10_000).round(0)
st.dataframe(df_rent_disp[["年", "年メリット（万円）", "累計メリット（万円）"]], use_container_width=True)

st.markdown("---")

# ===== 下段：購入（売却・税・仲介・ローン込み） =====
st.header("🔽 下段：購入（売却・税・仲介・ローン込み）")

# 物件
pc1, pc2, pc3, pc4 = st.columns(4)
with pc1:
    land_price_man = st.number_input("土地価格（取得時・万円）", min_value=0, value=10_000, step=100)
with pc2:
    land_growth = st.number_input("土地の値上がり率（年・%）", min_value=0.0, max_value=10.0, value=1.0, step=0.1) / 100.0
with pc3:
    building_price_man = st.number_input("建物価格（取得時・万円）", min_value=0, value=5_000, step=100)
with pc4:
    structure = st.selectbox("建物構造（減価償却：定率法）", list(DEPR_RATE_MAP.keys()), index=0)

# ローン
lc1, lc2, lc3, lc4 = st.columns(4)
with lc1:
    loan_principal_man = st.number_input("借入金額（ローン元本・万円）", min_value=0, value=15_000, step=100)
with lc2:
    loan_rate = st.number_input("金利（年・%）", min_value=0.0, max_value=10.0, value=1.0, step=0.05) / 100.0
with lc3:
    loan_years = st.number_input("返済期間（年）", min_value=1, max_value=60, value=35, step=1)
with lc4:
    repay_method = st.selectbox("返済方式", ["元利均等", "元金均等"])

# 売却・税
sc1, sc2, sc3, sc4 = st.columns(4)
with sc1:
    treat_building_as_zero = st.checkbox("売却価格は土地のみ（建物市場価値0と仮定）", value=True)
with sc2:
    apply_30m_deduction = st.checkbox("3,000万円特別控除（居住用）を適用", value=True)
with sc3:
    tax_rate_cg = st.number_input("譲渡所得税率（長期・%）", min_value=0.0, max_value=55.0, value=20.315, step=0.1) / 100.0
with sc4:
    commission_tax_rate = st.number_input("消費税率（仲介手数料に適用・%）", min_value=0.0, max_value=20.0, value=10.0, step=0.5) / 100.0

# 円に変換
land_price = man_to_yen(land_price_man)
building_price = man_to_yen(building_price_man)
loan_principal = man_to_yen(loan_principal_man)

# 計算
depr_rate = DEPR_RATE_MAP[structure]

# 将来の土地価格（名目）
land_future = land_price * ((1 + land_growth) ** years_until_sale)
land_appreciation = land_future - land_price  # 値上がり額の見える化

# 建物簿価（参考・税務用）
building_book = building_price * ((1 - depr_rate) ** years_until_sale)

# 返済表（年払い）
am_df = amortization_schedule(loan_principal, loan_rate, loan_years, method=repay_method)
elapsed = min(years_until_sale, loan_years)
loan_balance = float(am_df.loc[am_df["年"] == elapsed, "期末残債"].values[0])

# 売却価格（デフォは土地のみ）
sale_price = land_future if treat_building_as_zero else (land_future + building_book)

# 仲介手数料（3% + 6万円 + 消費税）
commission = (sale_price * 0.03 + 60_000) * (1 + commission_tax_rate)

# 取得費（売却対象に対応する原価：土地のみ or 土地+建物）
acquisition_cost = land_price if treat_building_as_zero else (land_price + building_price)

# 譲渡所得（控除前）
capital_gain_base = sale_price - commission - acquisition_cost
deduction = 30_000_000 if apply_30m_deduction else 0  # 3,000万円控除
taxable_gain = max(0.0, capital_gain_base - deduction)
capital_gains_tax = taxable_gain * tax_rate_cg

# 最終手残り（名目）
net_proceeds = sale_price - commission - capital_gains_tax - loan_balance

# ---- 表示 ----
st.subheader("計算サマリー（購入）")
col1, col2, col3 = st.columns(3)
with col1:
    st.write("**土地（将来価格）**", man(land_future, 0))
    st.write("**土地の値上がり額**", man(land_appreciation, 0))
    st.write("**建物（簿価・参考）**", man(building_book, 0))
with col2:
    st.write("**売却価格**", man(sale_price, 0))
    st.write("**仲介手数料**", man(commission, 0))
    st.write("**売却時ローン残債**", man(loan_balance, 0))
with col3:
    st.write("**譲渡所得（控除前）**", man(max(0.0, capital_gain_base), 0))
    st.write("**課税譲渡所得**", man(taxable_gain, 0))
    st.write("**譲渡所得税**", man(capital_gains_tax, 0))

st.success(f"■ 売却手残り（名目）：**{man(net_proceeds, 0)}**")

# 比較（名目のみ）
st.markdown("---")
st.subheader("📊 最終比較（社宅 累計 vs 購入 手残り）")
compare_df = pd.DataFrame({
    "区分": ["社宅（累計メリット）", "購入（売却手残り）", "差額（購入−社宅）"],
    "金額（円）": [sum_rent_nominal_yen, net_proceeds, net_proceeds - sum_rent_nominal_yen]
})
disp_df = compare_df.copy()
disp_df["金額（万円）"] = (disp_df["金額（円）"] / 10_000).round(0)
st.dataframe(disp_df[["区分", "金額（万円）"]], use_container_width=True)

diff = net_proceeds - sum_rent_nominal_yen
if diff >= 0:
    st.success(f"■ 名目ベースの優位：**購入が {man(diff, 0)} 有利**")
else:
    st.warning(f"■ 名目ベースの優位：**社宅が {man(abs(diff), 0)} 有利**")

# 住宅ローン返済表（年次・万円表示）
st.markdown("---")
st.subheader("📄 住宅ローン返済表（年次・万円）")
disp_am = am_df.copy()
for col in ["返済額", "利息", "元金", "期末残債"]:
    disp_am[col] = (disp_am[col] / 10_000).round(1)
st.dataframe(disp_am, use_container_width=True)

# ================= CSV / PDF 出力 =================
st.markdown("---")
st.subheader("⬇️ 出力（CSV / PDF）")

# CSV
csv = compare_df.to_csv(index=False).encode("utf-8-sig")
st.download_button("比較結果CSVをダウンロード", data=csv, file_name="compare_result.csv", mime="text/csv")

# PDF（日本語フォント埋め込みで文字化け解消）
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # ★ 日本語フォント（同梱してください）
    FONT_PATH = "fonts/NotoSansJP-Regular.ttf"
    FONT_NAME = "NotoSansJP"
    pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))

    def wrap_lines(c, text, x_mm, y_mm, max_width_mm, font_name, font_size, leading_mm=6):
        """簡易折返し。max_width_mmを超える前に改行。"""
        max_w = max_width_mm * mm
        c.setFont(font_name, font_size)
        lines = []
        buf = ""
        for ch in text:
            if ch == "\n":
                lines.append(buf); buf = ""; continue
            trial = buf + ch
            if c.stringWidth(trial, font_name, font_size) <= max_w:
                buf = trial
            else:
                lines.append(buf); buf = ch
        if buf:
            lines.append(buf)
        for line in lines:
            c.drawString(x_mm*mm, y_mm*mm, line)
            y_mm -= leading_mm
        return y_mm

    def export_pdf(path: str):
        c = canvas.Canvas(path, pagesize=A4)
        W, H = A4
        x = 20  # mm
        y = (H/mm) - 20

        c.setFont(FONT_NAME, 14)
        c.drawString(x*mm, y*mm, "社宅 vs 不動産購入 シミュレーター 要約（名目累計）")
        y -= 10

        c.setFont(FONT_NAME, 10)
        body = [
            f"売却までの年数: {years_until_sale} 年",
            f"[社宅] 年間メリット: {man(annual_tax_saving_yen)} / 累計: {man(sum_rent_nominal_yen)}",
            f"[購入] 土地将来価格: {man(land_future, 0)} / 土地の値上がり額: {man(land_appreciation, 0)}",
            f"      建物簿価(参考): {man(building_book, 0)} / 売却価格: {man(sale_price, 0)}",
            f"      仲介手数料: {man(commission, 0)} / 売却時ローン残債: {man(loan_balance, 0)}",
            f"      譲渡所得(控除前): {man(max(0.0, capital_gain_base), 0)} / 課税譲渡所得: {man(taxable_gain, 0)} / 譲渡税: {man(capital_gains_tax, 0)}",
            f"最終手残り（名目）: {man(net_proceeds, 0)}",
            f"比較（名目）: {'購入が' if (diff) >= 0 else '社宅が'} {man(abs(diff), 0)} 有利",
        ]
        for line in body:
            y = wrap_lines(c, line, x, y, max_width_mm=170, font_name=FONT_NAME, font_size=10, leading_mm=6)

        c.showPage()
        c.save()

    if st.button("PDF要約を生成"):
        path = "summary.pdf"
        export_pdf(path)
        with open(path, "rb") as f:
            st.download_button("summary.pdf をダウンロード", data=f, file_name="summary.pdf", mime="application/pdf")
except Exception as e:
    st.error("PDF生成でエラー。fonts/NotoSansJP-Regular.ttf が配置されているか確認してください。")