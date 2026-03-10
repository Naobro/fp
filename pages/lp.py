import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==========================================
# ページ設定
# ==========================================
st.set_page_config(page_title="簡易ライフプラン表（住居費ver）", layout="wide")

# スタイル設定
hide_sidebar = """
<style>
section[data-testid='stSidebar'] {display: none !important;}
button[kind="header"] {display: none !important;}
[data-testid="stHeader"] {visibility: hidden !important;}
[data-testid="stToolbar"] {display: none !important;}
div.block-container {padding-top: 1rem !important; max-width: 100% !important;}
</style>
"""
st.markdown(hide_sidebar, unsafe_allow_html=True)

# ==========================================
# タイトル
# ==========================================
st.markdown("<h1 style='font-size:28px; text-align:center;'>📊 簡易ライフプラン表（住居費ver）</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#666;'>今後60年間の住居戦略完全比較</p>", unsafe_allow_html=True)

# ==========================================
# 1. 基本情報
# ==========================================
st.markdown("## 👨‍👩‍👧 基本情報")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 世帯情報")
    husband_age = st.number_input("夫の現在年齢（歳）", min_value=20, max_value=70, value=32)
    husband_income = st.number_input("夫の年収（万円）", min_value=0, value=600, step=10)

with col2:
    st.markdown("### 配偶者情報")
    wife_age = st.number_input("妻の現在年齢（歳）", min_value=20, max_value=70, value=30)
    wife_income = st.number_input("妻の年収（万円）", min_value=0, value=200, step=10)

with col3:
    household_income = husband_income + wife_income
    st.markdown("### 計算結果")
    st.metric("世帯年収", f"{household_income}万円")
    start_year = st.number_input("開始年", min_value=2020, max_value=2030, value=2025)

# 子供情報（0-5人対応）
st.markdown("### 👶 子供情報（0〜5人対応）")
children_count = st.number_input("子供人数", min_value=0, max_value=5, value=2)

children_ages = []
if children_count > 0:
    cols = st.columns(min(children_count, 5))
    for i in range(children_count):
        with cols[i]:
            age = st.number_input(
                f"第{i+1}子 現在年齢", 
                min_value=0, 
                max_value=25, 
                value=2 if i == 0 else 0, 
                key=f"child_{i}"
            )
            children_ages.append(age)

# ==========================================
# 2. 借入可能額自動計算
# ==========================================
st.markdown("---")
st.markdown("## 💰 借入可能額自動判定")

# 固定パラメータ
SCREENING_RATE = 0.03
REPAYMENT_RATIO = 0.40
MAX_COMPLETION_AGE = 79

# 計算
annual_repayment_capacity = household_income * 10000 * REPAYMENT_RATIO
monthly_repayment_capacity = annual_repayment_capacity / 12
max_loan_years = min(50, MAX_COMPLETION_AGE - husband_age)

def calculate_max_loan_amount(years):
    if years <= 0:
        return 0
    monthly_rate = SCREENING_RATE / 12
    n_months = years * 12
    return monthly_repayment_capacity * ((1 - (1 + monthly_rate)**(-n_months)) / monthly_rate)

max_loan_35 = calculate_max_loan_amount(35)
max_loan_max = calculate_max_loan_amount(max_loan_years)

col_loan1, col_loan2, col_loan3 = st.columns(3)

with col_loan1:
    st.metric("35年返済での借入可能額", f"{max_loan_35/10000:,.0f}万円")

with col_loan2:
    st.metric(f"最長{max_loan_years}年返済での借入可能額", f"{max_loan_max/10000:,.0f}万円")

with col_loan3:
    st.metric("月額返済可能額", f"{monthly_repayment_capacity/10000:,.1f}万円")

# ==========================================
# 3. 物件・資金計画
# ==========================================
st.markdown("---")
st.markdown("## 🏠 物件・資金計画")

col_prop1, col_prop2 = st.columns(2)

