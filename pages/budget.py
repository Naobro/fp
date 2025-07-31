import streamlit as st
import pandas as pd
import numpy_financial as npf
import matplotlib.pyplot as plt
from utils import set_matplotlib_japanese_font  # ✅ 追加

# ✅ フォント設定をutils.pyから呼び出す
set_matplotlib_japanese_font()

st.title("賃貸 vs 購入 住居費・資産価値シミュレーター")

# --- 賃貸プラン入力 ---
st.markdown("#### 年齢ごとの家賃設定（最大4区分・すべて万円単位/整数）")
age_rent_list = []
for i in range(4):
    c1, c2, c3 = st.columns([2, 2, 2])
    with c1:
        age_from = st.number_input(f"年齢（開始）", 0, 100,
                                   30 if i == 0 else 40 if i == 1 else 60 if i == 2 else 70, key=f"age_from_{i}")
    with c2:
        age_to = st.number_input(f"年齢（終了）", 0, 100,
                                 39 if i == 0 else 59 if i == 1 else 69 if i == 2 else 100, key=f"age_to_{i}")
    with c3:
        rent = st.number_input(f"家賃（万円）", 1, 100,
                               10 if i == 0 else 13 if i == 1 else 9 if i == 2 else 7, key=f"rent_{i}")
    age_rent_list.append((age_from, age_to, int(round(rent))))
st.caption("※賃料上昇率は自動で2年ごと2%、引越し費用は家賃×6ヶ月分が自動加算")

start_age = age_rent_list[0][0]
years = 50
ages = [start_age + i for i in range(years)]

# --- 年間家賃計算 ---
annual_rent = []
current_rent = None
increase_rate = 0.02
section_idx = 0
section = age_rent_list[section_idx]
section_start_idx = 0

for i, age in enumerate(ages):
    if section_idx < len(age_rent_list) and age > section[1]:
        section_idx += 1
        if section_idx < len(age_rent_list):
            section = age_rent_list[section_idx]
            section_start_idx = i
            current_rent = section[2]
    if current_rent is None or age == section[0]:
        current_rent = section[2]
        section_start_idx = i
    in_section_years = i - section_start_idx
    up_count = in_section_years // 2
    applied_rent = current_rent * ((1 + increase_rate) ** up_count)
    applied_rent = int(round(applied_rent))
    annual_rent.append(applied_rent * 12)

