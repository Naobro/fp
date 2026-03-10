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
# 3. 物件・資金計画（修正版）
# ==========================================
st.markdown("---")
st.markdown("## 🏠 物件・資金計画")

def reset_loan_conditions():
    """借入条件が変更された時の自動リセット関数"""
    # 金利関連のセッション状態をクリア
    keys_to_reset = ['variable_rates', 'complete_table', 'last_loan_years', 'last_base_rate']
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]

col_prop1, col_prop2 = st.columns(2)

with col_prop1:
    property_price = st.number_input("物件価格（万円）", min_value=100, value=6000, step=100)
    self_funds = st.number_input("自己資金（万円）", min_value=0, value=500, step=50)
    
    # 🔑 重要：on_changeコールバックを追加
    loan_years = st.number_input(
        "希望借入年数", 
        min_value=1, 
        max_value=max_loan_years, 
        value=min(35, max_loan_years),
        on_change=reset_loan_conditions,  # 年数変更時に自動リセット
        help="年数を変更すると金利スケジュールが自動更新されます"
    )

with col_prop2:
    closing_costs = property_price * 0.07
    total_cost = property_price + closing_costs
    required_loan = max(0, total_cost - self_funds)
    
    st.metric("諸費用（7%）", f"{closing_costs:,.0f}万円")
    st.metric("必要総額", f"{total_cost:,.0f}万円")
    st.metric("必要借入額", f"{required_loan:,.0f}万円")

# 借入可否判定（既存のまま）
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
# 5. 60年完全比較テーブル（横スクロール型）
# ==========================================
st.markdown("---")
st.markdown("## 📊 60年完全比較テーブル（変動・固定・賃貸 統合表示）")

# 基準金利設定（コンパクトに）
col_rate1, col_rate2, col_rate3 = st.columns(3)

with col_rate1:
    base_rate_variable = st.number_input(
        "変動金利 基準（%）", 
        min_value=0.0, max_value=10.0, value=0.6, step=0.01, format="%.2f",
        on_change=reset_loan_conditions  # 基準金利変更時もリセット
    )
    if loan_years >= 36:
        actual_variable_base = base_rate_variable + 0.1
        st.warning(f"⚠️ **超長期ローン（{loan_years}年）のため全期間+0.10%適用**")
        st.info(f"基準金利 {base_rate_variable:.2f}% → 実際の適用金利 **{actual_variable_base:.2f}%**")
    else:
        actual_variable_base = base_rate_variable
        st.success(f"✅ 標準ローン（{loan_years}年）基準金利そのまま適用")

with col_rate2:
    base_rate_flat = st.number_input(
        "固定金利 基準（%）", 
        min_value=0.0, max_value=10.0, value=2.36, step=0.01, format="%.2f",
        on_change=reset_loan_conditions  # 固定金利変更時もリセット
    )
    if loan_years >= 36:
        actual_flat_base = base_rate_flat + 0.1
        st.warning(f"⚠️ **超長期ローン（{loan_years}年）のため全期間+0.10%適用**")
        st.info(f"基準金利 {base_rate_flat:.2f}% → 実際の適用金利 **{actual_flat_base:.2f}%**")
    else:
        actual_flat_base = base_rate_flat
        st.success(f"✅ 標準ローン（{loan_years}年）基準金利そのまま適用")

with col_rate3:
    # フラット35ポイント計算（既存のまま）
    current_children = sum(1 for age in children_ages if age >= 0 and age < 18)
    if current_children > 0:
        child_plus_points = current_children
        st.metric("子育てプラス", f"{child_plus_points}pt")
    else:
        is_young_couple = husband_age < 40 or wife_age < 40
        child_plus_points = 1 if is_young_couple else 0
        st.metric("子育てプラス", f"{child_plus_points}pt")
    
    total_flat_points = child_plus_points
    st.metric("フラット35ポイント", f"{total_flat_points}pt")


# フラット35金利スケジュール生成（既存関数を使用）
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

# 巨大テーブル初期化
if 'complete_table' not in st.session_state:
    # 項目定義（縦軸）
    row_items = [
        "年齢",
        "家族人数",
        "世帯年収",
        "",  # 空行
        "【変動金利】",
        "適用金利(%)",
        "月額返済(万円)",
        "年間返済(万円)", 
        "うち元金(万円)",
        "うち利息(万円)",
        "ローン残債(万円)",
        "",  # 空行
        "【固定金利】", 
        "適用金利(%)",
        "月額返済(万円)",
        "年間返済(万円)",
        "うち元金(万円)", 
        "うち利息(万円)",
        "ローン残債(万円)",
        "",  # 空行
        "【賃貸】",
        "月額家賃(万円)",
        "年間家賃(万円)",
        "更新料等(万円)",
        "賃貸年間総額(万円)"
    ]
    
    # 60年分の列名
    year_columns = ["項目"] + [f"{y}年目" for y in range(1, 61)]
    
    # DataFrame作成
    st.session_state.complete_table = pd.DataFrame(
        index=range(len(row_items)),
        columns=year_columns
    )
    st.session_state.complete_table["項目"] = row_items
    
    # 初期値で埋める
    for col in year_columns[1:]:  # "項目"列以外
        st.session_state.complete_table[col] = 0.0