with col_prop1:
    property_price = st.number_input("物件価格（万円）", min_value=100, value=6000, step=100)
    self_funds = st.number_input("自己資金（万円）", min_value=0, value=500, step=50)
    loan_years = st.number_input("希望借入年数", min_value=1, max_value=max_loan_years, value=min(35, max_loan_years))

with col_prop2:
    closing_costs = property_price * 0.07
    total_cost = property_price + closing_costs
    required_loan = max(0, total_cost - self_funds)
    
    st.metric("諸費用（7%）", f"{closing_costs:,.0f}万円")
    st.metric("必要総額", f"{total_cost:,.0f}万円")
    st.metric("必要借入額", f"{required_loan:,.0f}万円")

# 借入可否判定
if required_loan <= max_loan_35:
    st.success(f"✅ 35年ローンで購入可能（余裕額：{(max_loan_35/10000 - required_loan):,.0f}万円）")
elif required_loan <= max_loan_max:
    st.warning(f"⚠️ 超長期ローン（{max_loan_years}年）なら購入可能")
else:
    shortage = required_loan - max_loan_max
    st.error(f"❌ 借入不可（不足額：{shortage:,.0f}万円）")

# ==========================================
# 4. 賃貸プラン設定
# ==========================================
st.markdown("---")
st.markdown("## 🏠 賃貸プラン設定")

current_rent = st.number_input("現在の家賃（万円/月）", min_value=0.0, value=12.0, step=0.5)
renewal_fee = st.number_input("更新料（ヶ月分/2年毎）", min_value=0.0, value=1.0, step=0.5)

# 家賃推移設定（シンプル版）
st.markdown("### 家賃推移設定")
col_rent1, col_rent2, col_rent3 = st.columns(3)

with col_rent1:
    rent_phase2_year = st.number_input("変更時期1（年後）", min_value=1, value=5)
    rent_phase2_amount = st.number_input("変更後家賃1（万円/月）", min_value=0.0, value=18.0, step=0.5)

with col_rent2:
    rent_phase3_year = st.number_input("変更時期2（年後）", min_value=1, value=30)
    rent_phase3_amount = st.number_input("変更後家賃2（万円/月）", min_value=0.0, value=15.0, step=0.5)

with col_rent3:
    st.info("例：\n5年後→18万円（子供誕生）\n30年後→15万円（老後）")

# 家賃スケジュール生成
rent_schedule = []
for year in range(1, 61):
    if year < rent_phase2_year:
        rent_schedule.append(current_rent)
    elif year < rent_phase3_year:
        rent_schedule.append(rent_phase2_amount)
    else:
        rent_schedule.append(rent_phase3_amount)

# ==========================================
# 5. 変動金利プラン設定
# ==========================================
st.markdown("---")
st.markdown("## 📈 変動金利プラン設定")

col_var1, col_var2 = st.columns(2)

with col_var1:
    base_rate_variable = st.number_input(
        "基準金利（%）", 
        min_value=0.0, 
        max_value=10.0, 
        value=0.6, 
        step=0.01,
        format="%.2f",
        key="var_base",
        help="36年以上の場合、自動的に+0.1%されます"
    )
    
    # 36年以上の場合の自動加算
    if loan_years >= 36:
        actual_variable_base = base_rate_variable + 0.1
        st.info(f"36年以上のため+0.1% → 実際の基準金利：{actual_variable_base:.2f}%")
    else:
        actual_variable_base = base_rate_variable

with col_var2:
    st.markdown("### 金利変動設定ツール")
    change_year = st.number_input("○年目から", min_value=1, max_value=60, value=5, key="var_change_year")
    change_rate = st.number_input("金利を○%にする", min_value=0.0, max_value=10.0, value=1.5, step=0.01, key="var_change_rate")
    
    if st.button("金利一括変更（以降継続）", key="var_change_btn"):
        if 'variable_rates' not in st.session_state:
            st.session_state.variable_rates = [actual_variable_base] * 60
        
        for i in range(change_year - 1, 60):
            st.session_state.variable_rates[i] = change_rate
        st.success(f"{change_year}年目以降を{change_rate}%に変更")

