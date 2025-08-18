# pages/housing_allowance.py
from typing import Literal, Dict, List
import pandas as pd
import streamlit as st

# ========= ユーティリティ =========
def man_to_yen(v_man: float) -> float:
    return float(v_man) * 10_000.0

def yen_to_man(v_yen: float) -> float:
    return float(v_yen) / 10_000.0

def man(n_yen: float, digits: int = 1) -> str:
    return f"{yen_to_man(n_yen):,.{digits}f}万円"

def annuity_payment_monthly(principal: float, annual_rate: float, years: int) -> float:
    m = years * 12
    if m <= 0: return 0.0
    r = annual_rate / 12.0
    if r == 0: return principal / m
    return principal * r / (1 - (1 + r) ** (-m))

def amortization_schedule_annual(
    principal: float,
    annual_rate: float,
    years: int,
    method: Literal["元利均等", "元金均等"] = "元利均等",
) -> pd.DataFrame:
    rows = []
    bal = principal
    years = max(1, years)
    cum_pr = 0.0
    if method == "元利均等":
        # 年払いの近似（表示用）。残債は月ベースで別計算。
        if annual_rate == 0:
            pmt = principal / years
        else:
            r, n = annual_rate, years
            pmt = principal * r / (1 - (1 + r) ** (-n))
        for y in range(1, years + 1):
            interest = bal * annual_rate
            pr = min(pmt - interest, bal)
            pay = pr + interest
            bal = max(0.0, bal - pr)
            cum_pr += pr
            rows.append([y, pay, interest, pr, cum_pr, bal])
    else:
        pr_const = principal / years
        for y in range(1, years + 1):
            interest = bal * annual_rate
            pr = min(pr_const, bal)
            pay = pr + interest
            bal = max(0.0, bal - pr)
            cum_pr += pr
            rows.append([y, pay, interest, pr, cum_pr, bal])
    return pd.DataFrame(rows, columns=["年", "返済額", "利息", "元金", "資産累計", "期末残債"])

def remaining_balance_monthly(principal: float, annual_rate: float, years_total: int, years_elapsed: int,
                              method: Literal["元利均等", "元金均等"]) -> float:
    months_total = years_total * 12
    months_elapsed = min(years_elapsed * 12, months_total)
    r = annual_rate / 12.0
    bal = principal
    if method == "元利均等":
        pmt = annuity_payment_monthly(principal, annual_rate, years_total)
        for _ in range(months_elapsed):
            interest = bal * r
            pr = min(pmt - interest, bal)
            bal = max(0.0, bal - pr)
        return bal
    else:
        pr_m = principal / months_total
        for _ in range(months_elapsed):
            bal = max(0.0, bal - pr_m)
        return bal

# ========= 減価償却（定額法） =========
LIFE_MAP: Dict[str, int] = {
    "木造（住宅・耐用22年）": 22,
    "S造（耐用34年）":        34,
    "RC造（耐用47年）":       47,
}

def building_book_value_straight(building_price: float, structure: str,
                                 years_elapsed: int, built_age_at_purchase: int = 0) -> float:
    life_total = LIFE_MAP[structure]
    life_rem = max(1, life_total - max(0, built_age_at_purchase))  # 残存耐用年数（簡易）
    used = min(years_elapsed, life_rem)
    factor = max(0.0, 1.0 - used / life_rem)
    return building_price * factor

def remaining_book_straight(add_cost_yen: float, life_years: int, years_elapsed_since_add: int) -> float:
    used = min(years_elapsed_since_add, life_years)
    factor = max(0.0, 1.0 - used / life_years)
    return add_cost_yen * factor

# ========= 社宅の概算税率（参考） =========
def estimated_combined_tax_rate(income_yen: float) -> float:
    i = income_yen
    if i <= 1_950_000:   return 0.15
    if i <= 3_300_000:   return 0.20
    if i <= 6_950_000:   return 0.30
    if i <= 9_000_000:   return 0.33
    if i <= 18_000_000:  return 0.43
    if i <= 40_000_000:  return 0.50
    return 0.55