# 変動金利スケジュール初期化（状態検証付き）
if 'variable_rates' not in st.session_state:
    st.session_state.variable_rates = [actual_variable_base] * 60
    st.session_state.last_loan_years = loan_years
    st.session_state.last_base_rate = actual_variable_base

# 追加の状態検証：コールバックで拾えなかった変更を検出
if ('last_loan_years' not in st.session_state or 
    st.session_state.last_loan_years != loan_years or
    abs(st.session_state.last_base_rate - actual_variable_base) > 1e-9):
    
    # 金利スケジュールを新しい基準金利で再初期化
    st.session_state.variable_rates = [actual_variable_base] * 60
    st.session_state.last_loan_years = loan_years
    st.session_state.last_base_rate = actual_variable_base
    
    st.success(f"🔄 **借入条件変更検知：金利スケジュールを {actual_variable_base:.2f}% で自動更新しました**")

# 金利編集機能
st.markdown("### 🛠 変動金利スケジュール編集")

# 状況説明と手動リセット
col_info, col_reset = st.columns([3, 1])
with col_info:
    if loan_years >= 36:
        st.info(f"""
        📌 **超長期ローン（{loan_years}年）の金利について**
        - 借入期間が36年以上のため、基準金利に+0.10%が全期間適用されています
        - 下記の金利は既に+0.10%加算済みの値です（1年目から{loan_years}年目まで）
        - 現在の適用金利：**{actual_variable_base:.2f}%**（基準{base_rate_variable:.2f}% + 0.10%）
        """)
    else:
        st.success(f"✅ 標準ローン（{loan_years}年）基準金利 **{actual_variable_base:.2f}%** をそのまま適用")

with col_reset:
    st.markdown("#### ")  # 高さ調整
    if st.button("🔄 金利リセット", help=f"全期間を {actual_variable_base:.2f}% に戻します", use_container_width=True):
        st.session_state.variable_rates = [actual_variable_base] * 60
        st.success(f"✅ 全期間を {actual_variable_base:.2f}% にリセットしました")
        st.rerun()

st.caption("💡 **Excelライクな自動フィル：ある年の金利を変更すると、その年以降すべて同じ金利に自動変更されます**")

# 金利編集テーブル（小数点第2位表示）
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
            help=f"{y}年目を変更すると{y}年目以降すべて同じ金利になります",
            min_value=0.0,
            max_value=10.0,
            step=0.01,
            format="%.2f"  # 小数点第2位まで強制表示
        ) for y in range(1, 61)
    },
    use_container_width=True,
    height=120,
    key="rate_editor"
)

# Excelライクな自動フィル機能
if not edited_rates.equals(rate_edit_df):
    new_rates = edited_rates.iloc[0].tolist()
    old_rates = st.session_state.variable_rates
    
    # 変更された年を検出（浮動小数点誤差対策）
    changed_year_index = None
    for i in range(60):
        if abs(new_rates[i] - old_rates[i]) > 1e-9:
            changed_year_index = i
            break
    
    # 変更された年以降をすべて同じ金利に（Excelのフィルダウン動作）
    if changed_year_index is not None:
        changed_rate = new_rates[changed_year_index]
        # その年以降を全て同じ値で上書き
        for i in range(changed_year_index, 60):
            st.session_state.variable_rates[i] = changed_rate
        
        st.success(f"✅ **{changed_year_index + 1}年目以降を {changed_rate:.2f}% に一括変更しました**")
        st.balloons()  # 視覚的フィードバック
        st.rerun()


# 厳密計算エンジン（既存を改良）
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
                "rate": 0,
                "monthly_payment": 0,
                "annual_payment": 0,
                "annual_principal": 0,
                "annual_interest": 0,
                "balance": 0
            })
    
    return schedule

# 計算実行
variable_schedule = calculate_complete_schedule(required_loan, loan_years, st.session_state.variable_rates)
flat_schedule = calculate_complete_schedule(required_loan, loan_years, flat_rate_schedule)

