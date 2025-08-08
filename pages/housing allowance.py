import math
from dataclasses import dataclass
from typing import Literal, Dict, Tuple

import numpy as np
import pandas as pd
import streamlit as st

# ========== ユーティリティ ==========
def yen(n: float) -> str:
    return f"¥{n:,.0f}"

def pv(value: float, rate: float, years: int) -> float:
    return value / ((1 + rate) ** years) if years > 0 else value

def annuity_payment(principal: float, annual_rate: float, years: int) -> float:
    """元利均等（年払い）"""
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
    """年次の返済表（年払い）。"""
    rows = []
    balance = principal
    if method == "元利均等":
        pmt = annuity_payment(principal, annual_rate, years)
        for y in range(1, years + 1):
            interest = balance * annual_rate
            principal_pay = pmt - interest
            balance = max(0.0, balance - principal_pay)
            rows.append([y, pmt, interest, principal_pay, balance])
    else:  # 元金均等
        principal_pay_const = principal / years
        for y in range(1, years + 1):
            interest = balance * annual_rate
            pmt = principal_pay_const + interest
            balance = max(0.0, balance - principal_pay_const)
            rows.append([y, pmt, interest, principal_pay_const, balance])
    df = pd.DataFrame(rows, columns=["年", "返済額", "利息", "元金", "期末残債"])
    return df

# 建物構造→定率法償却率（概算）
DEPR_RATE_MAP: Dict[str, float] = {
    "木造（住宅・耐用22年）": 0.091,
    "S造（耐用34年）": 0.059,
    "RC造（耐用47年）": 0.046,
}

# ========== Streamlit UI ==========
st.set_page_config(page_title="社宅 vs 購入 シミュレーター（手残り&現在価値）", layout="wide")
st.title("🏠 社宅 vs 不動産購入 シミュレーター（ローン・売却・税・インフレ込）")

with st.expander("使い方 / 前提（クリックで展開）", expanded=False):
    st.markdown(
        """
- **上段＝社宅（賃貸扱い）**、**下段＝購入**で条件を入力。  
- 売却は「指定年後」または「お子さんが25歳になった年」に連動できます。  
- 売却時は **仲介手数料（3%+6万+消費税）**、**3,000万円特別控除**（居住用）を考慮。  
- 建物は**定率法**で減価（構造に応じた償却率）。市場価値は0仮定（※必要なら変更可）。  
- **結果**は「名目」と「現在価値（インフレ割引）」で比較。  
- 右下にCSV/PDF出力もあります。
        """
    )

# ===== 共通（シナリオ軸） =====
st.subheader("⏱ 売却タイミング・インフレ")
c1, c2, c3, c4 = st.columns(4)
with c1:
    timing_mode = st.selectbox("売却タイミングの決め方", ["年数指定", "お子さんの年齢連動（25歳時）"])
with c2:
    if timing_mode == "年数指定":
        years_until_sale = st.number_input("売却までの年数", min_value=1, max_value=60, value=20, step=1)
    else:
        child_age_now = st.number_input("お子さんの現在年齢", min_value=0, max_value=60, value=5, step=1)
        years_until_sale = max(1, 25 - child_age_now)
        st.info(f"→ 自動計算：売却まで **{years_until_sale} 年**")
with c3:
    inflation_rate = st.number_input("インフレ率（年）", min_value=0.0, max_value=5.0, value=1.0, step=0.1) / 100.0
with c4:
    disp_unit_man = st.checkbox("表示を万円単位にする", value=True)

unit = 10_000 if disp_unit_man else 1

st.markdown("---")

# ===== 上段：社宅 =====
st.header("🔼 上段：社宅（賃貸扱い）")
cc1, cc2, cc3, cc4 = st.columns(4)
with cc1:
    income = st.number_input("年収（概算・税率算定の参考）", min_value=0, value=20_000_000, step=100_000)
with cc2:
    company_rent_month = st.number_input("会社負担の家賃（月）", min_value=0, value=350_000, step=10_000)
with cc3:
    self_rent_month = st.number_input("自己負担の家賃（月）", min_value=0, value=35_000, step=5_000)
with cc4:
    tax_rate_manual = st.number_input("節税率（所得税+住民税 合計%）", min_value=0.0, max_value=60.0, value=55.0, step=1.0) / 100.0