# 変動金利テーブル初期化
if 'variable_rates' not in st.session_state:
    st.session_state.variable_rates = [actual_variable_base] * 60

# 変動金利テーブル表示（抜粋）
st.markdown("### 変動金利スケジュール（抜粋表示）")
display_years = [1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]
var_display_data = {
    "年目": display_years,
    "金利(%)": [st.session_state.variable_rates[y-1] for y in display_years]
}
st.dataframe(pd.DataFrame(var_display_data), hide_index=True)

# ==========================================
# 6. 固定金利プラン設定（フラット35）
# ==========================================
st.markdown("---")
st.markdown("## 🏦 固定金利プラン設定（フラット35）")

col_flat1, col_flat2 = st.columns(2)

with col_flat1:
    base_rate_flat = st.number_input(
        "今月の基準金利（%）", 
        min_value=0.0, 
        max_value=10.0, 
        value=2.36, 
        step=0.01,
        format="%.2f",
        key="flat_base",
        help="フラット35の実際の基準金利を入力"
    )
    
    # 36年以上の場合の自動加算
    if loan_years >= 36:
        actual_flat_base = base_rate_flat + 0.1
        st.info(f"36年以上のため+0.1% → 実際の基準金利：{actual_flat_base:.2f}%")
    else:
        actual_flat_base = base_rate_flat

with col_flat2:
    st.markdown("### フラット35ポイント制度")
    
    # 子育てプラスポイント自動計算
    current_children = sum(1 for age in children_ages if age >= 0 and age < 18)
    
    if current_children > 0:
        child_plus_points = current_children
        st.metric("【子育てプラス】ポイント", f"{child_plus_points}pt", help=f"子供{current_children}人")
    else:
        # 子供がいない場合の若年夫婦判定
        is_young_couple = husband_age < 40 or wife_age < 40
        child_plus_points = 1 if is_young_couple else 0
        status = "若年夫婦" if is_young_couple else "対象外"
        st.metric("【子育てプラス】ポイント", f"{child_plus_points}pt", help=status)
    
    # 追加ポイント（簡易版）
    additional_points = 0
    col_pt1, col_pt2 = st.columns(2)
    with col_pt1:
        if st.checkbox("ZEH住宅", key="zeh"):
            additional_points += 3
        if st.checkbox("長期優良住宅", key="chouki"):
            additional_points += 2
    with col_pt2:
        if st.checkbox("省エネ基準", key="shoene"):
            additional_points += 1
        if st.checkbox("管理計画認定", key="kanri"):
            additional_points += 1
    
    total_flat_points = child_plus_points + additional_points
    st.metric("合計ポイント", f"{total_flat_points}pt")

# フラット35金利スケジュール自動生成
def generate_flat35_schedule(base_rate, total_points, loan_years):
    """フラット35のポイント制度による金利スケジュール生成"""
    
    # ポイント数による引き下げルール
    if total_points <= 2:
        discount_1_5 = total_points * 0.25
        discount_6_10 = 0
    elif total_points == 3:
        discount_1_5 = 0.75
        discount_6_10 = 0
    elif total_points == 4:
        discount_1_5 = 1.00
        discount_6_10 = 0
    else:  # 5pt以上
        discount_1_5 = 1.00
        discount_6_10 = 0.25
    
    # 年次金利スケジュール作成
    schedule = []
    for year in range(1, 61):
        if year <= loan_years:
            if year <= 5:
                rate = base_rate - discount_1_5
            elif year <= 10:
                rate = base_rate - discount_6_10
            else:
                rate = base_rate
            schedule.append(max(0.1, rate))
        else:
            schedule.append(0.0)
    
    return schedule

