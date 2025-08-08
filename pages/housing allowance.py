# pages/housing_allowance.py
import math
from typing import Literal, Dict, List
import pandas as pd
import streamlit as st

# ================= ユーティリティ =================
def man_to_yen(v_man: float) -> float:
    return float(v_man) * 10_000.0

def yen_to_man(v_yen: float) -> float:
    return float(v_yen) / 10_000.0

def man(n_yen: float, digits: int = 1) -> str:
    return f"{yen_to_man(n_yen):,.{digits}f}万円"

def annuity_payment_annual(principal: float, annual_rate: float, years: int) -> float:
    """元利均等（年払い, 円）"""
    if years <= 0:
        return 0.0
    if annual_rate == 0:
        return principal / years
    r = annual_rate
    n = years
    return principal * r / (1 - (1 + r) ** (-n))

def annuity_payment_monthly(principal: float, annual_rate: float, years: int) -> float:
    """元利均等（**月払い**, 円）"""
    months = years * 12
    if months <= 0:
        return 0.0
    r_m = annual_rate / 12.0
    if r_m == 0:
        return principal / months
    return principal * r_m / (1 - (1 + r_m) ** (-months))

def amortization_schedule_annual(
    principal: float,
    annual_rate: float,
    years: int,
    method: Literal["元利均等", "元金均等"] = "元利均等",
) -> pd.DataFrame:
    """年次返済表（円, 年払い）— 資産累計（元金累計）つき"""
    rows = []
    balance = principal
    years = max(1, years)
    cumulative_principal = 0.0

    if method == "元利均等":
        pmt = annuity_payment_annual(principal, annual_rate, years)
        for y in range(1, years + 1):
            interest = balance * annual_rate
            principal_pay = min(pmt - interest, balance)
            payment = interest + principal_pay
            balance = max(0.0, balance - principal_pay)
            cumulative_principal += principal_pay
            rows.append([y, payment, interest, principal_pay, cumulative_principal, balance])
    else:  # 元金均等
        principal_pay_const = principal / years
        for y in range(1, years + 1):
            interest = balance * annual_rate
            principal_pay = min(principal_pay_const, balance)
            payment = principal_pay + interest
            balance = max(0.0, balance - principal_pay)
            cumulative_principal += principal_pay
            rows.append([y, payment, interest, principal_pay, cumulative_principal, balance])

    return pd.DataFrame(rows, columns=["年", "返済額", "利息", "元金", "資産累計", "期末残債"])

def remaining_balance_monthly(principal: float, annual_rate: float, years_total: int, years_elapsed: int,
                              method: Literal["元利均等", "元金均等"]) -> float:
    """**月払い**での厳密な残債（経過年数×12ヶ月後）"""
    months_total = years_total * 12
    months_elapsed = min(years_elapsed * 12, months_total)
    r_m = annual_rate / 12.0
    bal = principal

    if method == "元利均等":
        pmt_m = annuity_payment_monthly(principal, annual_rate, years_total)
        for _ in range(months_elapsed):
            interest = bal * r_m
            principal_pay = min(pmt_m - interest, bal)
            bal = max(0.0, bal - principal_pay)
        return bal
    else:  # 元金均等（毎月一定元金返済）
        principal_pm = principal / months_total
        for _ in range(months_elapsed):
            # 利息は支払っているが、残債は元金分だけ減る
            bal = max(0.0, bal - principal_pm)
        return bal

# ============ 減価償却（定額法） ============
LIFE_MAP: Dict[str, int] = {
    "木造（住宅・耐用22年）": 22,
    "S造（耐用34年）":        34,
    "RC造（耐用47年）":       47,
}
def straight_rate(structure: str) -> float:
    return 1.0 / LIFE_MAP[structure]

def building_book_value_straight(building_price: float, structure: str, years_elapsed: int) -> float:
    """定額法：簿価 = 取得価額 × max(0, 1 - 償却率×年数)"""
    rate = straight_rate(structure)
    life = LIFE_MAP[structure]
    factor = max(0.0, 1.0 - rate * min(years_elapsed, life))
    return building_price * factor

def remaining_book_straight(add_cost_yen: float, life_years: int, years_elapsed_since_add: int) -> float:
    """リフォーム等の資本的支出を定額法で償却した売却時点の残簿価"""
    used = min(years_elapsed_since_add, life_years)
    factor = max(0.0, 1.0 - used / life_years)
    return add_cost_yen * factor