company_rent_year = company_rent_month * 12
self_rent_year = self_rent_month * 12
annual_tax_saving = max(company_rent_year - self_rent_year, 0) * tax_rate_manual

# 年ごとのCF & 現在価値
rows_rent = []
pv_sum_rent = 0.0
for y in range(1, years_until_sale + 1):
    cf = annual_tax_saving
    cf_pv = pv(cf, inflation_rate, y)
    pv_sum_rent += cf_pv
    rows_rent.append([y, cf, cf_pv])

df_rent = pd.DataFrame(rows_rent, columns=["年", "社宅CF（年）", "社宅CF（年・現在価値）"])
sum_rent_nominal = df_rent["社宅CF（年）"].sum()
sum_rent_pv = df_rent["社宅CF（年・現在価値）"].sum()

st.write("**社宅の年間メリット（節税）＝**", yen(annual_tax_saving))
st.dataframe(df_rent.assign(**{
    "社宅CF（年）": (df_rent["社宅CF（年）"]/unit).round(1),
    "社宅CF（年・現在価値）": (df_rent["社宅CF（年・現在価値）"]/unit).round(1),
}))

st.success(
    f"■ 社宅の累計メリット：名目 **{yen(sum_rent_nominal)}** / 現在価値 **{yen(sum_rent_pv)}**"
)

st.markdown("---")

# ===== 下段：購入 =====
st.header("🔽 下段：購入（売却・税・仲介・ローン込み）")

# 物件
pc1, pc2, pc3, pc4 = st.columns(4)
with pc1:
    land_price = st.number_input("土地価格（取得時）", min_value=0, value=100_000_000, step=1_000_000)
with pc2:
    land_growth = st.number_input("土地の値上がり率（年）%", min_value=0.0, max_value=10.0, value=1.0, step=0.1) / 100.0
with pc3:
    building_price = st.number_input("建物価格（取得時）", min_value=0, value=50_000_000, step=1_000_000)
with pc4:
    structure = st.selectbox("建物構造（減価償却：定率法）", list(DEPR_RATE_MAP.keys()), index=0)

# ローン
lc1, lc2, lc3, lc4 = st.columns(4)
with lc1:
    loan_principal = st.number_input("借入金額（ローン元本）", min_value=0, value=150_000_000, step=1_000_000)
with lc2:
    loan_rate = st.number_input("金利（年）%", min_value=0.0, max_value=10.0, value=1.0, step=0.05) / 100.0
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
    long_term_tax = 0.20315  # 20.315%
    tax_rate_cg = st.number_input("譲渡所得税率（長期）%", min_value=0.0, max_value=55.0, value=20.315, step=0.1) / 100.0
with sc4:
    commission_tax_rate = st.number_input("消費税率（仲介手数料に適用）%", min_value=0.0, max_value=20.0, value=10.0, step=0.5) / 100.0

# 計算
depr_rate = DEPR_RATE_MAP[structure]

# 20年後など：土地価格
land_future = land_price * ((1 + land_growth) ** years_until_sale)

# 建物簿価（定率法）
building_book = building_price * ((1 - depr_rate) ** years_until_sale)

# 返済表（年払い）
am_df = amortization_schedule(loan_principal, loan_rate, loan_years, method=repay_method)
elapsed = min(years_until_sale, loan_years)
loan_balance = float(am_df.loc[am_df["年"] == elapsed, "期末残債"].values[0])

# 売却価格
sale_price = land_future if treat_building_as_zero else (land_future + building_book)

# 仲介手数料（3% + 6万円 + 消費税）
commission = (sale_price * 0.03 + 60_000) * (1 + commission_tax_rate)

# 譲渡所得（※売却経費は取得費控除前にマイナス可能）
# 取得費は「売却対象に対応する原価」を採用：デフォは土地のみ売却→土地原価のみ
acquisition_cost = land_price if treat_building_as_zero else (land_price + building_price)
capital_gain_base = sale_price - commission - acquisition_cost

# 3,000万円特別控除
deduction = 30_000_000 if apply_30m_deduction else 0
taxable_gain = max(0.0, capital_gain_base - deduction)
capital_gains_tax = taxable_gain * tax_rate_cg

# 最終手残り（名目）：売却金 - 仲介 - 譲渡税 - 残債
net_proceeds = sale_price - commission - capital_gains_tax - loan_balance
net_proceeds_pv = pv(net_proceeds, inflation_rate, years_until_sale)