flat_rate_schedule = generate_flat35_schedule(actual_flat_base, total_flat_points, loan_years)

st.markdown("### フラット35金利スケジュール（自動生成）")
flat_display_data = {
    "年目": display_years,
    "金利(%)": [flat_rate_schedule[y-1] for y in display_years]
}
st.dataframe(pd.DataFrame(flat_display_data), hide_index=True)

if total_flat_points > 0:
    st.success(f"当初5年間：{flat_rate_schedule[0]:.2f}%、6年目以降：{flat_rate_schedule[5]:.2f}%")

# ==========================================
# 7. 正確な償却計算（毎年再計算）
# ==========================================
def calculate_exact_loan_schedule(loan_amount_man, loan_years, rate_schedule):
    """毎年再計算による正確な償却スケジュール"""
    
    remaining_balance = loan_amount_man * 10000  # 円換算
    schedule = []
    
    for year in range(1, 61):  # 60年固定
        if year <= loan_years and remaining_balance > 0:
            current_rate = rate_schedule[year - 1] / 100
            monthly_rate = current_rate / 12
            remaining_months = (loan_years - year + 1) * 12
            
            # 月額返済額計算（元利均等）
            if monthly_rate == 0:
                monthly_payment = remaining_balance / remaining_months
            else:
                monthly_payment = npf.pmt(monthly_rate, remaining_months, -remaining_balance)
            
            # 年間の元金・利息計算（月次で正確に）
            annual_principal = 0
            annual_interest = 0
            year_start_balance = remaining_balance
            
            for month in range(12):
                if remaining_balance <= 0:
                    break
                
                monthly_interest = remaining_balance * monthly_rate
                monthly_principal = monthly_payment - monthly_interest
                
                if monthly_principal > remaining_balance:
                    monthly_principal = remaining_balance
                
                annual_principal += monthly_principal
                annual_interest += monthly_interest
                remaining_balance -= monthly_principal
            
            schedule.append({
                "year": year,
                "rate": current_rate * 100,
                "monthly_payment": monthly_payment / 10000,
                "annual_payment": monthly_payment * 12 / 10000,
                "annual_principal": annual_principal / 10000,
                "annual_interest": annual_interest / 10000,
                "year_end_balance": remaining_balance / 10000
            })
        else:
            schedule.append({
                "year": year,
                "rate": 0,
                "monthly_payment": 0,
                "annual_payment": 0,
                "annual_principal": 0,
                "annual_interest": 0,
                "year_end_balance": 0
            })
    
    return schedule

# ==========================================
# 8. 60年シミュレーション実行
# ==========================================
st.markdown("---")
st.markdown("## 📊 60年間シミュレーション結果")

# 償却計算実行
variable_schedule = calculate_exact_loan_schedule(required_loan, loan_years, st.session_state.variable_rates)
flat_schedule = calculate_exact_loan_schedule(required_loan, loan_years, flat_rate_schedule)

# 60年分のライフプランデータ作成
simulation_data = []
maintenance_annual = 60  # 維持費（万円/年）

for year in range(1, 61):
    age = husband_age + year - 1
    year_display = start_year + year - 1
    
    # 家族人数計算（18歳未満の同居子供）
    children_this_year = sum(1 for c_age in children_ages if 0 <= (c_age + year - 1) < 18)
    family_size = 2 + children_this_year
    
    # 賃貸コスト
    rent_monthly = rent_schedule[year - 1]
    rent_annual = rent_monthly * 12
    if year % 2 == 0:  # 2年毎の更新料
        rent_annual += rent_monthly * renewal_fee
    
    # 変動金利コスト
    var_data = variable_schedule[year - 1]
    var_annual_payment = var_data["annual_payment"]
    var_annual_cost = var_annual_payment + maintenance_annual if var_annual_payment > 0 else 0
    
    # 固定金利コスト
    flat_data = flat_schedule[year - 1]
    flat_annual_payment = flat_data["annual_payment"]
    flat_annual_cost = flat_annual_payment + maintenance_annual if flat_annual_payment > 0 else 0
    
    simulation_data.append({
        "年目": year,
        "西暦": year_display,
        "年齢": age,
        "家族人数": family_size,
        "賃貸年額": rent_annual,
        "変動年額": var_annual_cost,
        "固定年額": flat_annual_cost,
        "変動月額": var_data["monthly_payment"],
        "固定月額": flat_data["monthly_payment"],
        "変動残債": var_data["year_end_balance"],
        "固定残債": flat_data["year_end_balance"],
        "変動金利": var_data["rate"],
        "固定金利": flat_data["rate"]
    })