# ========= 画面 =========
st.set_page_config(page_title="社宅 vs 購入", layout="wide")
st.title("🏠 社宅 vs 不動産購入 シミュレーター")

with st.expander("使い方 / 前提", expanded=False):
    st.markdown(
        """
- 建物は**定額法**（木造22年 / S造34年 / RC造47年）。**中古は購入時築年数で残存年数償却**。  
- リフォームは**資本的支出**として原価へ追加し定額法で償却。  
- **プレミアム率（%）**を各リフォームに設定すると、売却時の**市場価値**に上乗せ（取得費には含めません）。  
        """
    )

# ===== 売却タイミング =====
st.subheader("⏱ 売却タイミング")
years_until_sale = st.number_input("売却までの年数", min_value=1, max_value=100, value=20, step=1)

st.markdown("---")

# ===== 上段：社宅 =====
st.header("🔼 上段：社宅（賃貸扱い）")
c1, c2, c3, c4 = st.columns(4)
with c1:
    income_man = st.number_input("年収（万円）", min_value=0, value=2000, step=10)
with c2:
    company_rent_month_man = st.number_input("会社負担の家賃（月・万円）", min_value=0.0, value=35.0, step=0.1, format="%.1f")
with c3:
    self_rent_month_man = st.number_input("自己負担の家賃（月・万円）", min_value=0.0, value=3.5, step=0.1, format="%.1f")
with c4:
    tax_rate = estimated_combined_tax_rate(man_to_yen(income_man))
    st.metric("自動推定・節税率（所得税+住民税）", f"{tax_rate*100:.1f}%")

company_rent_year = man_to_yen(company_rent_month_man) * 12
self_rent_year    = man_to_yen(self_rent_month_man)    * 12
annual_saving     = max(company_rent_year - self_rent_year, 0.0) * tax_rate
sum_rent_nominal  = annual_saving * years_until_sale

colA, colB = st.columns(2)
with colA:
    st.write("**社宅の年間メリット（節税）**：", man(annual_saving))
with colB:
    st.success(f"■ 社宅の累計メリット（名目）：**{man(sum_rent_nominal, 0)}**（{years_until_sale}年）")

st.markdown("---")

# ===== 下段：購入 =====
st.header("🔽 下段：購入（売却・税・仲介・ローン込み）")

# 物件
p1, p2, p3, p4 = st.columns(4)
with p1:
    land_price_man = st.number_input("土地価格（取得時・万円）", min_value=0, value=10_000, step=100)
with p2:
    land_growth = st.number_input("土地の値上がり率（年・%）", min_value=0.0, max_value=10.0, value=1.0, step=0.1) / 100.0
with p3:
    building_price_man = st.number_input("建物価格（取得時・万円）", min_value=0, value=5_000, step=100)
with p4:
    structure = st.selectbox("建物構造（定額法）", list(LIFE_MAP.keys()), index=0)

built_age = st.number_input("購入時点の築年数（年）", min_value=0, max_value=120, value=0, step=1)

