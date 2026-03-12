import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
from datetime import datetime

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
# 管理者機能（パスワード変更）
# ==========================================
if 'customer_password' not in st.session_state:
    st.session_state.customer_password = "terassnishiyama"
if 'password_history' not in st.session_state:
    st.session_state.password_history = []
if 'admin_authenticated' not in st.session_state:
    st.session_state.admin_authenticated = False
if 'user_authenticated' not in st.session_state:
    st.session_state.user_authenticated = False

query_params = st.query_params
is_admin_mode = query_params.get("admin") == "1"

if is_admin_mode:
    st.markdown("# 🔐 管理者専用ページ")
    st.markdown("---")
    
    if not st.session_state.admin_authenticated:
        admin_password = st.text_input("管理者パスワードを入力", type="password", key="admin_pw")
        if st.button("ログイン", type="primary"):
            if admin_password == "naoki0709":
                st.session_state.admin_authenticated = True
                st.success("✅ 認証成功")
                st.rerun()
            else:
                st.error("❌ パスワードが違います")
        st.stop()
    
    st.success("✅ 管理者認証完了")
    st.markdown("---")
    st.markdown("## 📊 ツールアクセス管理")
    
    col_admin1, col_admin2 = st.columns(2)
    
    with col_admin1:
        st.metric("現在のお客様用パスワード", st.session_state.customer_password)
        if st.session_state.password_history:
            last_change = st.session_state.password_history[-1]
            st.caption(f"最終変更：{last_change}")
    
    with col_admin2:
        new_password = st.text_input("新しいパスワード", key="new_pw")
        if st.button("🔄 パスワード変更", type="primary"):
            if new_password and len(new_password) >= 4:
                st.session_state.customer_password = new_password
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                st.session_state.password_history.append(f"{timestamp} - {new_password}")
                st.success(f"✅ パスワードを変更しました：{new_password}")
                st.info("💡 この新パスワードをLステップで配信してください")
                st.balloons()
            else:
                st.error("❌ 4文字以上のパスワードを入力してください")
    
    st.markdown("---")
    st.markdown("### 📋 変更履歴")
    if st.session_state.password_history:
        for record in reversed(st.session_state.password_history[-10:]):
            st.text(record)
    else:
        st.caption("まだ変更履歴はありません")
    
    if st.button("🚪 ログアウト"):
        st.session_state.admin_authenticated = False
        st.rerun()
    st.stop()

# ==========================================
# お客様用パスワード認証
# ==========================================
if not st.session_state.user_authenticated:
    st.markdown("<h1 style='text-align:center;'>🔐 ライフプランツール</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>公式LINE登録者専用</p>", unsafe_allow_html=True)
    
    col_auth1, col_auth2, col_auth3 = st.columns([1, 2, 1])
    with col_auth2:
        password_input = st.text_input("パスワードを入力してください", type="password")
        if st.button("ログイン", type="primary", use_container_width=True):
            if password_input == st.session_state.customer_password:
                st.session_state.user_authenticated = True
                st.success("✅ 認証成功")
                st.rerun()
            else:
                st.error("❌ パスワードが正しくありません")
    st.stop()

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
    st.markdown("### ご主人")
    husband_age = st.number_input("現在年齢（歳）", min_value=20, max_value=70, value=32, key="husband_age")
    
    col_h_sal, col_h_grow = st.columns([2, 1])
    with col_h_sal:
        husband_salary = st.number_input("現在の年収（万円）", min_value=0, value=600, step=10, key="husband_salary")
    with col_h_grow:
        husband_growth = st.number_input("上昇率(%)", min_value=0.0, max_value=10.0, value=2.0, step=0.1, key="husband_growth")
    
    husband_retirement = st.number_input("定年年齢（歳）", min_value=50, max_value=80, value=65, key="husband_retire")

with col2:
    st.markdown("### 奥様")
    wife_age = st.number_input("現在年齢（歳）", min_value=20, max_value=70, value=30, key="wife_age")
    
    col_w_sal, col_w_grow = st.columns([2, 1])
    with col_w_sal:
        wife_salary = st.number_input("現在の年収（万円）", min_value=0, value=200, step=10, key="wife_salary")
    with col_w_grow:
        wife_growth = st.number_input("上昇率(%)", min_value=0.0, max_value=10.0, value=1.5, step=0.1, key="wife_growth")
    
    wife_retirement = st.number_input("定年年齢（歳）", min_value=50, max_value=80, value=65, key="wife_retire")