move_years = [section[0] for section in age_rent_list[1:]]
move_cost = [annual_rent[i] // 12 * 6 if ages[i] in move_years else 0 for i in range(years)]
cum_rent = []
total = 0
for i in range(years):
    total += annual_rent[i] + move_cost[i]
    cum_rent.append(total)

# --- 購入プラン入力 ---
st.markdown("---\n#### 購入条件の入力")
left, right = st.columns([2, 1])
with left:
    st.subheader("物件条件")
    property_type = st.radio("物件種別", ["マンション", "戸建て"])
    price = st.number_input("物件価格（万円）", 500, 30000, 5000)
    built_year = st.number_input("購入時点の築年数", 0, 100, 0)
    area = st.number_input("専有面積（㎡）", 10, 200, 70)
    reno = st.checkbox("リノベーション済み／予定")
    if property_type == "戸建て":
        land_area = st.number_input("土地面積（㎡）", 10, 500, 100)
        building_price = st.number_input("建物価格（万円）", 500, int(price), 1500)
    st.markdown("<hr style='border: 1.5px solid #0f0; margin: 18px 0;'>", unsafe_allow_html=True)

    st.subheader("売主区分")
    seller_type = st.radio("売主の種類", ["宅建業者・買取再販", "一般個人"], index=0)
    is_shinchiku = False
    if seller_type == "宅建業者・買取再販":
        is_shinchiku = st.checkbox("工事完了後2年以内かつ未入居（新築扱い）", value=True)
    else:
        is_shinchiku = False  # 個人の場合は新築不可

    st.subheader("借入条件")
    loan_years = st.number_input("借入期間（年）", 1, 50, 35)
    loan_rate = st.number_input("金利（年%）", 0.1, 5.0, 0.59) / 100
    funds = st.number_input("自己資金（万円）", 0, int(price), 500)
    if reno:
        reno_cost = st.number_input("リノベ費用（万円・不明なら自動計算）", 0, 3000, int(area * 10))
        reno_effect = st.slider("リノベ効果の資産価値反映率（目安0.6）", 0.0, 1.0, 0.6)
        reno_timing = st.number_input("リノベ実施タイミング（購入時=0年目、5年後=5など）", 0, years - 1, 0)
    else:
        reno_cost = 0
        reno_effect = 0
        reno_timing = 100
    if property_type == "戸建て":
        land_price = price - building_price

with right:
    st.write("")

expense = int(round(price * 0.07))
loan_amount = price + expense - funds
st.caption(f"諸費用（7%自動計算）：{expense}万円　→　借入額：{loan_amount}万円")

# --- ローン返済推移（元利均等返済・npf.pvで計算） ---
n_months = loan_years * 12
monthly_rate = loan_rate / 12
loan_monthly = -npf.pmt(monthly_rate, n_months, loan_amount * 10000) / 10000  # 万円
loan_monthly = int(round(loan_monthly, 0))
loan_payment = [loan_monthly * 12 if i < loan_years else 0 for i in range(years)]
loan_cumulative = [sum(loan_payment[:i + 1]) for i in range(years)]
loan_balance = []
for y in range(years):
    n = n_months - y * 12
    if n > 0:
        bal = npf.pv(monthly_rate, n, -loan_monthly * 10000, 0) / 10000  # 万円
        loan_balance.append(int(round(bal)))
    else:
        loan_balance.append(0)

# --- 資産価値推移 ---
property_value = []
if property_type == "マンション":
    for y in range(years):
        age = built_year + y
        if age <= 2:
            base = price * 0.92
        elif age <= 15:
            base = price * 0.92 * (0.98 ** (age - 2))
        elif age <= 30:
            base = price * 0.92 * (0.98 ** 13) * (0.985 ** (age - 15))
        else:
            base = price * 0.92 * (0.98 ** 13) * (0.985 ** 15) * (0.992 ** (age - 30))
        if reno and y == reno_timing:
            base += reno_cost * reno_effect
        property_value.append(int(base))
elif property_type == "戸建て":
    building_value = [building_price * ((1 - 0.04) ** y) for y in range(years)]
    land_value = [land_price for _ in range(years)]
    building_value = [max(b, 0) for b in building_value]
    for y in range(years):
        bv = building_value[y]
        lv = land_value[y]
        if reno and y == reno_timing:
            bv += reno_cost * reno_effect
        property_value.append(int(bv + lv))

# --- 住宅性能・世帯区分選択 ---
st.markdown("##### 住宅性能・世帯要件の選択")
perf = st.selectbox("住宅性能区分", [
    "長期優良住宅・低炭素住宅", "ZEH水準省エネ住宅", "省エネ基準適合住宅", "その他の住宅"])
is_kosodate = st.checkbox("子育て・若者世帯", value=False)

# --- 住宅ローン控除 判定ロジック ---
if seller_type == "宅建業者・買取再販" and is_shinchiku:
    if perf == "長期優良住宅・低炭素住宅":
        koujo_limit = 5000 if is_kosodate else 4500
        koujo_years = 13
    elif perf == "ZEH水準省エネ住宅":
        koujo_limit = 4500 if is_kosodate else 3500
        koujo_years = 13
    elif perf == "省エネ基準適合住宅":
        koujo_limit = 4000 if is_kosodate else 3000
        koujo_years = 13
    else:
        koujo_limit = 0
        koujo_years = 0
else:
    if perf in ["長期優良住宅・低炭素住宅", "ZEH水準省エネ住宅", "省エネ基準適合住宅"]:
        koujo_limit = 3000
        koujo_years = 10
    else:
        koujo_limit = 2000
        koujo_years = 10
koujo_years = min(loan_years, koujo_years)

koujo = []
for y in range(years):
    if y < koujo_years:
        k = min(loan_balance[y], koujo_limit) * 0.007
        koujo.append(int(round(k, 0)))
    else:
        koujo.append(0)
koujo_cumulative = [sum(koujo[:i + 1]) for i in range(years)]

# --- 横持ち比較テーブル ---
data = {
    "年齢": ages,
    "年間家賃": annual_rent,
    "引越し費用": move_cost,
    "賃貸累計支出": cum_rent,
    "　": [""] * years,
    "ローン返済(年)": loan_payment,
    "累計返済": loan_cumulative,
    "残債": loan_balance,
    "物件価値": property_value,
    "ローン控除額": koujo,
    "ローン控除累計": koujo_cumulative,
}
df = pd.DataFrame(data)
df = df.T.reset_index()
df.columns = ["項目"] + [str(age) for age in ages]
st.markdown("---\n#### 50年 賃貸vs購入 横持ち比較")
st.dataframe(df, width=2500, height=520)

# --- 残債 vs 評価額比較テーブル ---
gap = [pv - lb for pv, lb in zip(property_value, loan_balance)]
reverse_year = next((i for i, g in enumerate(gap) if g > 0), None)
df_compare = pd.DataFrame({
    "年齢": ages,
    "ローン残債": loan_balance,
    "資産価値": property_value,
    "差額（資産価値-残債）": gap,
})
def highlight_row(row):
    if reverse_year is not None and row.name == reverse_year:
        return ['background-color: #ffecb3'] * len(row)
    else:
        return [''] * len(row)
st.markdown("### 資産価値とローン残債の比較テーブル")
st.dataframe(df_compare.style.apply(highlight_row, axis=1), width=1100, height=420)

if reverse_year is not None:
    st.success(f"【アンダーローン脱却】年齢 {ages[reverse_year]} 歳（経過{reverse_year}年目）で資産価値がローン残債を上回ります！")
else:
    st.warning("※期間内で資産価値がローン残債を上回る年はありません。")

# --- 残債と資産価値の推移グラフ ---
st.markdown("### 残債と資産価値の推移グラフ")
fig2, ax2 = plt.subplots(figsize=(14, 4))
ax2.plot(ages, loan_balance, label="ローン残債", marker='o')
ax2.plot(ages, property_value, label="資産価値", marker='o')
if reverse_year is not None:
    ax2.axvline(ages[reverse_year], color='orange', linestyle='--', label='逆転年')
ax2.set_xlabel("年齢")
ax2.set_ylabel("万円")
ax2.set_title("資産価値とローン残債の推移")
ax2.legend()
ax2.grid(True)
st.pyplot(fig2)
st.caption("※ローン残債と資産価値（物件評価額）が逆転するタイミングに注目。背景黄色行が逆転年。")

# --- 住宅ローン控除 比較テーブル（完全版） ---
st.markdown("### 【2024-2025年度版】住宅ローン控除制度 比較表")
html_table = """
<style>
.mytable { border-collapse: collapse; width: 100%; font-size: 1.06em;}
.mytable th, .mytable td { border: 1px solid #aaa; padding: 7px 10px; text-align: center; vertical-align: middle;}
.mytable th { background: #e7f2fb;}
.red { color: #e53935; font-weight: bold; font-size: 1.1em;}
</style>
<table class="mytable">
<thead>
<tr>
  <th rowspan="2">新築／既存</th>
  <th rowspan="2">住宅の環境性能等</th>
  <th colspan="2">借入限度額</th>
  <th rowspan="2">控除期間</th>
</tr>
<tr>
  <th>子育て・若者</th>
  <th>その他</th>
</tr>
</thead>
<tbody>
<tr>
  <td rowspan="3">新築住宅<br>買取再販</td>
  <td>長期優良住宅・低炭素住宅</td>
  <td>5,000万円</td>
  <td>4,500万円</td>
  <td class="red">13年</td>
</tr>
<tr>
  <td>ZEH水準省エネ住宅</td>
  <td>4,500万円</td>
  <td>3,500万円</td>
  <td class="red">13年</td>
</tr>
<tr>
  <td>省エネ基準適合住宅</td>
  <td>4,000万円</td>
  <td>3,000万円</td>
  <td class="red">13年</td>
</tr>
<tr>
  <td rowspan="2">既存住宅</td>
  <td>長期優良・低炭素/ZEH/省エネ</td>
  <td>3,000万円</td>
  <td>3,000万円</td>
  <td class="red">10年</td>
</tr>
<tr>
  <td>その他の住宅</td>
  <td>2,000万円</td>
  <td>2,000万円</td>
  <td class="red">10年</td>
</tr>
</tbody>
</table>
"""
st.markdown(html_table, unsafe_allow_html=True)

# --- 控除要件・性能基準説明 ---
st.markdown("""
<div style='font-size:0.98em; text-align:left; margin-top:0.8em; line-height:1.7;'>
<b>【適用要件】</b><br>
・<b>床面積：</b>住宅の床面積が50㎡以上で、かつ床面積の2分の1以上を自己の居住用としていること<br>
・<b>所得要件：</b>控除を受ける年分の合計所得金額が2,000万円以下であること<br>
・<b>借入金の条件：</b>10年以上にわたり分割して返済する方法になっている住宅ローン等を利用していること<br>
・<b>中古住宅の耐震性：</b>昭和57年1月1日以後に建築された住宅、または耐震基準に適合することが証明された住宅であること<br>
・<b>子育て世帯・若者夫婦世帯：</b>
[1] 年齢19歳未満の扶養親族を有する者<br>
[2] 年齢40歳未満であって配偶者を有する者、又は年齢40歳以上であって年齢40歳未満の配偶者を有する者
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style='font-size:0.98em; text-align:left; margin-top:0.8em; line-height:1.7;'>
<b>【住宅性能区分の評価基準（住宅性能表示制度）】</b><br>
・<b>省エネ基準適合住宅：</b> 断熱等性能等級4以上 & 一次エネルギー消費量等級4以上<br>
・<b>ZEH水準省エネ住宅：</b> 断熱等性能等級5 & 一次エネルギー消費量等級6<br>
・<b>認定長期優良住宅：</b> ZEH水準＋耐震性能、劣化対策、維持管理等、幅広い認定基準
</div>
""", unsafe_allow_html=True)