# リフォーム（最大3件）— プレミアム率を各件に設定
st.markdown("### 🛠 リフォーム（資本的支出・定額法）＋ 市場価値プレミアム")
ren_enable = st.checkbox("リフォームを計上する", value=False)
ren_rows: List[dict] = []
if ren_enable:
    ren_count = st.number_input("リフォーム件数（最大3）", min_value=1, max_value=3, value=1, step=1)
    st.caption("※ 実施年は『取得後○年』。売却年より後の設定は未実施扱いで無視します。")
    for i in range(int(ren_count)):
        r1, r2, r3, r4 = st.columns(4)
        with r1:
            ry = st.number_input(f"#{i+1} 実施年（取得後○年）", min_value=1, max_value=100, value=min(10, years_until_sale), step=1, key=f"ren_y_{i}")
        with r2:
            rc_man = st.number_input(f"#{i+1} 費用（万円）", min_value=0, value=500, step=10, key=f"ren_c_{i}")
        with r3:
            life_mode = st.selectbox(
                f"#{i+1} 償却年数の扱い",
                ["法定年数で新規スタート", "残存年数で償却（残り耐用年数）"],
                index=0, key=f"ren_m_{i}"
            )
        with r4:
            prem = st.number_input(f"#{i+1} 市場価値プレミアム率（%）", min_value=0.0, max_value=200.0, value=20.0, step=5.0, key=f"ren_p_{i}") / 100.0
        ren_rows.append({"year": int(ry), "cost_yen": man_to_yen(rc_man), "mode": life_mode, "prem": prem})

# ローン
l1, l2, l3, l4 = st.columns(4)
with l1:
    loan_principal_man = st.number_input("借入金額（ローン元本・万円）", min_value=0, value=15_000, step=100)
with l2:
    loan_rate = st.number_input("金利（年・%）", min_value=0.0, max_value=10.0, value=1.0, step=0.05) / 100.0
with l3:
    loan_years = st.number_input("返済期間（年）", min_value=1, max_value=60, value=35, step=1)
with l4:
    repay_method = st.selectbox("返済方式", ["元利均等", "元金均等"])

# 売却・税
s1, s2, s3, s4 = st.columns(4)
with s1:
    apply_30m = st.checkbox("3,000万円特別控除（居住用）を適用", value=True)
with s2:
    tax_rate_cg = st.number_input("譲渡所得税率（長期・%）", min_value=0.0, max_value=55.0, value=20.315, step=0.1) / 100.0
with s3:
    vat_comm = st.number_input("消費税率（仲介手数料に適用・%）", min_value=0.0, max_value=20.0, value=10.0, step=0.5) / 100.0
with s4:
    st.write("")

# 円換算
land_price     = man_to_yen(land_price_man)
building_price = man_to_yen(building_price_man)
loan_principal = man_to_yen(loan_principal_man)

# 建物簿価（中古は残存年数償却）
building_book_base = building_book_value_straight(building_price, structure, years_until_sale, built_age_at_purchase=built_age)

# リフォーム簿価＋プレミアム
ren_book_total = 0.0
ren_total_spend = 0.0
ren_premium_total = 0.0
if ren_enable and ren_rows:
    base_life = LIFE_MAP[structure]
    for r in ren_rows:
        if r["year"] > years_until_sale:
            continue  # 売却後は未実施として無視
        years_since = max(0, years_until_sale - r["year"])
        life_used = base_life if r["mode"] == "法定年数で新規スタート" else max(1, base_life - r["year"])
        rem_book = remaining_book_straight(r["cost_yen"], life_used, years_since)  # 簿価ベース
        ren_book_total += rem_book
        ren_total_spend += r["cost_yen"]
        ren_premium_total += rem_book * r["prem"]  # 市場プレミアム（簿価に対する上乗せ）

# 建物：簿価と“市場価値”
building_book_total   = building_book_base + ren_book_total
building_market_value = building_book_total + ren_premium_total  # ←上乗せ分

# 土地将来価格
land_future = land_price * ((1 + land_growth) ** years_until_sale)
land_appreciation = land_future - land_price

# 残債（月ベース）
am_df = amortization_schedule_annual(loan_principal, loan_rate, loan_years, method=repay_method)
loan_balance = remaining_balance_monthly(loan_principal, loan_rate, loan_years, years_until_sale, repay_method)

# 月々返済
if repay_method == "元利均等":
    monthly_payment = annuity_payment_monthly(loan_principal, loan_rate, loan_years)
    monthly_payment_label = f"{man(monthly_payment, 1)} / 月"
