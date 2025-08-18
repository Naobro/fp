# fp/pages/購入時期.py
import math
import streamlit as st

# =========================
# ページ設定
# =========================
st.set_page_config(page_title="購入時期シミュレーション", layout="wide")
st.title("🏠 購入時期シミュレーション（今 vs 5年後）")
st.caption("※ すべて金額は『万円』単位で入力します。上限・下限はありません。")

# =========================
# ユーティリティ
# =========================
def monthly_payment(principal_man: float, years: int, annual_rate_percent: float) -> float:
    """
    元利均等返済の毎月返済額（万円）を返す
    principal_man: 借入額（万円）
    years: 返済年数（年）
    annual_rate_percent: 年利（%）
    """
    n = years * 12
    r = (annual_rate_percent / 100.0) / 12.0
    if n <= 0:
        return 0.0
    if r == 0:
        return principal_man / n
    return principal_man * r * (1 + r) ** n / ((1 + r) ** n - 1)

def cumulative_rent_5y(start_rent_man: float, yoy_increase_percent: float) -> float:
    """
    5年間の家賃累計（万円）を返す。
    start_rent_man: 1年目の月額家賃（万円）
    yoy_increase_percent: 年ごとの家賃上昇率（%）
    """
    total = 0.0
    monthly = start_rent_man
    for year in range(5):
        total += monthly * 12
        monthly *= (1 + yoy_increase_percent / 100.0)
    return total

# =========================
# 入力フォーム（上限・下限なし、万円単位）
# =========================
with st.sidebar:
    st.subheader("入力（万円・%）")
    now_price = st.number_input("現在の物件価格（万円）", value=6000, step=100)
    future_price = st.number_input("5年後の物件価格（万円）", value=7000, step=100)

    now_down = st.number_input("頭金（今・万円）", value=500, step=50)
    future_down = st.number_input("頭金（5年後・万円）", value=1000, step=50)

    now_rate = st.number_input("金利（年%・今）", value=0.7, step=0.05, format="%.2f")
    future_rate = st.number_input("金利（年%・5年後）", value=1.20, step=0.05, format="%.2f")

    years = st.number_input("返済年数（年）", value=35, step=1)

    rent_month_man = st.number_input("現在の月額家賃（万円）", value=12.0, step=0.5, format="%.1f")
    rent_yoy = st.number_input("家賃の年上昇率（%）", value=2.0, step=0.5, format="%.1f")

# =========================
# 計算（今買う場合）
# =========================
now_loan = max(now_price - now_down, 0)                 # 借入額（万円）
now_monthly = monthly_payment(now_loan, int(years), float(now_rate))

# =========================
# 計算（5年後に買う場合）
# =========================
future_loan = max(future_price - future_down, 0)        # 借入額（万円）
future_monthly = monthly_payment(future_loan, int(years), float(future_rate))

# 待機期間の家賃累計（5年分）
rent_5y_total = cumulative_rent_5y(rent_month_man, rent_yoy)

# =========================
# 表示
# =========================
colA, colB, colC = st.columns([1,1,1])

with colA:
    st.markdown("### 今すぐ購入")
    st.metric("物件価格", f"{now_price:,.0f} 万円")
    st.metric("頭金", f"{now_down:,.0f} 万円")
    st.metric("借入額", f"{now_loan:,.0f} 万円")
    st.metric("金利（年）", f"{now_rate:.2f} %")
    st.metric("毎月返済額（概算）", f"{now_monthly:,.1f} 万円/月")

with colB:
    st.markdown("### 5年後に購入")
    st.metric("物件価格（5年後）", f"{future_price:,.0f} 万円")
    st.metric("頭金（5年後）", f"{future_down:,.0f} 万円")
    st.metric("借入額（5年後）", f"{future_loan:,.0f} 万円")
    st.metric("金利（年・5年後）", f"{future_rate:.2f} %")
    st.metric("毎月返済額（概算・5年後）", f"{future_monthly:,.1f} 万円/月")

with colC:
    st.markdown("### 待機コスト（5年間）")
    st.metric("家賃累計（5年）", f"{rent_5y_total:,.0f} 万円")
    # 5年後の毎月返済 - 今の毎月返済
    monthly_diff = future_monthly - now_monthly
    label = "毎月返済の差（5年後 − 今）"
    st.metric(label, f"{monthly_diff:+.1f} 万円/月")

st.divider()

# =========================
# ざっくり結論
# =========================
st.markdown("### ざっくり結論")
bullets = []

# 月々がどれだけ違うか
if monthly_diff > 0:
    bullets.append(f"5年後の方が **毎月 {monthly_diff:.1f} 万円** 高くなる見込みです。")
elif monthly_diff < 0:
    bullets.append(f"5年後の方が **毎月 {abs(monthly_diff):.1f} 万円** 低くなる見込みです。")
else:
    bullets.append("月々返済は今も5年後も **ほぼ同じ** 見込みです。")

# 家賃累計の重さ
bullets.append(f"5年間待つ場合、家賃だけで **約 {rent_5y_total:,.0f} 万円** の支出となります。")

# 借入額の違い
loan_diff = future_loan - now_loan
if loan_diff > 0:
    bullets.append(f"借入額は5年後の方が **{loan_diff:,.0f} 万円** 多くなる見込みです。")
elif loan_diff < 0:
    bullets.append(f"借入額は5年後の方が **{abs(loan_diff):,.0f} 万円** 少なくなる見込みです。")

# 最後のまとめ（簡易）
if (monthly_diff >= 0 and rent_5y_total > 0 and future_loan >= now_loan):
    summary = "👉 **総合的には“今買う”ほうが有利**になりやすい条件です。"
elif (monthly_diff <= 0 and future_loan <= now_loan):
    summary = "👉 **総合的には“5年後に買う”選択も検討価値あり**の条件です。"
else:
    summary = "👉 条件次第で結論が変わります。頭金計画や金利見通しを加味して検討しましょう。"

# 表示
for b in bullets:
    st.write("• " + b)
st.success(summary)

# =========================
# メモ
# =========================
with st.expander("計算の前提（クリックで表示）"):
    st.write(
        """
- すべて **万円** 表記です（例：6,000万円 → 6000）。
- ローン返済は **元利均等返済** の概算です。諸費用・保険・管理費等は含めていません。
- 「5年後」シナリオは **家賃支出（5年分）** を別枠で表示しています。
- 実際の与信条件・手数料・保証料等で変動します。最終判断前に金融機関試算をご確認ください。
        """
    )