df_simulation = pd.DataFrame(simulation_data)

# 結果表示（重要な年のみ抜粋）
important_years = [1, 5, 10, 15, 20, 25, 30, 35, 40, 50, 60]
df_display = df_simulation[df_simulation["年目"].isin(important_years)].copy()

# 表示用に数値を整形
display_columns = ["年目", "西暦", "年齢", "家族人数", "賃貸年額", "変動月額", "固定月額", "変動残債", "固定残債"]
df_show = df_display[display_columns].copy()

for col in ["賃貸年額", "変動月額", "固定月額", "変動残債", "固定残債"]:
    df_show[col] = df_show[col].apply(lambda x: f"{x:,.1f}" if x > 0 else "-")

st.dataframe(df_show, hide_index=True, use_container_width=True)

# ==========================================
# 9. グラフ表示
# ==========================================
fig = make_subplots(
    rows=2, cols=2,
    subplot_titles=('月額住居費の推移', 'ローン残債の推移', '年間住居費の推移', '適用金利の推移'),
    vertical_spacing=0.1,
    horizontal_spacing=0.1
)

# 月額住居費
fig.add_trace(
    go.Scatter(
        x=df_simulation["年齢"], 
        y=df_simulation["賃貸年額"]/12, 
        name="賃貸", 
        line=dict(color='orange', width=3)
    ),
    row=1, col=1
)

fig.add_trace(
    go.Scatter(
        x=df_simulation["年齢"], 
        y=df_simulation["変動月額"], 
        name="変動", 
        line=dict(color='blue', width=3)
    ),
    row=1, col=1
)

fig.add_trace(
    go.Scatter(
        x=df_simulation["年齢"], 
        y=df_simulation["固定月額"], 
        name="固定", 
        line=dict(color='green', width=3)
    ),
    row=1, col=1
)

# ローン残債
fig.add_trace(
    go.Scatter(
        x=df_simulation["年齢"], 
        y=df_simulation["変動残債"], 
        name="変動残債", 
        line=dict(color='blue', dash='dot'),
        showlegend=False
    ),
    row=1, col=2
)

fig.add_trace(
    go.Scatter(
        x=df_simulation["年齢"], 
        y=df_simulation["固定残債"], 
        name="固定残債", 
        line=dict(color='green', dash='dot'),
        showlegend=False
    ),
    row=1, col=2
)

# 年間住居費
fig.add_trace(
    go.Scatter(
        x=df_simulation["年齢"], 
        y=df_simulation["賃貸年額"], 
        name="賃貸年額", 
        line=dict(color='orange'),
        showlegend=False
    ),
    row=2, col=1
)

fig.add_trace(
    go.Scatter(
        x=df_simulation["年齢"], 
        y=df_simulation["変動年額"], 
        name="変動年額", 
        line=dict(color='blue'),
        showlegend=False
    ),
    row=2, col=1
)

fig.add_trace(
    go.Scatter(
        x=df_simulation["年齢"], 
        y=df_simulation["固定年額"], 
        name="固定年額", 
        line=dict(color='green'),
        showlegend=False
    ),
    row=2, col=1
)

