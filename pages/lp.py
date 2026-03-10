import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf

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

# 子供情報（0-5人対応・将来の出産計画対応）
st.markdown("### 👶 子供情報（0〜5人対応・将来の出産計画対応）")
st.caption("💡 既に誕生している子供と将来の出産予定を分けて入力できます")

children_count = st.number_input("子供人数（予定含む）", min_value=0, max_value=5, value=2, help="将来の予定も含めた合計人数")

children_birth_years = []  # 出生年リスト（負の数=既に誕生、正の数=将来誕生）

if children_count > 0:
    cols = st.columns(min(children_count, 5))
    for i in range(children_count):
        with cols[i]:
            st.markdown(f"#### 第{i+1}子")
            
            # 既に誕生済みか将来予定かを選択
            birth_status = st.radio(
                "状況",
                options=["既に誕生済み", "将来の予定"],
                index=0 if i == 0 else 1,
                key=f"child_status_{i}",
                label_visibility="collapsed"
            )
            
            if birth_status == "既に誕生済み":
                current_age = st.number_input(
                    "現在の年齢（歳）",
                    min_value=0,
                    max_value=25,
                    value=2 if i == 0 else 0,
                    key=f"child_age_{i}"
                )
                birth_year = -current_age
                children_birth_years.append(birth_year)
                st.success(f"✅ 現在{current_age}歳")
                
            else:  # 将来の予定
                years_until_birth = st.number_input(
                    "何年後に誕生予定？",
                    min_value=1,
                    max_value=20,
                    value=2 if i == 1 else (2 * i),
                    key=f"child_future_{i}"
                )
                children_birth_years.append(years_until_birth)
                st.info(f"📅 {years_until_birth}年後に誕生予定")

    # 入力内容の確認表示
    st.markdown("---")
    st.markdown("#### 📋 家族計画確認")
    family_plan_text = []
    for i, birth_year in enumerate(children_birth_years):
        if birth_year <= 0:
            age = abs(birth_year)
            family_plan_text.append(f"第{i+1}子：既に誕生済み（現在{age}歳）")
        else:
            family_plan_text.append(f"第{i+1}子：{birth_year}年後に誕生予定")
    
    for text in family_plan_text:
        st.write(f"• {text}")
else:
    st.info("💑 子供なし（DINKS）として計算します")
    children_birth_years = []

# ==========================================
# 2. 借入可能額自動計算
# ==========================================
st.markdown("---")
st.markdown("## 💰 借入可能額自動判定")

SCREENING_RATE = 0.03
REPAYMENT_RATIO = 0.40
MAX_COMPLETION_AGE = 79

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

def reset_loan_conditions():
    keys_to_reset = ['variable_rates', 'complete_table', 'last_loan_years', 'last_base_rate']
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]

col_prop1, col_prop2 = st.columns(2)

with col_prop1:
    property_price = st.number_input("物件価格（万円）", min_value=100, value=6000, step=100)
    self_funds = st.number_input("自己資金（万円）", min_value=0, value=500, step=50)
    
    loan_years = st.number_input(
        "希望借入年数", 
        min_value=1, 
        max_value=max_loan_years, 
        value=min(35, max_loan_years),
        on_change=reset_loan_conditions,
        help="年数を変更すると金利スケジュールが自動更新されます"
    )

with col_prop2:
    closing_costs = property_price * 0.07
    total_cost = property_price + closing_costs
    required_loan = max(0, total_cost - self_funds)
    
    st.metric("諸費用（7%）", f"{closing_costs:,.0f}万円")
    st.metric("必要総額", f"{total_cost:,.0f}万円")
    st.metric("必要借入額", f"{required_loan:,.0f}万円")

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
# 5. 60年完全比較テーブル
# ==========================================
st.markdown("---")
st.markdown("## 📊 60年完全比較テーブル（変動・固定・賃貸 統合表示）")

col_rate1, col_rate2, col_rate3 = st.columns(3)

with col_rate1:
    base_rate_variable = st.number_input(
        "変動金利 基準（%）", 
        min_value=0.0, max_value=10.0, value=0.6, step=0.01, format="%.2f",
        on_change=reset_loan_conditions
    )
    if loan_years >= 36:
        actual_variable_base = base_rate_variable + 0.1
        st.warning(f"⚠️ **超長期ローン（{loan_years}年）全期間+0.10%**")
        st.info(f"実際の金利：**{actual_variable_base:.2f}%**")
    else:
        actual_variable_base = base_rate_variable
        st.success(f"✅ 基準金利：{actual_variable_base:.2f}%")