# 表示
st.subheader("計算サマリー（購入）")
sum_cols = st.columns(2)
with sum_cols[0]:
    st.write("**土地（将来価格）**", yen(land_future))
    st.write("**建物（簿価・参考）**", yen(building_book))
    st.write("**売却価格**", yen(sale_price))
    st.write("**仲介手数料**", yen(commission))
with sum_cols[1]:
    st.write("**譲渡所得（控除前）**", yen(max(0.0, capital_gain_base)))
    st.write("**課税譲渡所得**", yen(taxable_gain))
    st.write("**譲渡所得税**", yen(capital_gains_tax))
    st.write("**売却時ローン残債**", yen(loan_balance))

st.success(
    f"■ 売却手残り（名目）：**{yen(net_proceeds)}** / 現在価値：**{yen(net_proceeds_pv)}**  "
    f"(割引率＝インフレ {inflation_rate*100:.1f}%・期間 {years_until_sale}年)"
)

# 比較
st.markdown("---")
st.subheader("📊 最終比較（社宅 vs 購入）")

compare_df = pd.DataFrame({
    "区分": ["社宅（累計）", "社宅（累計・現在価値）", "購入（売却手残り）", "購入（売却手残り・現在価値）"],
    "金額": [sum_rent_nominal, sum_rent_pv, net_proceeds, net_proceeds_pv]
})
disp_df = compare_df.copy()
disp_df["金額"] = (disp_df["金額"] / unit).round(1)
st.dataframe(disp_df)

diff_nominal = net_proceeds - sum_rent_nominal
diff_pv = net_proceeds_pv - sum_rent_pv

if diff_pv >= 0:
    st.success(f"■ 現在価値ベースの優位：**購入が {yen(abs(diff_pv))} 有利**")
else:
    st.warning(f"■ 現在価値ベースの優位：**社宅が {yen(abs(diff_pv))} 有利**")

# 返済表の抜粋
st.markdown("---")
st.subheader("📄 住宅ローン返済表（年次）")
disp_am = am_df.copy()
for col in ["返済額", "利息", "元金", "期末残債"]:
    disp_am[col] = (disp_am[col] / unit).round(1)
st.dataframe(disp_am)

# ===== ダウンロード（CSV / PDF） =====
st.markdown("---")
st.subheader("⬇️ 出力")

# CSV
csv = compare_df.to_csv(index=False).encode("utf-8-sig")
st.download_button("比較結果CSVをダウンロード", data=csv, file_name="compare_result.csv", mime="text/csv")

# PDF（簡易要約）
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    def export_pdf(path: str):
        c = canvas.Canvas(path, pagesize=A4)
        w, h = A4
        y = h - 20*mm
        c.setFont("Helvetica-Bold", 14)
        c.drawString(20*mm, y, "社宅 vs 購入 シミュレーター 要約")
        y -= 10*mm

        c.setFont("Helvetica", 10)
        lines = [
            f"売却までの年数: {years_until_sale} 年 / インフレ: {inflation_rate*100:.1f}%",
            f"[社宅] 年間メリット: {yen(annual_tax_saving)} / 累計: {yen(sum_rent_nominal)} / 現在価値: {yen(sum_rent_pv)}",
            f"[購入] 土地将来価格: {yen(land_future)} / 建物簿価(参考): {yen(building_book)}",
            f"      売却価格: {yen(sale_price)} / 仲介: {yen(commission)} / 譲渡税: {yen(capital_gains_tax)}",
            f"      残債: {yen(loan_balance)} / 手残り（名目）: {yen(net_proceeds)} / （現在価値）: {yen(net_proceeds_pv)}",
            f"比較（現在価値）: {'購入が' if diff_pv>=0 else '社宅が'} {yen(abs(diff_pv))} 有利",
        ]
        for line in lines:
            c.drawString(20*mm, y, line)
            y -= 7*mm

        c.showPage()
        c.save()

    if st.button("PDF要約を生成"):
        path = "summary.pdf"
        export_pdf(path)
        with open(path, "rb") as f:
            st.download_button("summary.pdf をダウンロード", data=f, file_name="summary.pdf", mime="application/pdf")
except Exception as e:
    st.info("PDF出力には reportlab が必要です（requirements.txt に含めています）。")