# 適用金利
fig.add_trace(
    go.Scatter(
        x=df_simulation["年齢"], 
        y=df_simulation["変動金利"], 
        name="変動金利", 
        line=dict(color='blue'),
        showlegend=False
    ),
    row=2, col=2
)

fig.add_trace(
    go.Scatter(
        x=df_simulation["年齢"], 
        y=df_simulation["固定金利"], 
        name="固定金利", 
        line=dict(color='green'),
        showlegend=False
    ),
    row=2, col=2
)

# レイアウト更新
for i, j in [(1,1), (1,2), (2,1), (2,2)]:
    fig.update_xaxes(title_text="年齢", row=i, col=j)

fig.update_yaxes(title_text="月額（万円）", row=1, col=1)
fig.update_yaxes(title_text="残債（万円）", row=1, col=2)
fig.update_yaxes(title_text="年額（万円）", row=2, col=1)
fig.update_yaxes(title_text="金利（%）", row=2, col=2)

fig.update_layout(height=800, showlegend=True)
st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 10. 最終比較結果
# ==========================================
st.markdown("---")
st.markdown("## 🎯 最終比較結果（60年後）")

# 60年間の総コスト計算
total_rent_cost = df_simulation["賃貸年額"].sum()
total_var_cost = df_simulation["変動年額"].sum()
total_flat_cost = df_simulation["固定年額"].sum()

# 最終資産計算（簡易版）
final_property_value = property_price * 0.5  # 簡易的に50%残存と仮定

col_final1, col_final2, col_final3 = st.columns(3)

with col_final1:
    st.metric("賃貸コース", f"{total_rent_cost:,.0f}万円", help="60年間の総住居費")
    st.caption("手元資産：0万円")

with col_final2:
    var_advantage = total_rent_cost - total_var_cost
    st.metric("変動金利コース", f"{total_var_cost:,.0f}万円", delta=f"賃貸より{var_advantage:,.0f}万円お得")
    st.caption(f"手元資産：約{final_property_value:,.0f}万円")

with col_final3:
    flat_advantage = total_rent_cost - total_flat_cost
    st.metric("固定金利コース", f"{total_flat_cost:,.0f}万円", delta=f"賃貸より{flat_advantage:,.0f}万円お得")
    st.caption(f"手元資産：約{final_property_value:,.0f}万円")

# 計算精度確認
final_var_balance = df_simulation.iloc[-1]["変動残債"]
final_flat_balance = df_simulation.iloc[-1]["固定残債"]

if abs(final_var_balance) < 1 and abs(final_flat_balance) < 1:
    st.success("✅ 計算精度確認済み：ローン完済確認")
else:
    st.warning(f"⚠️ 残債計算要確認：変動{final_var_balance:.1f}万円、固定{final_flat_balance:.1f}万円")

# ==========================================
# 11. 待機コスト判定
# ==========================================
st.markdown("---")
st.markdown("## ⏰ 「今は時期じゃない」対策（待機コスト判定）")

wait_years = st.number_input("何年待つ予定ですか？", min_value=1, max_value=10, value=2)

# 機会損失計算
rent_loss = current_rent * 12 * wait_years
first_year_principal = variable_schedule[0]["annual_principal"]
principal_loss = first_year_principal * wait_years
deduction_loss = 28 * wait_years  # 概算

total_opportunity_loss = rent_loss + principal_loss + deduction_loss
breakeven_decline_rate = (total_opportunity_loss / property_price) * 100

col_wait1, col_wait2 = st.columns(2)

with col_wait1:
    st.error(f"🚨 **{wait_years}年待つ機会損失：約{total_opportunity_loss:,.0f}万円**")
    st.write(f"• 捨て家賃：{rent_loss:,.0f}万円")
    st.write(f"• 元金積立の遅れ：{principal_loss:,.0f}万円")
    st.write(f"• 住宅ローン控除の遅れ：{deduction_loss:,.0f}万円")

