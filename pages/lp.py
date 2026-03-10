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

# ==========================================
# 1-2. 子供情報（独立計画対応版）
# ==========================================
st.markdown("---")
st.markdown("### 👶 子供情報（独立計画設定対応）")
st.caption("💡 各子供の誕生時期と独立時期を詳細に設定できます")

children_count = st.number_input("子供人数（予定含む）", min_value=0, max_value=5, value=2, help="将来の予定も含めた合計人数")

# 子供データの構造体リスト
children_data = []

if children_count > 0:
    cols = st.columns(min(children_count, 5))
    for i in range(children_count):
        with cols[i]:
            st.markdown(f"#### 第{i+1}子")
            
            # 誕生状況
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
                    min_value=0, max_value=30, 
                    value=2 if i == 0 else 0, 
                    key=f"child_age_{i}"
                )
                birth_year_offset = -current_age
                st.success(f"✅ 現在{current_age}歳")
            else:
                years_until_birth = st.number_input(
                    "何年後に誕生予定？",
                    min_value=1, max_value=20, 
                    value=2 if i == 1 else (2 * i), 
                    key=f"child_future_{i}"
                )
                birth_year_offset = years_until_birth
                st.info(f"📅 {years_until_birth}年後に誕生予定")
            
            # 🔑 新機能：独立時期設定
            st.markdown("---")
            st.markdown("**🏠 独立計画**")
            independence_option = st.selectbox(
                "いつ家を出る？",
                options=[
                    "18歳（大学から一人暮らし）",
                    "22歳（就職後すぐ独立）",
                    "25歳（数年間は実家から通勤）", 
                    "30歳（長期間同居）",
                    "ずっと同居"
                ],
                index=1,  # デフォルトは22歳
                key=f"child_indep_{i}"
            )
            
            # 独立年齢を数値に変換
            if "18歳" in independence_option:
                independence_age = 18
                st.caption("🎓 大学から一人暮らし想定")
            elif "22歳" in independence_option:
                independence_age = 22
                st.caption("💼 就職後すぐに独立")
            elif "25歳" in independence_option:
                independence_age = 25
                st.caption("🏢 数年間実家から通勤")
            elif "30歳" in independence_option:
                independence_age = 30
                st.caption("🏡 長期間同居")
            else:  # ずっと同居
                independence_age = 999
                st.caption("👨‍👩‍👧‍👦 生涯同居想定")
            
            # データ保存
            children_data.append({
                "birth_year_offset": birth_year_offset,
                "independence_age": independence_age
            })

    # 家族計画サマリー
    st.markdown("---")
    st.markdown("#### 📋 家族計画サマリー")
    summary_parts = []
    for i, child in enumerate(children_data):
        if child["birth_year_offset"] <= 0:
            age = abs(child["birth_year_offset"])
            status = f"現在{age}歳"
        else:
            status = f"{child['birth_year_offset']}年後誕生"
        
        if child["independence_age"] < 999:
            indep_text = f"{child['independence_age']}歳独立"
        else:
            indep_text = "ずっと同居"
        
        summary_parts.append(f"第{i+1}子：{status}（{indep_text}）")
    
    st.write(" / ".join(summary_parts))
else:
    st.info("💑 子供なし（DINKS）として計算します")

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
    if years <= 0: return 0
    monthly_rate = SCREENING_RATE / 12
    n_months = years * 12
    return monthly_repayment_capacity * ((1 - (1 + monthly_rate)**(-n_months)) / monthly_rate)

max_loan_35 = calculate_max_loan_amount(35)
max_loan_max = calculate_max_loan_amount(max_loan_years)

col_loan1, col_loan2, col_loan3 = st.columns(3)
with col_loan1: st.metric("35年返済での借入可能額", f"{max_loan_35/10000:,.0f}万円")
with col_loan2: st.metric(f"最長{max_loan_years}年返済での借入可能額", f"{max_loan_max/10000:,.0f}万円")
with col_loan3: st.metric("月額返済可能額", f"{monthly_repayment_capacity/10000:,.1f}万円")

# ==========================================
# 3. 物件・資金計画
# ==========================================
st.markdown("---")
st.markdown("## 🏠 物件・資金計画")

def reset_loan_conditions():
    keys_to_reset = ['variable_rates', 'complete_table', 'last_loan_years', 'last_base_rate', 'last_children_data']
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]

col_prop1, col_prop2 = st.columns(2)

