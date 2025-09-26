# pages/loan_comparison.py
import streamlit as st
import pandas as pd

st.set_page_config(page_title="住宅ローン比較（変動 vs フラット）", page_icon="🏠", layout="wide")

# ===============================
# 計算ユーティリティ
# ===============================
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
        if year in rate_schedule:
            current_rate = rate_schedule[year]
            monthly = monthly_payment(balance, current_rate, total_months - m + 1)

        interest = balance * (current_rate / 100 / 12)
        principal_payment = monthly - interest
        balance -= principal_payment
        total_paid += monthly

        if m % 12 == 0 and year in checkpoints:
            results[year] = {
                "金利": round(current_rate, 3),
                "月額": round(monthly / 10000, 1),
                "累計": round(total_paid / 10000, 1),
            }
    return results

# ===============================
# UI 入力
# ===============================
st.title("🏠 住宅ローン比較（変動 vs フラット35）")

col1, col2 = st.columns(2)
with col1:
    principal = st.number_input("借入金額（万円）", min_value=100, value=5000, step=100)
with col2:
    years = st.number_input("返済期間（年）", min_value=1, max_value=50, value=35)

base_var = st.number_input("変動金利 初期値（％）", value=0.520, step=0.001, format="%.3f")
flat_rate = st.number_input("フラット35 基準金利（％）", value=1.500, step=0.001, format="%.3f")

checkpoints = [1, 5, 10, 20, 30, 35, 45, 50]

# ===============================
# 金利シナリオ定義
# ===============================
rate_scenarios = {}

# 現状維持
rate_scenarios["変動 現状維持"] = {y: base_var for y in range(1, years + 1)}

# BAD (+0.1%/年)
bad = {}
for y in range(1, years + 1):
    bad[y] = base_var + 0.1 * (y - 1)
rate_scenarios["変動 BAD (+0.1%/年)"] = bad

# GOOD (−0.01%/年, 下限0.25%)
good = {}
for y in range(1, years + 1):
    r = base_var - 0.01 * (y - 1)
    good[y] = max(r, 0.25)
rate_scenarios["変動 GOOD (−0.01%/年)"] = good

# FREE (自由入力: テーブル)
st.markdown("### 自由入力（金利スケジュール）")
init_df = pd.DataFrame({"年": list(range(1, years + 1)), "金利(%)": [base_var] * years})
free_df = st.data_editor(init_df, num_rows="dynamic", use_container_width=True)
free = {}
for _, row in free_df.iterrows():
    year = int(row["年"])
    rate = float(row["金利(%)"])
    free[year] = rate
rate_scenarios["変動 FREE（自由入力）"] = free

# フラット35（例：1P と 5P）
flat_1p = {y: flat_rate - 0.25 for y in range(1, years + 1)}
flat_5p = {}
for y in range(1, years + 1):
    if y <= 5:
        flat_5p[y] = flat_rate - 1.00
    elif y <= 10:
        flat_5p[y] = flat_rate - 0.25
    else:
        flat_5p[y] = flat_rate
rate_scenarios["フラット35 1P"] = flat_1p
rate_scenarios["フラット35 5P"] = flat_5p

# ===============================
# 計算 & 出力
# ===============================
st.markdown("### 📊 比較テーブル")
rows = []
for name, schedule in rate_scenarios.items():
    sim = simulate(principal, years, schedule, checkpoints)
    row = {"シナリオ": name}
    for y in checkpoints:
        if y in sim:
            row[f"{y}年"] = f"金利 {sim[y]['金利']}% | 月額 {sim[y]['月額']}万 | 累計 {sim[y]['累計']}万"
        else:
            row[f"{y}年"] = "-"
    rows.append(row)

df = pd.DataFrame(rows)
st.dataframe(df, use_container_width=True)
