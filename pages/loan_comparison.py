# pages/loan_comparison.py
import streamlit as st
import pandas as pd

st.set_page_config(page_title="住宅ローン比較", page_icon="🏦", layout="wide")

# -------------------------------
# 返済額計算（元利均等）
# -------------------------------
def monthly_payment(balance: float, annual_rate: float, months: int) -> float:
    r = (annual_rate / 100) / 12
    if months <= 0:
        return 0.0
    if abs(r) < 1e-12:
        return balance / months
    return balance * r * (1 + r) ** months / ((1 + r) ** months - 1)

def simulate(principal: int, years: int, rate_schedule: dict[int, float], checkpoints: list[int]):
    balance = principal * 10000
    total_paid = 0
    results = {}
    total_months = years * 12
    monthly = 0
    current_rate = None

    for m in range(1, total_months + 1):
        year = (m - 1) // 12 + 1
        # 年初に金利更新
        if year in rate_schedule and (m - 1) % 12 == 0:
            current_rate = rate_schedule[year]
            monthly = monthly_payment(balance, current_rate, total_months - m + 1)

        # 1か月返済
        interest = balance * (current_rate / 100 / 12)
        principal_payment = monthly - interest
        balance -= principal_payment
        total_paid += monthly

        # 年末に記録
        if m % 12 == 0 and year in checkpoints:
            results[year] = {
                "金利": round(current_rate, 2),
                "月額": round(monthly / 10000, 1),
                "累計": round(total_paid / 10000, 0),
            }
    return results

# -------------------------------
# 複利運用シミュレーション
# -------------------------------
def compound_investment(monthly: float, annual_rate: float, years: int) -> float:
    r = (annual_rate / 100) / 12
    months = years * 12
    if months <= 0:
        return 0.0
    if abs(r) < 1e-12:
        return monthly * months
    return monthly * (((1 + r) ** months - 1) / r)

# -------------------------------
# UI
# -------------------------------
st.markdown(
    "<h3 style='font-size:22px;'>🏠 住宅ローン比較<br>（変動金利 vs 固定金利：フラット35）</h3>",
    unsafe_allow_html=True
)

col1, col2 = st.columns(2)
with col1:
    principal = st.number_input("借入金額（万円）", value=5000, step=100)
with col2:
    years = st.number_input("返済期間（年）", value=35, min_value=1, max_value=50)

base_rate = st.number_input("変動金利 初期値（％）", value=0.52, step=0.01, format="%.2f")
flat_rate = st.number_input("フラット35 基準金利（％）", value=1.89, step=0.01, format="%.2f")

checkpoints = [1, 5, 10, 20, 30, 35, 45, 50]

# -------------------------------
# 金利シナリオ
# -------------------------------
scenarios = {}

# 現状維持
scenarios["変動 現状維持"] = {y: base_rate for y in range(1, years + 1)}

# GOOD（毎年-0.01%, 下限0.25）
good = {}
for y in range(1, years + 1):
    good[y] = max(base_rate - 0.01 * (y - 1), 0.25)
scenarios["変動 GOOD"] = good

# BAD（指定テーブル）
bad_rates = {
    1: 0.52, 2: 0.686, 3: 0.852, 4: 1.018, 5: 1.184, 6: 1.35,
    7: 1.44, 8: 1.53, 9: 1.62, 10: 1.71, 11: 1.80, 12: 1.89,
    13: 1.98, 14: 2.07, 15: 2.16, 16: 2.25, 17: 2.30, 18: 2.35,
    19: 2.40, 20: 2.45, 21: 2.50, 22: 2.55, 23: 2.60, 24: 2.65,
    25: 2.70, 26: 2.75, 27: 2.80, 28: 2.85, 29: 2.90, 30: 2.95,
    31: 3.00, 32: 3.05, 33: 3.10, 34: 3.15, 35: 3.20, 36: 3.25
}
scenarios["変動 BAD"] = {y: bad_rates.get(y, 3.25) for y in range(1, years + 1)}

# FREE（横展開入力）
st.markdown(
    "<h3 style='font-size:22px;'>📊 金利　自由入力</h3>",
    unsafe_allow_html=True
)
free_df = pd.DataFrame({"年": list(range(1, years + 1)), "金利(%)": [base_rate] * years}).T
free_df.columns = [f"{i}年" for i in range(1, years + 1)]
edited_free = st.data_editor(free_df, use_container_width=True)
free = {}
for idx, col in enumerate(edited_free.columns):
    free[idx + 1] = float(edited_free.loc["金利(%)", col])