with col_prop1:
    property_price = st.number_input("物件価格（万円）", min_value=100, value=6000, step=100)
    self_funds = st.number_input("自己資金（万円）", min_value=0, value=500, step=50)
    
    loan_years = st.number_input(
        "希望借入年数", 
        min_value=1, max_value=max_loan_years, 
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
# 4. 賃貸プラン設定（家族構成連動）
# ==========================================
st.markdown("---")
st.markdown("## 🏠 賃貸プラン設定（家族構成連動）")

col_rent1, col_rent2, col_rent3 = st.columns(3)

with col_rent1:
    st.markdown("### 夫婦のみ（2LDK）")
    rent_couple = st.number_input("月額家賃（万円）", min_value=0.0, value=12.0, step=0.5, key="rent_2ldk")
    renewal_fee = st.number_input("更新料（ヶ月分/2年毎）", min_value=0.0, value=1.0, step=0.5)

with col_rent2:
    st.markdown("### 子供1-2人（3LDK）")
    rent_family_3 = st.number_input("月額家賃（万円）", min_value=0.0, value=18.0, step=0.5, key="rent_3ldk")

with col_rent3:
    st.markdown("### 子供3人以上（4LDK）")
    rent_family_4 = st.number_input("月額家賃（万円）", min_value=0.0, value=22.0, step=0.5, key="rent_4ldk")

# ==========================================
# 5. 60年完全比較テーブル（独立計画対応版）
# ==========================================
st.markdown("---")
st.markdown("## 📊 60年完全比較テーブル（独立計画連動）")

# 子供データ変更検知
if 'last_children_data' not in st.session_state:
    st.session_state.last_children_data = children_data

if st.session_state.last_children_data != children_data:
    if 'complete_table' in st.session_state:
        del st.session_state.complete_table
    st.session_state.last_children_data = children_data
    st.info("🔄 子供の独立計画変更を検知し、テーブルを再構築しました")

# 基準金利設定
col_rate1, col_rate2, col_rate3 = st.columns(3)

with col_rate1:
    base_rate_variable = st.number_input(
        "変動金利 基準（%）", 
        min_value=0.0, max_value=10.0, value=0.6, step=0.01, format="%.2f",
        on_change=reset_loan_conditions
    )
    if loan_years >= 36:
        actual_variable_base = base_rate_variable + 0.1
        st.warning(f"⚠️ 超長期ローン（{loan_years}年）全期間+0.10%")
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
        st.warning(f"⚠️ 超長期ローン（{loan_years}年）全期間+0.10%")
        st.info(f"実際の金利：**{actual_flat_base:.2f}%**")
    else:
        actual_flat_base = base_rate_flat
        st.success(f"✅ 基準金利：{actual_flat_base:.2f}%")

with col_rate3:
    # フラット35ポイント計算
    current_children_under18 = 0
    for child in children_data:
        birth_year_offset = child["birth_year_offset"]
        if birth_year_offset <= 0:
            current_age = abs(birth_year_offset)
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
        "必要間取り",
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
        "【賃貸（家族連動）】",
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
                if remaining_balance <= 0: break
                monthly_interest = remaining_balance * monthly_rate
                monthly_principal = monthly_payment - monthly_interest
                if monthly_principal > remaining_balance: monthly_principal = remaining_balance
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

# 項目名から行インデックスを取得する関数
def get_row_index(item_name, occurrence=0):
    try:
        matching_indices = st.session_state.complete_table[
            st.session_state.complete_table["項目"] == item_name
        ].index.tolist()
        if len(matching_indices) > occurrence:
            return matching_indices[occurrence]
        return None
    except Exception:
        return None

# データ投入（独立計画対応）
for year in range(1, 61):
    col_name = f"{year}年目"
    
    # 家族情報計算
    current_year_ad = start_year + year - 1
    husband_age_year = husband_age + year - 1
    wife_age_year = wife_age + year - 1
    
    children_ages_year = []
    children_living = 0
    
    # 🔑 独立計画に基づく家族構成計算
    for child in children_data:
        birth_year_offset = child["birth_year_offset"]
        independence_age = child["independence_age"]
        
        # 年齢計算
        if birth_year_offset <= 0:
            current_age = abs(birth_year_offset)
            child_age = current_age + year - 1
        else:
            if year < birth_year_offset:
                child_age = "未誕生"
            else:
                child_age = year - birth_year_offset
        
        # 独立判定と表示
        if isinstance(child_age, int):
            if child_age < 0:
                child_display = "未誕生"
            elif child_age < independence_age:
                # 独立年齢未満なら同居
                children_living += 1
                child_display = child_age
            else:
                # 独立年齢以上なら独立
                child_display = f"{child_age}(独立)"
        else:
            child_display = child_age
        
        children_ages_year.append(child_display)
    
    family_size = 2 + children_living
    
    # 🔑 家族人数に基づく間取りと家賃決定
    if children_living == 0:
        required_layout = "2LDK"
        monthly_rent = rent_couple
    elif children_living <= 2:
        required_layout = "3LDK"
        monthly_rent = rent_family_3
    else:
        required_layout = "4LDK"
        monthly_rent = rent_family_4
    
    rent_annual = monthly_rent * 12
    renewal_cost = monthly_rent * renewal_fee if year % 2 == 0 else 0
    rent_total = rent_annual + renewal_cost
    
    var_data = variable_schedule[year - 1]
    flat_data = flat_schedule[year - 1]
    
    # テーブルデータ書き込み
    idx = get_row_index("【家族構成】")
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = ""
    
    idx = get_row_index("西暦")
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = current_year_ad
    
    idx = get_row_index("夫 年齢")
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = husband_age_year
    
    idx = get_row_index("妻 年齢")
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = wife_age_year
    
    for i in range(children_count):
        idx = get_row_index(f"第{i+1}子 年齢")
        if idx is not None:
            if i < len(children_ages_year):
                st.session_state.complete_table.at[idx, col_name] = children_ages_year[i]
            else:
                st.session_state.complete_table.at[idx, col_name] = "未誕生"
    
    idx = get_row_index("家族人数")
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = family_size
    
    idx = get_row_index("必要間取り")
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = required_layout
    
    idx = get_row_index("世帯年収")
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = household_income
    
    # 変動金利データ
    idx = get_row_index("【変動金利】")
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = ""
    
    idx = get_row_index("適用金利(%)", 0)
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = var_data["rate"]
    
    idx = get_row_index("月額返済(万円)", 0)
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = var_data["monthly_payment"]
    
    idx = get_row_index("年間返済(万円)", 0)
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = var_data["annual_payment"]
    
    idx = get_row_index("うち元金(万円)", 0)
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = var_data["annual_principal"]
    
    idx = get_row_index("うち利息(万円)", 0)
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = var_data["annual_interest"]
    
    idx = get_row_index("ローン残債(万円)", 0)
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = var_data["balance"]
    
    # 固定金利データ
    idx = get_row_index("【固定金利】")
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = ""
    
    idx = get_row_index("適用金利(%)", 1)
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = flat_data["rate"]
    
    idx = get_row_index("月額返済(万円)", 1)
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = flat_data["monthly_payment"]
    
    idx = get_row_index("年間返済(万円)", 1)
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = flat_data["annual_payment"]
    
    idx = get_row_index("うち元金(万円)", 1)
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = flat_data["annual_principal"]
    
    idx = get_row_index("うち利息(万円)", 1)
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = flat_data["annual_interest"]
    
    idx = get_row_index("ローン残債(万円)", 1)
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = flat_data["balance"]
    
    # 賃貸データ
    idx = get_row_index("【賃貸（家族連動）】")
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = ""
    
    idx = get_row_index("月額家賃(万円)")
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = monthly_rent
    
    idx = get_row_index("年間家賃(万円)")
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = rent_annual
    
    idx = get_row_index("更新料等(万円)")
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = renewal_cost
    
    idx = get_row_index("賃貸年間総額(万円)")
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = rent_total

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
st.caption("💡 横スクロールで家族構成の変化と住居費推移を同時確認")

display_table = st.session_state.complete_table.copy()

for col in display_table.columns[1:]:
    for idx in display_table.index:
        try:
            value = display_table.at[idx, col]
            item_name = display_table.at[idx, "項目"]
            
            if not isinstance(item_name, str): continue
            if isinstance(value, str): continue
            
            if item_name in ["", "【家族構成】", "【変動金利】", "【固定金利】", "【賃貸（家族連動）】"]: continue
            
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
        except:
            continue

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

# 賃貸総額の再計算（家族連動）
total_rent_cost_linked = 0
for year in range(1, 61):
    col_name = f"{year}年目"
    idx_rent = get_row_index("賃貸年間総額(万円)")
    if idx_rent is not None:
        val = st.session_state.complete_table.at[idx_rent, col_name]
        if isinstance(val, (int, float)):
            total_rent_cost_linked += val

with col_sum1: st.metric("変動金利 60年総額", f"{total_var_cost:,.0f}万円")
with col_sum2: st.metric("固定金利 60年総額", f"{total_flat_cost:,.0f}万円")
with col_sum3: st.metric("賃貸 60年総額", f"{total_rent_cost_linked:,.0f}万円")

# 待機コスト判定
st.markdown("---")
st.markdown("## ⏰ 「今は時期じゃない」対策（待機コスト判定）")

wait_years = st.number_input("何年待つ予定ですか？", min_value=1, max_value=10, value=2)

rent_loss = rent_couple * 12 * wait_years + (rent_couple * renewal_fee * (wait_years // 2))
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