else:
    r_m = loan_rate / 12.0
    pr_m = loan_principal / (loan_years * 12)
    first_month = pr_m + loan_principal * r_m
    monthly_payment_label = f"{man(first_month, 1)} / 月（初月目安）"

# 売却価格（市場価値を採用）
sale_price = land_future + building_market_value

# 仲介手数料（3% + 6万 + 消費税）
commission = (sale_price * 0.03 + 60_000) * (1 + vat_comm)

# 取得費（税務は簿価ベースのみ）
acquisition_cost = land_price + building_book_total

# 譲渡所得
gain_base = sale_price - commission - acquisition_cost
deduction = 30_000_000 if apply_30m else 0
taxable_gain = max(0.0, gain_base - deduction)
capital_gains_tax = taxable_gain * tax_rate_cg

# 手残り
net_proceeds = sale_price - commission - capital_gains_tax - loan_balance

# 累計資産（元金累計）
cumulative_equity = loan_principal - loan_balance

# ===== サマリー（指定の順） =====
st.subheader("計算サマリー（購入）")
a, b, c = st.columns(3)

with a:
    st.write("**土地（将来価格）**", man(land_future, 0))
    st.write("**土地の値上がり額**", man(land_appreciation, 0))
    st.write("**建物（簿価＝減価償却後の価格）**", man(building_book_total, 0))
    sub = f"（内訳：既存 {man(building_book_base,0)}"
    if ren_enable:
        sub += f" ＋ リフォーム残簿価 {man(ren_book_total,0)}"
        if ren_premium_total > 0:
            sub += f" ＋ 市場プレミアム {man(ren_premium_total,0)}"
        sub += f"／ リフォーム投資累計 {man(ren_total_spend,0)}"
    sub += "）"
    st.caption(sub)
    st.caption(f"月々返済金額：{monthly_payment_label}")

with b:
    st.write("**売却価格（＝土地+建物簿価）**", man(sale_price, 0))
    st.write("**仲介手数料**", man(commission, 0))
    st.write("**売却時ローン残債**", man(loan_balance, 0))
    st.caption(f"累計資産額（元金累計）：{man(cumulative_equity, 0)}")

with c:
    st.write("**取得費（＝土地+建物簿価）**", man(acquisition_cost, 0))
    st.write("**譲渡所得（控除前）**", man(max(0.0, gain_base), 0))
    st.write("**課税譲渡所得**", man(taxable_gain, 0))
    st.write("**譲渡所得税**", man(capital_gains_tax, 0))

st.success(f"■ 売却手残り（名目）：**{man(net_proceeds, 0)}**")

# ===== 比較 =====
st.markdown("---")
st.subheader("📊 最終比較（社宅 累計 vs 購入 手残り）")
cmp_df = pd.DataFrame({
    "区分": ["社宅（累計メリット）", "購入（売却手残り）", "差額（購入−社宅）"],
    "金額（円）": [sum_rent_nominal, net_proceeds, net_proceeds - sum_rent_nominal],
})
disp = cmp_df.copy()
disp["金額（万円）"] = (disp["金額（円）"] / 10_000).round(0)
st.dataframe(disp[["区分", "金額（万円）"]], use_container_width=True)

diff = net_proceeds - sum_rent_nominal
if diff >= 0:
    st.success(f"■ 名目ベースの優位：**購入が {man(diff, 0)} 有利**")
else:
    st.warning(f"■ 名目ベースの優位：**社宅が {man(-diff, 0)} 有利**")

# ===== 返済表 =====
st.markdown("---")
st.subheader("📄 住宅ローン返済表（年次・万円）")
am = amortization_schedule_annual(loan_principal, loan_rate, loan_years, method=repay_method)
for col in ["返済額", "利息", "元金", "資産累計", "期末残債"]:
    am[col] = (am[col] / 10_000).round(1)
st.dataframe(am[["年", "利息", "元金", "資産累計", "期末残債"]], use_container_width=True)