scenarios["変動 FREE"] = free

# フラット35 1P
flat1 = {}
for y in range(1, years + 1):
    flat1[y] = flat_rate - 0.25 if y <= 5 else flat_rate
scenarios["フラット35 1P"] = flat1

# フラット35 5P
flat5 = {}
for y in range(1, years + 1):
    if y <= 5:
        flat5[y] = flat_rate - 1.00
    elif y <= 10:
        flat5[y] = flat_rate - 0.25
    else:
        flat5[y] = flat_rate
scenarios["フラット35 5P"] = flat5

# -------------------------------
# シミュレーション結果表示
# -------------------------------
rows = []
for name, schedule in scenarios.items():
    sim = simulate(principal, years, schedule, checkpoints)
    row = {"シナリオ": name}
    for y in checkpoints:
        if y in sim:
            row[f"{y}年"] = f"金利{sim[y]['金利']}% / 月{sim[y]['月額']}万 / 累計{sim[y]['累計']}万"
        else:
            row[f"{y}年"] = "-"
    rows.append(row)

df = pd.DataFrame(rows)
st.dataframe(df, use_container_width=True)

# -------------------------------
# 注釈（テーブルの補足）
# -------------------------------
st.markdown("""
**注釈**  
- ※1P（当初5年間 年▲0.25％引下げ → 6年目以降は基準金利）  
- ※5P（当初5年間 年▲1.00％引下げ、6〜10年目 年▲0.25％引下げ → 11年目以降は基準金利）  
- BADシナリオ：2025年0.52％ → 2030年1.35％ → 2040年2.25％ → 2050年2.75％ → 2060年3.25％  
- GOODシナリオ：毎年 −0.01％（下限0.25％）
""")

# -------------------------------
# 差額投資シミュレーション
# -------------------------------
st.markdown(
    "<h3 style='font-size:22px;'>📈 差額投資シミュレーション</h3>",
    unsafe_allow_html=True
)

monthly_var = monthly_payment(principal * 10000, base_rate, years * 12)
monthly_flat = monthly_payment(principal * 10000, flat_rate, years * 12)

total_var = monthly_var * years * 12
total_flat = monthly_flat * years * 12

st.write(f"変動金利返済額（月）: {monthly_var:,.0f} 円")
st.write(f"固定金利返済額（月）: {monthly_flat:,.0f} 円")
st.write(f"変動金利返済総額: {total_var:,.0f} 円")
st.write(f"固定金利返済総額: {total_flat:,.0f} 円")

# 差額（毎月と総額）
diff_monthly = monthly_flat - monthly_var
diff_total = total_flat - total_var

st.write(f"差額（毎月）: {diff_monthly:,.0f} 円")
st.write(f"差額（総額）: {diff_total:,.0f} 円")

st.write(f"固定金利を払っているつもりで差額を運用すると")

# 差額を投資に回すケース
col3, col4 = st.columns(2)
with col3:
    invest_rate = st.number_input("想定利回り（年率）", value=4.0, step=0.1)
with col4:
    invest_years = st.number_input("運用期間（年）", value=years, step=1)

future_value = compound_investment(diff_monthly, invest_rate, invest_years)
st.success(f"積立結果は {future_value/10000:,.1f} 万円 になります。")

# -------------------------------
# メリット・デメリット表（縦に分ける版）
# -------------------------------
st.markdown(
    "<h3 style='font-size:20px;'>📊 変動・固定 メリット・デメリット</h3>",
    unsafe_allow_html=True
)

md_table = """
<div style="font-size:15px; line-height:1.8;">

<h4>変動金利</h4>

<b>メリット</b><br>
・借入時点の金利が低く、月々の返済額を抑えやすい<br>
・将来、金利が下がれば返済負担が軽くなる可能性<br>
・団信の選択肢が多い

<br>

<b>デメリット</b><br>
・金利上昇リスクで返済額が増える可能性<br>
・返済額が変動し、家計設計が不安定<br>
・未払利息リスクあり（125%ルールの影響）

<br><br>

<h4>固定金利</h4>

<b>メリット</b><br>
・返済額が固定で家計設計がしやすい<br>
・金利上昇リスクを排除できる安心感<br>
・団信加入が任意、健康に不安がある人でもローンを組める可能性

<br>

<b>デメリット</b><br>
・初期金利が変動型より高い<br>
・市場金利が下落しても返済額が変わらない（機会損失）<br>
・借入上限8,000万円
・物件により利用不可　適合証明必要

</div>
"""
st.markdown(md_table, unsafe_allow_html=True)