# ============ 税率（社宅の節税率の近似） ============
def estimated_combined_tax_rate(income_yen: float) -> float:
    """
    年収→概算の合計税率（国税の限界税率 + 住民税10%）の近似。
    ※控除等は未反映の簡易モデル。
    """
    i = income_yen
    if i <= 1_950_000:   return 0.15   # 5%+10%
    if i <= 3_300_000:   return 0.20   # 10%+10%
    if i <= 6_950_000:   return 0.30   # 20%+10%
    if i <= 9_000_000:   return 0.33   # 23%+10%
    if i <= 18_000_000:  return 0.43   # 33%+10%
    if i <= 40_000_000:  return 0.50   # 40%+10%
    return 0.55                          # 45%+10%

# ================= 画面設定 =================
st.set_page_config(page_title="社宅 vs 購入 シミュレーター（名目累計｜定額法＋リフォーム）", layout="wide")
st.title("🏠 社宅 vs 不動産購入 シミュレーター（ローン・売却・税・仲介｜名目累計｜定額法）")

with st.expander("使い方 / 前提（クリックで展開）", expanded=False):
    st.markdown(
        """
- **上段＝社宅（賃貸扱い）**、**下段＝購入**で条件を入力。  
- 売却は「指定年後」。  
- 売却時は **仲介手数料（3%+6万+消費税）**、**3,000万円特別控除**（居住用）を考慮。  
- 建物は**定額法**で減価（木造22年 / S造34年 / RC造47年）。  
- 売却価格 = **土地の将来価格 + 建物の簿価（定額法後）**。  
- リフォーム（資本的支出）は建物原価に追加し、**定額法**で償却（最大3件）。  
- 本ツールは**現在価値を使わず**「名目累計」で比較します。  
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

# 社宅メリット
company_rent_year_yen = man_to_yen(company_rent_month_man) * 12
self_rent_year_yen    = man_to_yen(self_rent_month_man) * 12
annual_tax_saving_yen = max(company_rent_year_yen - self_rent_year_yen, 0.0) * auto_tax_rate
sum_rent_nominal_yen  = annual_tax_saving_yen * years_until_sale

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
    structure = st.selectbox("建物構造（減価償却：定額法）", list(LIFE_MAP.keys()), index=0)

# リフォーム（資本的支出）
st.markdown("### 🛠 リフォーム（資本的支出・定額法で償却）")
ren_enable = st.checkbox("リフォームを計上する", value=False)
ren_rows: List[dict] = []
if ren_enable:
    ren_count = st.number_input("リフォーム件数（最大3）", min_value=1, max_value=3, value=1, step=1)
    st.caption("※ 実施年は『取得後○年』。償却は定額法。『残存年数償却』は残り耐用年数で均等償却。")
    for i in range(int(ren_count)):
        c1, c2, c3 = st.columns(3)
        with c1:
            ry = st.number_input(f"#{i+1} 実施年（取得後○年）", min_value=1, max_value=years_until_sale, value=min(10, years_until_sale), step=1, key=f"ren_y_{i}")
        with c2:
            rc_man = st.number_input(f"#{i+1} 費用（万円）", min_value=0, value=500, step=10, key=f"ren_c_{i}")
        with c3:
            life_mode = st.selectbox(
                f"#{i+1} 償却年数の扱い",
                ["法定年数で新規スタート", "残存年数で償却（残り耐用年数）"],
                index=0, key=f"ren_m_{i}"
            )
        ren_rows.append({"year": int(ry), "cost_yen": man_to_yen(rc_man), "mode": life_mode})

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
    apply_30m_deduction = st.checkbox("3,000万円特別控除（居住用）を適用", value=True)
with sc2:
    tax_rate_cg = st.number_input("譲渡所得税率（長期・%）", min_value=0.0, max_value=55.0, value=20.315, step=0.1) / 100.0
with sc3:
    commission_tax_rate = st.number_input("消費税率（仲介手数料に適用・%）", min_value=0.0, max_value=20.0, value=10.0, step=0.5) / 100.0
with sc4:
    st.write("")  # 余白

# 円へ変換
land_price     = man_to_yen(land_price_man)
building_price = man_to_yen(building_price_man)
loan_principal = man_to_yen(loan_principal_man)

# 減価償却（定額法）
building_book = building_book_value_straight(building_price, structure, years_until_sale)

# リフォーム残簿価の合算
ren_book_total = 0.0
ren_total_spend = 0.0
if ren_enable and ren_rows:
    base_life = LIFE_MAP[structure]
    for r in ren_rows:
        years_since = max(0, years_until_sale - r["year"])
        if r["mode"] == "法定年数で新規スタート":
            life_used = base_life
        else:  # 残存年数で償却
            life_used = max(1, base_life - r["year"])
        ren_book = remaining_book_straight(r["cost_yen"], life_used, years_since)
        ren_book_total += ren_book
        ren_total_spend += r["cost_yen"]

# 建物総簿価（＝既存建物簿価＋リフォーム残簿価）
building_book_total = building_book + ren_book_total

# 将来の土地価格（名目）
land_future = land_price * ((1 + land_growth) ** years_until_sale)
land_appreciation = land_future - land_price

# 返済：表示は年次表、残債は**月払いで厳密**に算出
am_df = amortization_schedule_annual(loan_principal, loan_rate, loan_years, method=repay_method)
loan_balance = remaining_balance_monthly(loan_principal, loan_rate, loan_years, years_until_sale, repay_method)

# 月々返済金額（表示用）
if repay_method == "元利均等":
    monthly_payment = annuity_payment_monthly(loan_principal, loan_rate, loan_years)
    monthly_payment_label = f"{man(monthly_payment, 1)} / 月"
else:
    r_m = loan_rate / 12.0
    principal_pm = loan_principal / (loan_years * 12)
    first_month = principal_pm + loan_principal * r_m
    monthly_payment = first_month
    monthly_payment_label = f"{man(first_month, 1)} / 月（初月目安）"

# 売却価格（＝土地+建物簿価）
sale_price = land_future + building_book_total

# 仲介手数料（3% + 6万円 + 消費税）
commission = (sale_price * 0.03 + 60_000) * (1 + commission_tax_rate)

# 取得費（＝土地 + 建物簿価）
acquisition_cost = land_price + building_book_total

# 譲渡所得
capital_gain_base = sale_price - commission - acquisition_cost
deduction = 30_000_000 if apply_30m_deduction else 0
taxable_gain = max(0.0, capital_gain_base - deduction)
capital_gains_tax = taxable_gain * tax_rate_cg

# 最終手残り（名目）
net_proceeds = sale_price - commission - capital_gains_tax - loan_balance

# 累計資産額（= 返済元金の累計 ＝ ローン元本 − 売却時残債）
cumulative_equity = loan_principal - loan_balance

# ---- 表示（ご指定の順番＋追記事項の位置）----
st.subheader("計算サマリー（購入）")
col1, col2, col3 = st.columns(3)

with col1:
    st.write("**土地（将来価格）**", man(land_future, 0))
    st.write("**土地の値上がり額**", man(land_appreciation, 0))
    st.write("**建物（簿価＝減価償却後の価格）**", man(building_book_total, 0))
    if ren_enable:
        st.caption(
            f"内訳：既存 {man(building_book,0)} ＋ リフォーム残簿価 {man(ren_book_total,0)}（投資累計 {man(ren_total_spend,0)}）"
        )
    st.caption(f"月々返済金額：{monthly_payment_label}")  # ← この位置に月々返済

with col2:
    st.write("**売却価格（＝土地+建物簿価）**", man(sale_price, 0))
    st.write("**仲介手数料**", man(commission, 0))
    st.write("**売却時ローン残債**", man(loan_balance, 0))
    st.caption(f"累計資産額（元金累計）：{man(cumulative_equity, 0)}")  # ← この位置に累計資産額

with col3:
    st.write("**取得費（＝土地+建物簿価）**", man(acquisition_cost, 0))
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
disp_am = amortization_schedule_annual(loan_principal, loan_rate, loan_years, method=repay_method)
for col in ["返済額", "利息", "元金", "資産累計", "期末残債"]:
    disp_am[col] = (disp_am[col] / 10_000).round(1)
st.dataframe(disp_am[["年", "利息", "元金", "資産累計", "期末残債"]], use_container_width=True)