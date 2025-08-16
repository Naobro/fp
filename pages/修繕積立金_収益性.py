import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ==============================
# 内部固定パラメータ（ユーザーには見せない）
# ==============================
INFLATION_RATE = 0.03  # 年3%固定

# 工事項目（周期, 単価）
WORKS = {
    "外壁塗装": {"cycle": 12, "unit_cost": 15000},   # 円/㎡
    "屋上防水": {"cycle": 15, "unit_cost": 12000},
    "給排水管更新": {"cycle": 30, "unit_cost": 20000},
    "エレベーター更新": {"cycle": 25, "unit_cost": 20000000},  # 1基2000万（1台換算）
}

# ==============================
# 入力フォーム
# ==============================
st.title("🏢 マンション修繕積立金シミュレーション")

st.sidebar.header("🔑 入力項目")

current_fund = st.sidebar.number_input("現在の修繕積立金（月額・マンション全体）", 0, 10_000_000, 1_000_000, step=10000)
my_area = st.sidebar.number_input("自分の専有面積（㎡）", 10, 500, 70)
total_area = st.sidebar.number_input("マンション延べ床面積（㎡）", 100, 100000, 5000)
age = st.sidebar.number_input("築年数（年）", 0, 100, 20)
units = st.sidebar.number_input("総戸数", 1, 1000, 100)
floors = st.sidebar.number_input("階数", 1, 60, 10)
rent_price = st.sidebar.number_input("近隣家賃相場（円/㎡）", 1000, 10000, 4000, step=100)

# ==============================
# 内部計算
# ==============================

# 1. 専有比率
share_ratio = my_area / total_area

# 2. 修繕積立金の年間額
annual_fund = current_fund * 12

# 3. シミュレーション年数（50年）
years = 50
current_year = 2025  # 今基準

# 4. 修繕計画表
records = []
balance = 0
cumulative_balance = []

for y in range(years):
    year = current_year + y
    # 積立金を追加
    balance += annual_fund

    # 工事費用発生チェック
    for work, info in WORKS.items():
        cycle = info["cycle"]
        unit_cost = info["unit_cost"]

        # 築年から見た発生年
        if ((age + y) % cycle) == 0 and (age + y) > 0:
            # 単価×延べ床面積（EVは例外で1基2000万扱い）
            if "エレベーター" in work:
                cost = unit_cost  # 1基前提
            else:
                cost = unit_cost * total_area

            # インフレ補正
            cost *= (1 + INFLATION_RATE) ** y

            # 引き落とし
            balance -= cost

            # 自分の負担
            my_cost = cost * share_ratio

            records.append({
                "年": year,
                "工事": work,
                "工事費用(総額)": int(cost),
                "あなたの負担額": int(my_cost),
                "残高(マンション全体)": int(balance)
            })

    cumulative_balance.append({"年": year, "残高": int(balance)})

df_works = pd.DataFrame(records)
df_balance = pd.DataFrame(cumulative_balance)

# ==============================
# 出力
# ==============================

st.subheader("📊 長期修繕計画（主要工事）")
st.dataframe(df_works)

st.subheader("💰 残高シミュレーション（全体）")
fig, ax = plt.subplots(figsize=(8,4))
ax.plot(df_balance["年"], df_balance["残高"], label="残高(全体)")
ax.axhline(0, color="red", linestyle="--", label="不足ライン")
ax.set_ylabel("円")
ax.legend()
st.pyplot(fig)

# 収益性評価
expected_rent = rent_price * my_area
monthly_my_share = current_fund * share_ratio
msg = "✅ 妥当な範囲です" if monthly_my_share < expected_rent * 0.2 else "⚠️ 家賃相場に比べて積立負担が重い可能性あり"

st.subheader("📈 収益性評価")
st.markdown(f"""
- あなたの月額積立負担（推計）: **{int(monthly_my_share):,}円**
- 近隣家賃水準: **{int(expected_rent):,}円**
- 評価: {msg}
""")