# テーブルにデータ投入
for year in range(1, 61):
    col_name = f"{year}年目"
    age = husband_age + year - 1
    
    # 家族人数計算
    children_this_year = sum(1 for c_age in children_ages if 0 <= (c_age + year - 1) < 18)
    family_size = 2 + children_this_year
    
    # 賃貸データ
    rent_monthly = rent_schedule[year - 1]
    rent_annual = rent_monthly * 12
    renewal_cost = rent_monthly * renewal_fee if year % 2 == 0 else 0
    rent_total = rent_annual + renewal_cost
    
    # 変動金利データ
    var_data = variable_schedule[year - 1]
    
    # 固定金利データ
    flat_data = flat_schedule[year - 1]
    
    # データ投入（行インデックスで指定）
    st.session_state.complete_table.at[0, col_name] = age  # 年齢
    st.session_state.complete_table.at[1, col_name] = family_size  # 家族人数
    st.session_state.complete_table.at[2, col_name] = household_income  # 世帯年収
    st.session_state.complete_table.at[3, col_name] = ""  # 空行
    
    st.session_state.complete_table.at[4, col_name] = ""  # 【変動金利】
    st.session_state.complete_table.at[5, col_name] = var_data["rate"]  # 適用金利
    st.session_state.complete_table.at[6, col_name] = var_data["monthly_payment"]  # 月額返済
    st.session_state.complete_table.at[7, col_name] = var_data["annual_payment"]  # 年間返済
    st.session_state.complete_table.at[8, col_name] = var_data["annual_principal"]  # 元金
    st.session_state.complete_table.at[9, col_name] = var_data["annual_interest"]  # 利息
    st.session_state.complete_table.at[10, col_name] = var_data["balance"]  # 残債
    st.session_state.complete_table.at[11, col_name] = ""  # 空行
    
    st.session_state.complete_table.at[12, col_name] = ""  # 【固定金利】
    st.session_state.complete_table.at[13, col_name] = flat_data["rate"]  # 適用金利
    st.session_state.complete_table.at[14, col_name] = flat_data["monthly_payment"]  # 月額返済
    st.session_state.complete_table.at[15, col_name] = flat_data["annual_payment"]  # 年間返済
    st.session_state.complete_table.at[16, col_name] = flat_data["annual_principal"]  # 元金
    st.session_state.complete_table.at[17, col_name] = flat_data["annual_interest"]  # 利息
    st.session_state.complete_table.at[18, col_name] = flat_data["balance"]  # 残債
    st.session_state.complete_table.at[19, col_name] = ""  # 空行
    
    st.session_state.complete_table.at[20, col_name] = ""  # 【賃貸】
    st.session_state.complete_table.at[21, col_name] = rent_monthly  # 月額家賃
    st.session_state.complete_table.at[22, col_name] = rent_annual  # 年間家賃
    st.session_state.complete_table.at[23, col_name] = renewal_cost  # 更新料等
    st.session_state.complete_table.at[24, col_name] = rent_total  # 年間総額

# 金利編集機能
st.markdown("### 🛠 変動金利スケジュール編集")
st.caption("💡 **金利を変更すると、その年以降すべて同じ金利に自動変更されます（Excelのフィルダウンと同じ動作）**")

# 変動金利スケジュール初期化
if 'variable_rates' not in st.session_state:
    st.session_state.variable_rates = [actual_variable_base] * 60

# 金利編集テーブル（小数点第2位まで表示）
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
            help=f"{y}年目の金利を変更すると{y}年目以降すべて同じ金利になります",
            min_value=0.0,
            max_value=10.0,
            step=0.01,
            format="%.2f"  # 小数点第2位まで強制表示
        ) for y in range(1, 61)
    },
    use_container_width=True,
    height=100,
    key="rate_editor"
)

# 編集内容を反映（Excelライクな自動フィルダウン機能）
if not edited_rates.equals(rate_edit_df):
    new_rates = edited_rates.iloc[0].tolist()
    old_rates = st.session_state.variable_rates
    
    # どの年が変更されたかを検出（浮動小数点誤差対策）
    changed_year_index = None
    for i in range(60):
        if abs(new_rates[i] - old_rates[i]) > 1e-9:
            changed_year_index = i
            break
    
    # 変更された年以降をすべて同じ金利に（Excelのフィルダウン動作）
    if changed_year_index is not None:
        changed_rate = new_rates[changed_year_index]
        # その年以降を全て同じ値で上書き
        for i in range(changed_year_index, 60):
            st.session_state.variable_rates[i] = changed_rate
        
        st.success(f"✅ {changed_year_index + 1}年目以降を {changed_rate:.2f}% に変更しました")
        st.rerun()


# 完全テーブル表示
st.markdown("### 📊 60年完全比較テーブル")
st.caption("💡 横スクロールで60年間の推移を確認できます。変動・固定・賃貸の全データを一覧表示。")

# 数値フォーマット適用
display_table = st.session_state.complete_table.copy()
for col in display_table.columns[1:]:  # "項目"列以外
    display_table[col] = display_table[col].apply(
        lambda x: f"{x:,.1f}" if isinstance(x, (int, float)) and x != 0 else ("" if x == 0 else x)
    )

st.dataframe(
    display_table,
    use_container_width=True,
    height=700,
    hide_index=True
)

# 簡易サマリー
st.markdown("### 📋 60年総コスト比較")
col_sum1, col_sum2, col_sum3 = st.columns(3)

# 60年間の総コスト計算
total_var_cost = sum(var_data["annual_payment"] for var_data in variable_schedule)
total_flat_cost = sum(flat_data["annual_payment"] for flat_data in flat_schedule) 
total_rent_cost = sum(rent_schedule[i] * 12 + (rent_schedule[i] * renewal_fee if (i+1) % 2 == 0 else 0) for i in range(60))

with col_sum1:
    st.metric("変動金利 60年総額", f"{total_var_cost:,.0f}万円")

with col_sum2:
    st.metric("固定金利 60年総額", f"{total_flat_cost:,.0f}万円")

with col_sum3:
    st.metric("賃貸 60年総額", f"{total_rent_cost:,.0f}万円")

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