with col_wait2:
    st.info(f"📉 **損益分岐点：{breakeven_decline_rate:.1f}%の価格下落**")
    st.write(f"物件が{property_price:,.0f}万円から{property_price - total_opportunity_loss:,.0f}万円まで")
    st.write("下落しないと待つ価値がありません")

# PDF出力案内
st.markdown("---")
st.info("💡 **PDF出力方法**：ブラウザの印刷機能（Ctrl+P）を使用してPDFとして保存してください。")

# LINEバナー（既存コードから）
import urllib.parse as _url

def render_line_banner():
    if "line_banner_closed" not in st.session_state:
        st.session_state.line_banner_closed = False
    
    try:
        qp = st.query_params
        close_flag = str(qp.get("close_banner", "0")) == "1"
        qp_dict = dict(qp)
    except Exception:
        qp = st.experimental_get_query_params()
        close_flag = (qp.get("close_banner", ["0"])[0] == "1")
        qp_dict = {k: (v[0] if isinstance(v, list) else v) for k, v in qp.items()}
    
    if close_flag:
        st.session_state.line_banner_closed = True
    
    if st.session_state.line_banner_closed:
        return
    
    qp_dict = {k: (v if not isinstance(v, list) else v[0]) for k, v in qp_dict.items()}
    qp_dict["close_banner"] = "1"
    qs = _url.urlencode(qp_dict)
    close_url = "?" + qs if qs else "?close_banner=1"
    
    st.markdown(f"""
    <style>
    .line-banner-wrap {{
      position: fixed;
      bottom: 100px; right: 18px; z-index: 9999;
    }}
    .line-banner {{
      background: #06C755; color: #fff;
      padding: 14px 18px 20px; border-radius: 12px;
      box-shadow: 0 4px 10px rgba(0,0,0,0.25);
      font-size: 15px; text-align: center; position: relative;
    }}
    .line-banner:hover {{ transform: scale(1.02); background:#05b34d; }}
    .line-banner .ttl {{ font-size: 17px; font-weight: 800; line-height: 1.4; }}
    .line-banner .id  {{ font-size: 20px; font-weight: 900; margin: 6px 0 6px; }}
    .line-banner img  {{
      width: 130px; display:block; margin: 8px auto 10px;
      border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.3);
      background:#fff;
    }}
    .line-banner .cta {{ display:inline-block; font-weight: 800; text-decoration: underline; color:#fff; }}
    .line-banner .close-btn {{
      position:absolute; top:6px; right:10px; width:24px; height:24px;
      border-radius:50%; background: rgba(0,0,0,0.25);
      color:#fff; text-align:center; line-height:24px;
      font-size:16px; font-weight:700; text-decoration:none;
    }}
    .line-banner .close-btn:hover {{ background: rgba(0,0,0,0.4); }}
    @media (max-width: 768px){{
      .line-banner-wrap {{ bottom: 100px; right: 14px; }}
      .line-banner {{ padding: 12px 14px 18px; }}
      .line-banner img {{ width: 110px; }}
      .line-banner .id {{ font-size: 18px; }}
    }}
    </style>

    <div class="line-banner-wrap" id="line-banner">
      <div class="line-banner" role="region" aria-label="LINE公式バナー">
        <a class="close-btn" href="{close_url}" aria-label="バナーを閉じる">×</a>
        <a href="https://lin.ee/m40HEqN" target="_blank" rel="noopener" style="text-decoration:none; color:#fff;">
          <div class="ttl">📲 ライフプラン相談は<br>LINEで簡単・不動産相談</div>
          <div class="id">LINE ID：@fudo3</div>
          <img src="https://qr-official.line.me/gs/M_277qthwd_GW.png?oat_content=qr" alt="LINE公式QRコード">
          <span class="cta">▶ 公式LINEで相談する</span>
        </a>
      </div>
    </div>
    """, unsafe_allow_html=True)


