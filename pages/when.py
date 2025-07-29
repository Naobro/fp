import streamlit as st
import numpy_financial as npf

st.title("【損失回避バイアス可視化】家賃vs購入 “今が得”か一目瞭然ツール")

# =============================
# 1. 入力フォーム
# =============================
st.header("【入力】")
col1, col2 = st.columns(2)
with col1:
    rent = st.number_input("現在の家賃（月額, 万円）", min_value=1, max_value=100, value=15)
    years_wait = st.number_input("何年待つ？（例:5年）", min_value=1, max_value=40, value=5)
    age_start = st.number_input("開始年齢", min_value=18, max_value=80, value=35)
with col2:
    price_now = st.number_input("今購入できる物件価格（万円）", min_value=500, max_value=30000, value=8000)
    self_funds = st.number_input("自己資金（万円）", min_value=0, max_value=price_now, value=1000)
    loan_years = st.number_input("借入期間（年）", min_value=5, max_value=50, value=35)
    loan_rate = st.number_input("ローン金利（年％）", min_value=0.1, max_value=5.0, value=0.7) / 100
    prop_drop_rate = st.number_input("物件下落率（年%）", min_value=0.0, max_value=10.0, value=2.0) / 100

# =============================
# 2. 今買った場合の計算
# =============================
expense = int(round(price_now * 0.07))
loan_amount = price_now + expense - self_funds
loan_monthly = -npf.pmt(loan_rate / 12, loan_years * 12, loan_amount * 10000) / 10000
loan_monthly = int(round(loan_monthly, 0))

# 家賃合計（待機期間中の掛け捨て）
total_rent = int(rent * 12 * years_wait)

# 待機期間中に返済した累計額
loan_paid_wait = loan_monthly * 12 * years_wait

# 待機期間後の残債
bal = [loan_amount]
for y in range(1, years_wait + 1):
    left = bal[-1] * (1 + loan_rate) - loan_monthly * 12
    bal.append(max(left, 0))
remain = int(round(bal[-1], 0))

# 物件価値（年率下落）
value = int(round(price_now * ((1 - prop_drop_rate) ** years_wait)))

# 純資産（物件価値 - 残債）
asset = value - remain

# =============================
# 3. 待って買う場合
# =============================
st.markdown("---")
st.subheader("【シナリオ：今買う vs 待って買う】")

# 損失回避できる上限価格
price_future = st.number_input("5年後に“いくらの物件”なら損失ナシ？", min_value=0, max_value=price_now, value=price_now - total_rent)

# 実際に待って購入する場合
future_price = st.number_input("5年後購入した場合の物件価格（例: 7000）", min_value=0, max_value=price_now, value=7000)
future_expense = int(round(future_price * 0.07))
future_loan = future_price + future_expense - self_funds
future_value = int(round(future_price * ((1 - prop_drop_rate) ** loan_years)))
future_remain = future_loan  # 借入直後は残債＝借入額
future_asset = future_value - future_remain

# =============================
# 4. 結論メッセージ
# =============================
colA, colB = st.columns(2)
with colA:
    st.markdown("### 【結論】今すぐ購入した場合（5年後）")
    st.markdown(f"""
- 累計返済額: **{loan_paid_wait:,} 万円**
- 残債: **{remain:,} 万円**
- 物件価値: **{value:,} 万円**
- **純資産: {asset:,} 万円**
- 家賃と比べて5年後 **{total_rent:,} 万円の損失回避**
    """)
with colB:
    st.markdown("### 【5年後まで賃貸→購入なら？】")
    st.markdown(f"""
- 5年間で家賃 **{total_rent:,} 万円** 掛け捨て
- 5年後購入できる価格は **{price_future:,} 万円** まで
- 実際に 7,000 万円で買うと、純資産 **{future_asset:,} 万円**
    """)

# =============================
# 5. まとめPL・BS表
# =============================
st.markdown("---")
st.markdown("### 主要比較（PL/BSシミュレーションまとめ）")

data = [
    ["", "今すぐ購入", f"{years_wait}年後賃貸→購入"],
    ["初期購入価格", f"{price_now:,} 万円", f"{future_price:,} 万円"],
    ["5年間の家賃総額", "0 円", f"{total_rent:,} 万円"],
    ["5年後残債", f"{remain:,} 万円", f"{future_loan:,} 万円"],
    ["5年後物件価値", f"{value:,} 万円", f"{future_value:,} 万円"],
    ["5年後純資産", f"{asset:,} 万円", f"{future_asset:,} 万円"],
    ["損失差額", "0 円", f"{total_rent:,} 万円"],
]

st.table(data)

st.caption("※PL：キャッシュフロー差分（損失回避バイアス）。BS：5年後純資産・価値推移も一目瞭然。今買う方が“何円得か”即わかります。")
