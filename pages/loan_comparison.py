# pages/loan_comparison.py
import streamlit as st
import pandas as pd

st.set_page_config(page_title="住宅ローン比較", page_icon="🏠", layout="wide")

# ========== 元利均等返済の計算関数 ==========
def monthly_payment(principal: float, annual_rate: float, months: int):
    """元利均等返済の毎月返済額"""
    r = annual_rate / 100 / 12
    if r == 0:
        return principal / months
    return principal * r * (1 + r) ** months / ((1 + r) ** months - 1)

def simulate(principal: int, years: int, rate_schedule: dict):
    """
    年ごとの返済をシミュレーション
    principal: 借入金額（万円）
    years: 返済期間（年）
    rate_schedule: {year: rate} の辞書。指定年から金利変更。
    """
    balance = principal * 10000
    total_paid = 0
    results = {}

    current_rate = None
    monthly = 0

    for m in range(1, years * 12 + 1):
        year = (m - 1) // 12 + 1
        # 金利切替
        if year in rate_schedule:
            current_rate = rate_schedule[year]
            monthly = monthly_payment(balance, current_rate, years * 12 - m + 1)

        # 返済処理
        interest = balance * (current_rate / 100 / 12)
        principal_payment = monthly - interest
        balance -= principal_payment
        total_paid += monthly

        # 年次記録
        if m % 12 == 0:
            results[year] = {
                "金利": round(current_rate, 2),
                "月額": round(monthly),
                "累計": round(total_paid),
                "残債": round(balance)
            }
    return results

# ========== 入力 ==========
st.title("🏠 住宅ローン比較シミュレーター")

col1, col2 = st.columns(2)
with col1:
    principal = st.number_input("借入金額（万円）", value=5000, step=100)
with col2:
    years = st.number_input("返済期間（年）", value=35, step=1)

st.markdown("### 🔧 金利シナリオ入力")

# 変動金利シナリオ
st.subheader("変動金利シナリオ")
var1 = st.number_input("① 現状維持シナリオ（%）", value=0.52, step=0.01)
var2 = st.number_input("② 毎年 +0.1% シナリオ（初期%）", value=0.52, step=0.01)
var3 = st.number_input("③ 毎年 +0.25% シナリオ（初期%）", value=0.52, step=0.01)
var4 = st.number_input("④ 毎年 -0.1% シナリオ（初期%）", value=0.52, step=0.01)

st.markdown("⑤ 自由入力シナリオ（年ごとの金利を辞書形式で指定してください）")
custom_str = st.text_area("例: {1:0.52, 11:0.6, 12:0.4, 20:2.0}", value="{1:0.52, 11:0.6, 12:0.4, 20:2.0}")
try:
    var5_schedule = eval(custom_str)
except:
    var5_schedule = {1: var1}

# 固定金利・フラット・ミックス
st.subheader("固定・フラット・ミックス")
fix2 = st.number_input("固定金利2年（%）", value=0.35, step=0.01)
fix10 = st.number_input("固定金利10年（%）", value=0.85, step=0.01)
flat = st.number_input("フラット35（%）", value=1.30, step=0.01)
flat_child = st.number_input("フラット子育て（%）", value=1.25, step=0.01)
flat_s = st.number_input("フラット35S（%）", value=1.20, step=0.01)
flat_s_child = st.number_input("フラット35S子育て（%）", value=1.15, step=0.01)
mix_ratio = st.slider("ミックスローン：変動と固定の割合（%）", 0, 100, 50)

# ========== シナリオ定義 ==========
scenarios = {
    "変動① 現状維持": {1: var1},
    "変動② 毎年+0.1%": {y: var2 + 0.1*(y-1) for y in range(1, years+1)},
    "変動③ 毎年+0.25%": {y: var3 + 0.25*(y-1) for y in range(1, years+1)},
    "変動④ 毎年-0.1%": {y: max(var4 - 0.1*(y-1), 0.0) for y in range(1, years+1)},
    "変動⑤ 自由入力": var5_schedule,
    "固定2年": {1: fix2},
    "固定10年": {1: fix10},
    "フラット35": {1: flat},
    "フラット子育て": {1: flat_child},
    "フラット35S": {1: flat_s},
    "フラット35S子育て": {1: flat_s_child},
    "ミックス": {1: (mix_ratio/100)*var1 + (1-mix_ratio/100)*fix10},
}

# ========== 計算 ==========
results = {}
for name, schedule in scenarios.items():
    sim = simulate(principal, years, schedule)
    results[name] = sim

# ========== 表示 ==========
st.subheader("📊 返済シミュレーション結果")
df = pd.DataFrame({
    name: {y: f"金利:{data['金利']}%\n月額:{data['月額']:,.0f}円\n累計:{data['累計']:,.0f}円\n残債:{data['残債']:,.0f}円"
           for y, data in sim.items()}
    for name, sim in results.items()
}).T

st.dataframe(df, use_container_width=True)