with col3:
    st.markdown("### その他・設定")
    stock_income = st.number_input("株式配当・その他収入（年額・万円）", min_value=0, value=0, step=10, help="※住宅ローンの借入計算には含まれません")
    start_year = st.number_input("シミュレーション開始年", min_value=2020, max_value=2030, value=2026)

# 年金計算関数
def calculate_pension(average_salary):
    employee_pension = average_salary * 0.18  # 厚生年金係数0.18
    national_pension = 80  # 国民年金80万円
    return employee_pension + national_pension

def calculate_average_working_salary(current_salary, growth_rate, current_age, retirement_age):
    working_years = max(1, retirement_age - current_age)
    total = 0
    for i in range(working_years):
        salary = current_salary * ((1 + growth_rate / 100) ** i)
        total += salary
    return total / working_years

husband_avg_salary = calculate_average_working_salary(husband_salary, husband_growth, husband_age, husband_retirement)
wife_avg_salary = calculate_average_working_salary(wife_salary, wife_growth, wife_age, wife_retirement)

husband_pension = calculate_pension(husband_avg_salary)
wife_pension = calculate_pension(wife_avg_salary)

# 借入計算用年収（その他収入を除外）
loan_calculation_income = husband_salary + wife_salary

# ==========================================
# 借入可能額自動計算
# ==========================================
st.markdown("---")
st.markdown("### 💰 借入可能額判定")

SCREENING_RATE = 0.03
REPAYMENT_RATIO = 0.40
MAX_COMPLETION_AGE = 79

annual_repayment_capacity = loan_calculation_income * 10000 * REPAYMENT_RATIO
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
with col_loan1: 
    st.metric("借入計算用年収", f"{loan_calculation_income:,.0f}万円")
    st.caption("※給与のみ（その他収入除外）")
with col_loan2: 
    st.metric("35年返済での借入可能額", f"{max_loan_35/10000:,.0f}万円")
with col_loan3: 
    st.metric(f"最長{max_loan_years}年返済での借入可能額", f"{max_loan_max/10000:,.0f}万円")

# ==========================================
# 1-2. 子供情報
# ==========================================
st.markdown("---")
st.markdown("### 👶 子供情報（独立計画設定対応）")

children_count = st.number_input("子供人数（予定含む）", min_value=0, max_value=5, value=2)

children_data = []

if children_count > 0:
    cols = st.columns(min(children_count, 5))
    for i in range(children_count):
        with cols[i]:
            st.markdown(f"#### 第{i+1}子")
            
            birth_status = st.radio(
                "状況",
                options=["既に誕生済み", "将来の予定"],
                index=0 if i == 0 else 1,
                key=f"child_status_{i}",
                label_visibility="collapsed"
            )
            
            if birth_status == "既に誕生済み":
                current_age = st.number_input("現在の年齢（歳）", min_value=0, max_value=30, value=2 if i == 0 else 0, key=f"child_age_{i}")
                birth_year_offset = -current_age
            else:
                years_until_birth = st.number_input("何年後に誕生予定？", min_value=1, max_value=20, value=2 if i == 1 else (2 * i), key=f"child_future_{i}")
                birth_year_offset = years_until_birth
            
            st.markdown("**🏠 独立計画**")
            independence_option = st.selectbox(
                "いつ家を出る？",
                options=["18歳", "22歳", "25歳", "30歳", "ずっと同居"],
                index=1,
                key=f"child_indep_{i}"
            )
            
            if "18歳" in independence_option: independence_age = 18
            elif "22歳" in independence_option: independence_age = 22
            elif "25歳" in independence_option: independence_age = 25
            elif "30歳" in independence_option: independence_age = 30
            else: independence_age = 999
            
            children_data.append({
                "birth_year_offset": birth_year_offset,
                "independence_age": independence_age
            })