with col_rate2:
    base_rate_flat = st.number_input(
        "固定金利 基準（%）", 
        min_value=0.0, max_value=10.0, value=2.36, step=0.01, format="%.2f",
        on_change=reset_loan_conditions
    )
    if loan_years >= 36:
        actual_flat_base = base_rate_flat + 0.1
        st.warning(f"⚠️ **超長期ローン（{loan_years}年）全期間+0.10%**")
        st.info(f"実際の金利：**{actual_flat_base:.2f}%**")
    else:
        actual_flat_base = base_rate_flat
        st.success(f"✅ 基準金利：{actual_flat_base:.2f}%")

with col_rate3:
    # フラット35ポイント計算（修正版）
    current_children_under18 = 0
    for birth_year in children_birth_years:
        if birth_year <= 0:  # 既に誕生済みの子供のみ
            current_age = abs(birth_year)
            if current_age < 18:
                current_children_under18 += 1
    
    if current_children_under18 > 0:
        child_plus_points = current_children_under18
        st.metric("子育てプラス", f"{child_plus_points}pt")
    else:
        is_young_couple = husband_age < 40 or wife_age < 40
        child_plus_points = 1 if is_young_couple else 0
        st.metric("子育てプラス", f"{child_plus_points}pt")
    
    total_flat_points = child_plus_points
    st.metric("フラット35ポイント", f"{total_flat_points}pt")

# フラット35金利スケジュール生成
def generate_flat35_schedule(base_rate, total_points, loan_years):
    if total_points <= 2:
        discount_1_5 = total_points * 0.25
        discount_6_10 = 0
    elif total_points == 3:
        discount_1_5 = 0.75
        discount_6_10 = 0
    elif total_points == 4:
        discount_1_5 = 1.00
        discount_6_10 = 0
    else:
        discount_1_5 = 1.00
        discount_6_10 = 0.25
    
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

# テーブル初期化
if 'complete_table' not in st.session_state:
    row_items = [
        "【家族構成】",
        "西暦",
        "夫 年齢",
        "妻 年齢"
    ]
    
    for i in range(children_count):
        row_items.append(f"第{i+1}子 年齢")
    
    row_items.extend([
        "家族人数",
        "世帯年収",
        "",
        "【変動金利】",
        "適用金利(%)",
        "月額返済(万円)",
        "年間返済(万円)", 
        "うち元金(万円)",
        "うち利息(万円)",
        "ローン残債(万円)",
        "",
        "【固定金利】", 
        "適用金利(%)",
        "月額返済(万円)",
        "年間返済(万円)",
        "うち元金(万円)", 
        "うち利息(万円)",
        "ローン残債(万円)",
        "",
        "【賃貸】",
        "月額家賃(万円)",
        "年間家賃(万円)",
        "更新料等(万円)",
        "賃貸年間総額(万円)"
    ])
    
    year_columns = ["項目"] + [f"{y}年目" for y in range(1, 61)]
    
    st.session_state.complete_table = pd.DataFrame(
        index=range(len(row_items)),
        columns=year_columns
    )
    st.session_state.complete_table["項目"] = row_items
    
    for col in year_columns[1:]:
        st.session_state.complete_table[col] = 0.0

# 変動金利スケジュール初期化
if 'variable_rates' not in st.session_state:
    st.session_state.variable_rates = [actual_variable_base] * 60
    st.session_state.last_loan_years = loan_years
    st.session_state.last_base_rate = actual_variable_base

if ('last_loan_years' not in st.session_state or 
    st.session_state.last_loan_years != loan_years or
    abs(st.session_state.last_base_rate - actual_variable_base) > 1e-9):
    
    st.session_state.variable_rates = [actual_variable_base] * 60
    st.session_state.last_loan_years = loan_years
    st.session_state.last_base_rate = actual_variable_base
    st.success(f"🔄 金利スケジュール自動更新：{actual_variable_base:.2f}%")

# 計算エンジン
def calculate_complete_schedule(loan_amount_man, loan_years, rate_list):
    remaining_balance = loan_amount_man * 10000
    schedule = []
    
    for year in range(1, 61):
        if year <= loan_years and remaining_balance > 0:
            current_rate = rate_list[year - 1] / 100
            monthly_rate = current_rate / 12
            remaining_months = (loan_years - year + 1) * 12
            
            if monthly_rate == 0:
                monthly_payment = remaining_balance / remaining_months
            else:
                monthly_payment = abs(npf.pmt(monthly_rate, remaining_months, remaining_balance))
            
            annual_principal = 0
            annual_interest = 0
            
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
                "rate": current_rate * 100,
                "monthly_payment": monthly_payment / 10000,
                "annual_payment": (annual_principal + annual_interest) / 10000,
                "annual_principal": annual_principal / 10000,
                "annual_interest": annual_interest / 10000,
                "balance": remaining_balance / 10000
            })
        else:
            schedule.append({
                "rate": 0, "monthly_payment": 0, "annual_payment": 0,
                "annual_principal": 0, "annual_interest": 0, "balance": 0
            })
    return schedule

variable_schedule = calculate_complete_schedule(required_loan, loan_years, st.session_state.variable_rates)
flat_schedule = calculate_complete_schedule(required_loan, loan_years, flat_rate_schedule)

# テーブルデータ投入
for year in range(1, 61):
    col_name = f"{year}年目"
    
    # 家族情報計算
    current_year_ad = start_year + year - 1
    husband_age_year = husband_age + year - 1
    wife_age_year = wife_age + year - 1
    
    children_ages_year = []
    children_living = 0
    
    for birth_year in children_birth_years:
        if birth_year <= 0:
            current_age = abs(birth_year)
            child_age = current_age + year - 1
        else:
            if year < birth_year:
                child_age = "未誕生"
            else:
                child_age = year - birth_year
        
        if isinstance(child_age, int) and 0 <= child_age < 18:
            children_living += 1
            children_ages_year.append(child_age)
        elif isinstance(child_age, int) and child_age >= 18:
            children_ages_year.append(f"{child_age}(独立)")
        else:
            children_ages_year.append(child_age)
    
    family_size = 2 + children_living
    
    # 賃貸データ
    rent_monthly = rent_schedule[year - 1]
    rent_annual = rent_monthly * 12
    renewal_cost = rent_monthly * renewal_fee if year % 2 == 0 else 0
    rent_total = rent_annual + renewal_cost
    
    var_data = variable_schedule[year - 1]
    flat_data = flat_schedule[year - 1]
    
    # データ書き込み
    row_index = 0
    st.session_state.complete_table.at[row_index, col_name] = ""; row_index += 1
    st.session_state.complete_table.at[row_index, col_name] = current_year_ad; row_index += 1
    st.session_state.complete_table.at[row_index, col_name] = husband_age_year; row_index += 1
    st.session_state.complete_table.at[row_index, col_name] = wife_age_year; row_index += 1
    
    for i in range(children_count):
        if i < len(children_ages_year):
            st.session_state.complete_table.at[row_index, col_name] = children_ages_year[i]
        else:
            st.session_state.complete_table.at[row_index, col_name] = "未誕生"
        row_index += 1
    
    st.session_state.complete_table.at[row_index, col_name] = family_size; row_index += 1
    st.session_state.complete_table.at[row_index, col_name] = household_income; row_index += 1
    st.session_state.complete_table.at[row_index, col_name] = ""; row_index += 1
    
    st.session_state.complete_table.at[row_index, col_name] = ""; row_index += 1
    st.session_state.complete_table.at[row_index, col_name] = var_data["rate"]; row_index += 1
    st.session_state.complete_table.at[row_index, col_name] = var_data["monthly_payment"]; row_index += 1
    st.session_state.complete_table.at[row_index, col_name] = var_data["annual_payment"]; row_index += 1
    st.session_state.complete_table.at[row_index, col_name] = var_data["annual_principal"]; row_index += 1
    st.session_state.complete_table.at[row_index, col_name] = var_data["annual_interest"]; row_index += 1
    st.session_state.complete_table.at[row_index, col_name] = var_data["balance"]; row_index += 1
    st.session_state.complete_table.at[row_index, col_name] = ""; row_index += 1
    
    st.session_state.complete_table.at[row_index, col_name] = ""; row_index += 1
    st.session_state.complete_table.at[row_index, col_name] = flat_data["rate"]; row_index += 1
    st.session_state.complete_table.at[row_index, col_name] = flat_data["monthly_payment"]; row_index += 1
    st.session_state.complete_table.at[row_index, col_name] = flat_data["annual_payment"]; row_index += 1
    st.session_state.complete_table.at[row_index, col_name] = flat_data["annual_principal"]; row_index += 1
    st.session_state.complete_table.at[row_index, col_name] = flat_data["annual_interest"]; row_index += 1
    st.session_state.complete_table.at[row_index, col_name] = flat_data["balance"]; row_index += 1
    st.session_state.complete_table.at[row_index, col_name] = ""; row_index += 1
    
    st.session_state.complete_table.at[row_index, col_name] = ""; row_index += 1
    st.session_state.complete_table.at[row_index, col_name] = rent_monthly; row_index += 1
    st.session_state.complete_table.at[row_index, col_name] = rent_annual; row_index += 1
    st.session_state.complete_table.at[row_index, col_name] = renewal_cost; row_index += 1
    st.session_state.complete_table.at[row_index, col_name] = rent_total