else:
    st.info("💑 子供なし（DINKS）として計算します")

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
    property_type = st.radio(
        "物件種別",
        options=["マンション", "戸建て（新築）"],
        horizontal=True,
        key="property_type"
    )
    
    property_price = st.number_input("物件価格（万円）", min_value=100, value=6000, step=100)
    self_funds = st.number_input("自己資金（万円）", min_value=0, value=500, step=50)
    
    loan_years = st.number_input(
        "希望借入年数", 
        min_value=1, max_value=max_loan_years, 
        value=min(35, max_loan_years),
        on_change=reset_loan_conditions
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
# 物件価値シミュレーション
# ==========================================
st.markdown("---")
st.markdown("## 📈 物件価値シミュレーション")

if property_type == "戸建て（新築）":
    st.info("🏡 **新築戸建て**：土地と建物を分けて評価します")
    
    land_price = property_price * 0.60
    building_price = property_price * 0.40
    
    col_split1, col_split2 = st.columns(2)
    with col_split1:
        st.metric("土地価格", f"{land_price:,.0f}万円", "60%")
    with col_split2:
        st.metric("建物価格", f"{building_price:,.0f}万円", "40%")
    
    st.markdown("#### 📊 価格推移予測")
    
    building_1y_low, building_1y_high = 0.85, 0.90
    building_2y_low, building_2y_high = 0.80, 0.85
    land_1y_low, land_1y_high = 0.96, 1.00
    land_2y_low, land_2y_high = 0.94, 0.98
    
    land_1_low = land_price * land_1y_low
    land_1_high = land_price * land_1y_high
    building_1_low = building_price * building_1y_low
    building_1_high = building_price * building_1y_high
    total_1_low = land_1_low + building_1_low
    total_1_high = land_1_high + building_1_high
    
    land_2_low = land_price * land_2y_low
    land_2_high = land_price * land_2y_high
    building_2_low = building_price * building_2y_low
    building_2_high = building_price * building_2y_high
    total_2_low = land_2_low + building_2_low
    total_2_high = land_2_high + building_2_high
    
    price_table = pd.DataFrame({
        "項目": ["土地", "建物", "合計", "全体係数"],
        "購入時": [f"{land_price:,.0f}万円", f"{building_price:,.0f}万円", f"{property_price:,.0f}万円", "1.000"],
        "1年後（下限）": [f"{land_1_low:,.0f}万円", f"{building_1_low:,.0f}万円", f"{total_1_low:,.0f}万円", f"{total_1_low/property_price:.3f}"],
        "1年後（上限）": [f"{land_1_high:,.0f}万円", f"{building_1_high:,.0f}万円", f"{total_1_high:,.0f}万円", f"{total_1_high/property_price:.3f}"],
        "2年後（下限）": [f"{land_2_low:,.0f}万円", f"{building_2_low:,.0f}万円", f"{total_2_low:,.0f}万円", f"{total_2_low/property_price:.3f}"],
        "2年後（上限）": [f"{land_2_high:,.0f}万円", f"{building_2_high:,.0f}万円", f"{total_2_high:,.0f}万円", f"{total_2_high/property_price:.3f}"]
    })
    
    st.dataframe(price_table, use_container_width=True, hide_index=True)
    
    def calculate_property_value(year_index):
        if year_index == 0:
            return property_price
        
        if year_index == 1:
            building_coef = (building_1y_low + building_1y_high) / 2
        elif year_index == 2:
            building_coef = (building_2y_low + building_2y_high) / 2
        else:
            building_coef = ((building_2y_low + building_2y_high) / 2) * (0.985 ** (year_index - 2))
        
        if year_index == 1:
            land_coef = (land_1y_low + land_1y_high) / 2
        elif year_index == 2:
            land_coef = (land_2y_low + land_2y_high) / 2
        else:
            land_coef = ((land_2y_low + land_2y_high) / 2) * (0.995 ** (year_index - 2))
        
        building_value = building_price * max(0.1, building_coef)
        land_value = land_price * max(0.8, land_coef)
        
        return building_value + land_value

else:
    st.info("🏢 **マンション**：建物全体として評価します")
    
    def calculate_property_value(year_index):
        if year_index == 0:
            return property_price
        elif year_index == 1:
            return property_price * 0.90
        elif year_index <= 5:
            return property_price * (0.90 - (year_index - 1) * 0.02)
        elif year_index <= 15:
            return property_price * (0.82 - (year_index - 5) * 0.015)
        else:
            return property_price * max(0.50, 0.67 - (year_index - 15) * 0.01)

# ==========================================
# 賃貸プラン設定
# ==========================================
st.markdown("---")
st.markdown("## 🏠 賃貸プラン設定")

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
# 60年完全比較テーブル
# ==========================================
st.markdown("---")
st.markdown("## 📊 60年完全比較テーブル")

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

# テーブル初期化（エラー修正版）
if 'complete_table' not in st.session_state:
    row_items = [
        "【家族構成】",
        "西暦",
        "ご主人 年齢",
        "奥様 年齢"
    ]
    
    for i in range(children_count):
        row_items.append(f"第{i+1}子 年齢")
    
    row_items.extend([
        "家族人数",
        "必要間取り",
        "【収入内訳】",
        "ご主人 年収(万円)",
        "奥様 年収(万円)",
        "株式配当・その他(万円)",
        "合計 世帯年収(万円)",
        "【変動金利】",
        "適用金利(%)",
        "月額返済(万円)",
        "年間返済(万円)", 
        "うち元金(万円)",
        "うち利息(万円)",
        "ローン残債(万円)",
        "物件現在価値(万円)",
        "売却損益(万円)",
        "【固定金利】", 
        "適用金利(%)",
        "月額返済(万円)",
        "年間返済(万円)",
        "うち元金(万円)", 
        "うち利息(万円)",
        "ローン残債(万円)",
        "物件現在価値(万円)",
        "売却損益(万円)",
        "【賃貸】",
        "月額家賃(万円)",
        "年間家賃(万円)",
        "更新料等(万円)",
        "賃貸年間総額(万円)",
        "賃貸累計(万円)"
    ])
    
    year_columns = ["項目"] + [f"{y}年目" for y in range(1, 61)]
    
    # 🔑 重要：dtype=objectを明示的に指定（数値・文字列の混在を許可）
    st.session_state.complete_table = pd.DataFrame(
        index=range(len(row_items)),
        columns=year_columns,
        dtype=object
    )
    st.session_state.complete_table["項目"] = row_items
    
    # 年収の初期値設定（定年・年金考慮）
    for year in range(1, 61):
        col_name = f"{year}年目"
        h_age = husband_age + year - 1
        w_age = wife_age + year - 1
        
        # ご主人の収入（定年前は給与、定年後は年金）
        if h_age < husband_retirement:
            h_income = husband_salary * ((1 + husband_growth / 100) ** (year - 1))
        else:
            h_income = husband_pension  # 年金に切り替え
            
        # 奥様の収入（定年前は給与、定年後は年金）
        if w_age < wife_retirement:
            w_income = wife_salary * ((1 + wife_growth / 100) ** (year - 1))
        else:
            w_income = wife_pension  # 年金に切り替え
        
        # 初期値をテーブルに設定
        for idx in st.session_state.complete_table.index:
            item = st.session_state.complete_table.at[idx, "項目"]
            if item == "ご主人 年収(万円)":
                st.session_state.complete_table.at[idx, col_name] = int(h_income)
            elif item == "奥様 年収(万円)":
                st.session_state.complete_table.at[idx, col_name] = int(w_income)
            elif item == "株式配当・その他(万円)":
                st.session_state.complete_table.at[idx, col_name] = stock_income
            elif item == "合計 世帯年収(万円)":
                st.session_state.complete_table.at[idx, col_name] = int(h_income + w_income + stock_income)

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

# データ投入（年収セル以外を更新）
rent_cumulative = 0

for year in range(1, 61):
    col_name = f"{year}年目"
    
    current_year_ad = start_year + year - 1
    husband_age_year = husband_age + year - 1
    wife_age_year = wife_age + year - 1
    
    children_ages_year = []
    children_living = 0
    
    for child in children_data:
        birth_year_offset = child["birth_year_offset"]
        independence_age = child["independence_age"]
        
        if birth_year_offset <= 0:
            current_age = abs(birth_year_offset)
            child_age = current_age + year - 1
        else:
            if year < birth_year_offset:
                child_age = "未誕生"
            else:
                child_age = year - birth_year_offset
        
        if isinstance(child_age, int):
            if child_age < 0:
                child_display = "未誕生"
            elif child_age < independence_age:
                children_living += 1
                child_display = child_age
            else:
                child_display = f"{child_age}(独立)"
        else:
            child_display = child_age
        
        children_ages_year.append(child_display)
    
    family_size = 2 + children_living
    
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
    rent_cumulative += rent_total
    
    # テーブルから年収データを取得（編集済みの値を使用）
    idx_h = get_row_index("ご主人 年収(万円)")
    idx_w = get_row_index("奥様 年収(万円)")
    idx_o = get_row_index("株式配当・その他(万円)")
    
    # 安全な値取得（None対応）
    try:
        husband_income_year = st.session_state.complete_table.at[idx_h, col_name] if idx_h is not None else 0
        if husband_income_year is None:
            husband_income_year = 0
    except:
        husband_income_year = 0
        
    try:
        wife_income_year = st.session_state.complete_table.at[idx_w, col_name] if idx_w is not None else 0
        if wife_income_year is None:
            wife_income_year = 0
    except:
        wife_income_year = 0
        
    try:
        other_income_year = st.session_state.complete_table.at[idx_o, col_name] if idx_o is not None else 0
        if other_income_year is None:
            other_income_year = 0
    except:
        other_income_year = 0
    
    total_income_year = husband_income_year + wife_income_year + other_income_year
    
    property_value = calculate_property_value(year - 1)
    
    var_data = variable_schedule[year - 1]
    flat_data = flat_schedule[year - 1]
    
    var_equity = property_value - var_data["balance"]
    flat_equity = property_value - flat_data["balance"]
    
    # テーブル書き込み（年収セル以外を更新）
    idx = get_row_index("【家族構成】")
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = ""
    
    idx = get_row_index("西暦")
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = current_year_ad
    
    idx = get_row_index("ご主人 年齢")
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = husband_age_year
    
    idx = get_row_index("奥様 年齢")
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
    
    idx = get_row_index("【収入内訳】")
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = ""
    
    # 合計世帯年収のみ再計算
    idx = get_row_index("合計 世帯年収(万円)")
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = total_income_year
    
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
    
    idx = get_row_index("物件現在価値(万円)", 0)
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = property_value
    
    idx = get_row_index("売却損益(万円)", 0)
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = var_equity
    
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
    
    idx = get_row_index("物件現在価値(万円)", 1)
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = property_value
    
    idx = get_row_index("売却損益(万円)", 1)
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = flat_equity
    
    idx = get_row_index("【賃貸】")
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = ""
    
    idx = get_row_index("月額家賃(万円)")
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = monthly_rent
    
    idx = get_row_index("年間家賃(万円)")
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = rent_annual
    
    idx = get_row_index("更新料等(万円)")
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = renewal_cost
    
    idx = get_row_index("賃貸年間総額(万円)")
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = rent_total
    
    idx = get_row_index("賃貸累計(万円)")
    if idx is not None: st.session_state.complete_table.at[idx, col_name] = rent_cumulative

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
    height=80,
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

# テーブル表示（完全編集可能・0.0セル削除対応）
st.markdown("### 📊 60年完全統合テーブル（Excelライク編集）")
st.caption("💡 全てのセルをダブルクリックして直接編集できます（年収・年金・家賃等を自由に調整）")

# 表示用テーブルの作成（0.0セル削除処理）
display_table = st.session_state.complete_table.copy()

for col in display_table.columns[1:]:
    for idx in display_table.index:
        try:
            value = display_table.at[idx, col]
            item_name = display_table.at[idx, "項目"]
            
            if not isinstance(item_name, str): continue
            if isinstance(value, str): continue
            
            # セクションヘッダーは空白に
            if item_name in ["【家族構成】", "【収入内訳】", "【変動金利】", "【固定金利】", "【賃貸】"]: 
                display_table.at[idx, col] = ""
                continue
            
            if isinstance(value, (int, float)):
                if value == 0:
                    # 0でも表示すべき項目
                    if "適用金利" in item_name:
                        display_table.at[idx, col] = f"{value:.2f}"
                    elif item_name in ["家族人数", "西暦"]:
                        display_table.at[idx, col] = f"{int(value)}"
                    elif "年収" in item_name or "収入" in item_name:
                        display_table.at[idx, col] = "0"
                    else:
                        # その他の0値は空白に（0.0セル削除）
                        display_table.at[idx, col] = ""
                else:
                    # 0以外の値の表示フォーマット
                    if "適用金利" in item_name:
                        display_table.at[idx, col] = f"{value:.2f}"
                    elif "年齢" in item_name or item_name in ["家族人数", "西暦"]:
                        display_table.at[idx, col] = f"{int(value)}"
                    elif "年収" in item_name or "収入" in item_name:
                        display_table.at[idx, col] = f"{int(value)}"
                    else:
                        display_table.at[idx, col] = f"{value:,.1f}"
        except:
            continue

# 完全編集可能テーブル
edited_complete_table = st.data_editor(
    display_table,
    use_container_width=True,
    height=800,
    hide_index=True,
    num_rows="fixed",
    key="complete_table_editor"
)

# 編集結果を元のテーブルに反映
for col in edited_complete_table.columns:
    for idx in edited_complete_table.index:
        try:
            edited_value = edited_complete_table.at[idx, col]
            if isinstance(edited_value, str) and edited_value.replace(",", "").replace(".", "").replace("-", "").isdigit():
                # 数値文字列を数値に変換
                numeric_value = float(edited_value.replace(",", ""))
                st.session_state.complete_table.at[idx, col] = numeric_value
            elif isinstance(edited_value, (int, float)):
                st.session_state.complete_table.at[idx, col] = edited_value
            else:
                st.session_state.complete_table.at[idx, col] = edited_value
        except:
            continue

# サマリー
st.markdown("### 📋 60年総コスト比較")
col_sum1, col_sum2, col_sum3, col_sum4 = st.columns(4)

total_var_cost = sum(data["annual_payment"] for data in variable_schedule)
total_flat_cost = sum(data["annual_payment"] for data in flat_schedule)

with col_sum1: st.metric("変動金利 60年総額", f"{total_var_cost:,.0f}万円")
with col_sum2: st.metric("固定金利 60年総額", f"{total_flat_cost:,.0f}万円")
with col_sum3: st.metric("賃貸 60年総額", f"{rent_cumulative:,.0f}万円")
with col_sum4:
    rent_vs_variable = rent_cumulative - total_var_cost
    if rent_vs_variable > 0:
        st.metric("賃貸との差額", f"+{rent_vs_variable:,.0f}万円", delta="購入が有利", delta_color="normal")
    else:
        st.metric("賃貸との差額", f"{rent_vs_variable:,.0f}万円", delta="賃貸が有利", delta_color="inverse")

# 購入時期比較
st.markdown("---")
st.markdown("## ⏰ 購入時期を遅らせた場合のシミュレーション")

wait_years = st.number_input("購入をどれくらい先送りするか（年）", min_value=1, max_value=10, value=2)

rent_loss = rent_couple * 12 * wait_years + (rent_couple * renewal_fee * (wait_years // 2))
first_year_principal = variable_schedule[0]["annual_principal"]
principal_loss = first_year_principal * wait_years
deduction_loss = 28 * wait_years

total_additional_cost = rent_loss + principal_loss + deduction_loss
breakeven_decline_rate = (total_additional_cost / property_price) * 100

col_wait1, col_wait2 = st.columns(2)

with col_wait1:
    st.warning(f"💡 **{wait_years}年先送りした場合の追加コスト試算：約{total_additional_cost:,.0f}万円**")
    st.write(f"• 期間中の賃貸コスト：{rent_loss:,.0f}万円")
    st.write(f"• 資産形成の遅れ：{principal_loss:,.0f}万円")
    st.write(f"• 税制優遇の遅れ：{deduction_loss:,.0f}万円")

with col_wait2:
    st.info(f"📉 **参考：この程度の価格変動があれば延期も選択肢になります**")
    st.write(f"物件価格が約 **{breakeven_decline_rate:.1f}%** 下落する場合")
    st.write(f"（{property_price:,.0f}万円 → {property_price - total_additional_cost:,.0f}万円）")

st.markdown("---")
st.markdown("### 💭 判断のポイント")
st.info("""
**最終的な判断はお客様にお任せしますが、以下の点をご検討ください：**

• **この物件にこの価格の価値があると感じるか？**  
• 待つことで得られるメリットは、追加コストを上回るか？  
• 金利上昇や健康状態変化などのリスクをどう考えるか？  

数値はあくまで参考情報です。ご家族の状況や将来計画に合わせて、総合的にご判断ください。
""")

st.markdown("---")
st.info("💡 **PDF出力方法**：ブラウザの印刷機能（Ctrl+P）を使用してPDFとして保存してください。")