# 金利編集機能
st.markdown("### 🛠 変動金利スケジュール編集")

col_info, col_reset = st.columns([3, 1])
with col_info:
    if loan_years >= 36:
        st.info(f"📌 超長期ローン（{loan_years}年）全期間+0.10%適用中")
    st.success(f"✅ 現在の金利：{actual_variable_base:.2f}%")

with col_reset:
    st.markdown("#### ")
    if st.button("🔄 金利リセット", use_container_width=True):
        st.session_state.variable_rates = [actual_variable_base] * 60
        st.success("リセット完了")
        st.rerun()

st.caption("💡 **Excelライク：金利変更すると以降すべて同じ金利に自動変更**")

rate_edit_df = pd.DataFrame(
    [st.session_state.variable_rates], 
    columns=[f"{y}年目" for y in range(1, 61)],
    index=["変動金利(%)"]
)

edited_rates = st.data_editor(
    rate_edit_df,
    column_config={
        f"{y}年目": st.column_config.NumberColumn(
            f"{y}年目",
            help=f"{y}年目以降を一括変更",
            min_value=0.0,
            max_value=10.0,
            step=0.01,
            format="%.2f"
        ) for y in range(1, 61)
    },
    use_container_width=True,
    height=120,
    key="rate_editor"
)

if not edited_rates.equals(rate_edit_df):
    new_rates = edited_rates.iloc[0].tolist()
    old_rates = st.session_state.variable_rates
    
    changed_year_index = None
    for i in range(60):
        if abs(new_rates[i] - old_rates[i]) > 1e-9:
            changed_year_index = i
            break
    
    if changed_year_index is not None:
        changed_rate = new_rates[changed_year_index]
        for i in range(changed_year_index, 60):
            st.session_state.variable_rates[i] = changed_rate
        
        st.success(f"✅ {changed_year_index + 1}年目以降を {changed_rate:.2f}% に変更")
        st.balloons()
        st.rerun()

# テーブル表示
st.markdown("### 📊 60年完全統合テーブル")
st.caption("💡 横スクロールで家族年齢と住居費推移を同時確認")

display_table = st.session_state.complete_table.copy()

for col in display_table.columns[1:]:
    for idx in display_table.index:
        value = display_table.at[idx, col]
        item_name = display_table.at[idx, "項目"]
        
        if isinstance(value, str):
            continue
        
        if item_name in ["", "【家族構成】", "【変動金利】", "【固定金利】", "【賃貸】"]:
            continue
        
        if isinstance(value, (int, float)):
            if value == 0 and "適用金利" not in item_name and "年齢" not in item_name and item_name != "西暦":
                display_table.at[idx, col] = ""
            elif "適用金利" in item_name:
                display_table.at[idx, col] = f"{value:.2f}"
            elif "年齢" in item_name or item_name in ["家族人数", "西暦"]:
                display_table.at[idx, col] = f"{int(value)}" if value > 0 else ""
            elif item_name == "世帯年収":
                display_table.at[idx, col] = f"{int(value)}"
            else:
                display_table.at[idx, col] = f"{value:,.1f}" if value > 0 else ""

st.dataframe(
    display_table,
    use_container_width=True,
    height=800,
    hide_index=True
)

# サマリー
st.markdown("### 📋 60年総コスト比較")
col_sum1, col_sum2, col_sum3 = st.columns(3)

total_var_cost = sum(data["annual_payment"] for data in variable_schedule)
total_flat_cost = sum(data["annual_payment"] for data in flat_schedule)
total_rent_cost = sum(rent_schedule[i] * 12 + (rent_schedule[i] * renewal_fee if (i+1) % 2 == 0 else 0) for i in range(60))

with col_sum1:
    st.metric("変動金利 60年総額", f"{total_var_cost:,.0f}万円")

with col_sum2:
    st.metric("固定金利 60年総額", f"{total_flat_cost:,.0f}万円")

with col_sum3:
    st.metric("賃貸 60年総額", f"{total_rent_cost:,.0f}万円")

# 待機コスト判定
st.markdown("---")
st.markdown("## ⏰ 「今は時期じゃない」対策（待機コスト判定）")

wait_years = st.number_input("何年待つ予定ですか？", min_value=1, max_value=10, value=2)

rent_loss = current_rent * 12 * wait_years
first_year_principal = variable_schedule[0]["annual_principal"]
principal_loss = first_year_principal * wait_years
deduction_loss = 28 * wait_years

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
