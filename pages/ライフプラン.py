import streamlit as st
import pandas as pd
import numpy_financial as npf
from utils import set_matplotlib_japanese_font  # ✅ utils.pyを利用

# ✅ 今後グラフ追加に備えてフォント設定
set_matplotlib_japanese_font()

def fv(rate, nper, pmt, pv=0, when=0):
    return npf.fv(rate, nper, pmt, pv, when)

st.title("50年ライフプラン＋キャッシュフロー/資産運用")

with st.form("lifeplan_form"):
    st.header("① 家族構成")
    col1, col2 = st.columns(2)
    with col1:
        age_main = st.number_input("ご主人 年齢", min_value=18, max_value=90, value=40)
    with col2:
        age_spouse = st.number_input("奥様 年齢", min_value=18, max_value=90, value=38)

    st.subheader("お子様（年齢・予定を分けて4人まで）")
    child_ages, child_plans = [], []
    for i in range(1, 5):
        c1, c2 = st.columns(2)
        with c1:
            age = st.number_input(f"{i}人目 お子様 年齢", min_value=0, max_value=60, value=0, key=f"child_age_{i}")
        with c2:
            plan = st.number_input(f"{i}人目 お子様 予定（何年後）", min_value=0, max_value=50, value=0, key=f"child_plan_{i}")
        child_ages.append(age)
        child_plans.append(plan)

    st.header("② 収入")
    colA, colB = st.columns(2)
    with colA:
        st.markdown("#### ご主人")
        income_main = st.number_input("年収(万円)", value=1000, key="income_main")
        income_up_main = st.number_input("年収上昇率(%)", value=1.0, key="income_up_main") / 100
        retire_age_main = st.number_input("退職予定年齢", min_value=30, max_value=90, value=65, key="retire_age_main")
        retire_main = st.number_input("退職金予定(万円)", value=2000, key="retire_main")
    with colB:
        st.markdown("#### 奥様")
        income_spouse = st.number_input("年収(万円)", value=500, key="income_spouse")
        income_up_spouse = st.number_input("年収上昇率(%)", value=1.0, key="income_up_spouse") / 100
        retire_age_spouse = st.number_input("退職予定年齢", min_value=30, max_value=90, value=60, key="retire_age_spouse")
        retire_spouse = st.number_input("退職金予定(万円)", value=1000, key="retire_spouse")
    stock_income = st.number_input("ストック収入（家賃・配当等/年, 万円）", value=0, key="stock_income")
    other_income = st.number_input("その他収入（年, 万円）", value=0, key="other_income")

    st.header("③ 支出")
    col5, col6 = st.columns(2)
    with col5:
        living = st.number_input("基本生活費（月）", value=20)
        house = st.number_input("住居費（月）", value=20)
        car = st.number_input("車両費（月）", value=0)
        edu = st.number_input("教育費（月）", value=0)
    with col6:
        ins = st.number_input("保険料（月）", value=2)
        other = st.number_input("その他（月）", value=2)
        extra = st.number_input("臨時支出（年額）", value=0)
        event = st.number_input("イベント支出（年額）", value=0)

    st.header("④ 年金・iDeCo")
    colP, colQ = st.columns(2)
    with colP:
        nenkin_net_main = st.number_input("ご主人 年金ネット年額（万円）", value=0, key="nenkin_net_main")
        nenkin_record_year = st.number_input("ご主人 年金加入年数", value=40, key="nenkin_record_year")
        nenkin_missing_year = st.number_input("ご主人 年金未納年数", value=0, key="nenkin_missing_year")
        avg_income_nenkin = st.number_input("ご主人 年金用平均年収(万円)", value=800, key="avg_income_nenkin")
        ideco_month = st.number_input("ご主人 iDeCo月額（円）", value=23000, key="ideco_month")
        ideco_year = st.number_input("ご主人 iDeCo年数", value=40, key="ideco_year")
        ideco_rate = st.number_input("ご主人 iDeCo利回り(%)", value=3.0, key="ideco_rate") / 100
    with colQ:
        nenkin_net_spouse = st.number_input("奥様 年金ネット年額（万円）", value=0, key="nenkin_net_spouse")
        nenkin_record_year_s = st.number_input("奥様 年金加入年数", value=20, key="nenkin_record_year_s")
        nenkin_missing_year_s = st.number_input("奥様 年金未納年数", value=5, key="nenkin_missing_year_s")
        avg_income_nenkin_s = st.number_input("奥様 年金用平均年収(万円)", value=800, key="avg_income_nenkin_s")
        ideco_month_s = st.number_input("奥様 iDeCo月額（円）", value=13000, key="ideco_month_s")
        ideco_year_s = st.number_input("奥様 iDeCo年数", value=20, key="ideco_year_s")
        ideco_rate_s = st.number_input("奥様 iDeCo利回り(%)", value=3.0, key="ideco_rate_s") / 100

    # ⑤ 資産運用
    st.header("⑤ 資産運用（月額積立・利回り入力）")
    st.caption("積立額は全て“万円/月”、利回りは“年利（%）”。積立0でもOK")
    port_names = [
        "NISA積立", "外貨預金積立", "投資信託/ETF積立", "保険（積立型）積立",
        "仮想通貨積立", "オフショア積立", "FX積立", "定期預金積立", "金・現物積立"
    ]
    port_defaults = [3, 1, 2, 1, 1, 1, 0, 1, 0]
    port_rates = [3.0, 2.0, 4.0, 1.5, 10.0, 5.0, 7.0, 1.0, 2.0]
    port_inputs, port_rate_inputs = [], []
    for i, name in enumerate(port_names):
        c1, c2 = st.columns(2)
        with c1:
            amt = st.number_input(f"{name}（万円/月）", value=port_defaults[i], key=f"{name}_amt")
        with c2:
            rate = st.number_input(f"{name} 年利回り（%）", value=port_rates[i], key=f"{name}_rate")
        port_inputs.append(amt)
        port_rate_inputs.append(rate/100)

    st.header("⑥ 資産・投資（初期値、すべて“万円”）")
    col7, col8 = st.columns(2)
    with col7:
        savings = st.number_input("貯蓄額（国内・万円）", value=500)
        foreign = st.number_input("外貨預金（万円）", value=0)
        securities = st.number_input("有価証券（NISA含む・万円）", value=0)
        insurance_product = st.number_input("保険商品（万円）", value=0)
    with col8:
        crypto = st.number_input("仮想通貨（万円）", value=0)
        offshore = st.number_input("オフショア積立（万円）", value=0)
        fx = st.number_input("FX（万円）", value=0)
        deposit = st.number_input("定期預金（万円）", value=0)
        gold = st.number_input("金・現物（万円）", value=0)

    submitted = st.form_submit_button("シミュレーション実行")

def get_child_age(years, age, plan):
    if age > 0:
        return [age + i for i in range(years)]
    elif plan > 0:
        return [""] * plan + [i for i in range(years - plan)]
    else:
        return [""] * years

if submitted:
    years = 50
    base_year = 2025
    columns = [str(base_year + i) for i in range(years)]

    # 家族年齢
    ages_main = [age_main + i for i in range(years)]
    ages_spouse = [age_spouse + i for i in range(years)]
    child_list = [get_child_age(years, child_ages[i], child_plans[i]) for i in range(4)]

    # 年金の簡易計算
    def nenkin_simple(avg_income, record_year, missing_year):
        wage_pension = avg_income * 5.481 / 1000 * record_year
        fix_pension = 80 * ((40-missing_year)/40)
        return wage_pension + fix_pension

    nenkin_main_value = nenkin_net_main if nenkin_net_main > 0 else nenkin_simple(avg_income_nenkin, nenkin_record_year, nenkin_missing_year)
    nenkin_spouse_value = nenkin_net_spouse if nenkin_net_spouse > 0 else nenkin_simple(avg_income_nenkin_s, nenkin_record_year_s, nenkin_missing_year_s)
    nenkin_main = [round(nenkin_main_value) if age >= 65 else 0 for age in ages_main]
    nenkin_spouse = [round(nenkin_spouse_value) if age >= 65 else 0 for age in ages_spouse]

    # iDeCo積立額
    ideco_total_main = round(fv(ideco_rate/12, ideco_year*12, -ideco_month, 0, 0) / 10000)
    ideco_main = [0]*years
    if 65 - age_main >= 0 and 65 - age_main < years:
        ideco_main[65 - age_main] = ideco_total_main

    ideco_total_spouse = round(fv(ideco_rate_s/12, ideco_year_s*12, -ideco_month_s, 0, 0) / 10000)
    ideco_spouse = [0]*years
    if 65 - age_spouse >= 0 and 65 - age_spouse < years:
        ideco_spouse[65 - age_spouse] = ideco_total_spouse

    # 収入・退職金
    incomes_main = [round(income_main*((1+income_up_main)**i)) if ages_main[i] < retire_age_main else 0 for i in range(years)]
    incomes_spouse = [round(income_spouse*((1+income_up_spouse)**i)) if ages_spouse[i] < retire_age_spouse else 0 for i in range(years)]
    retire_main_paid = [0]*years
    retire_spouse_paid = [0]*years
    if retire_age_main-age_main < years:
        retire_main_paid[retire_age_main-age_main] = round(retire_main)
    if retire_age_spouse-age_spouse < years:
        retire_spouse_paid[retire_age_spouse-age_spouse] = round(retire_spouse)

    # 収入合計
    stock_incomes = [round(stock_income) for _ in range(years)]
    other_incomes = [round(other_income) for _ in range(years)]
    total_income = [
        incomes_main[i]+incomes_spouse[i]+retire_main_paid[i]+retire_spouse_paid[i]+stock_incomes[i]+other_incomes[i]
        for i in range(years)
    ]
    total_pension = [nenkin_main[i]+nenkin_spouse[i]+ideco_main[i]+ideco_spouse[i] for i in range(years)]
    total_income_all = [total_income[i]+total_pension[i] for i in range(years)]

    # 支出
    monthly_expense = living+house+car+edu+ins+other
    annual_expense = [round(monthly_expense*12+extra+event) for _ in range(years)]
    surplus = [total_income_all[i]-annual_expense[i] for i in range(years)]

    # 投資積立
    asset_invest_sum = round(sum(port_inputs)*12)
    asset_invest_sums = [asset_invest_sum for _ in range(years)]

    # 資産残高計算
    asset_keys = [
        "NISA積立", "外貨預金積立", "投資信託/ETF積立", "保険（積立型）積立",
        "仮想通貨積立", "オフショア積立", "FX積立", "定期預金積立", "金・現物積立"
    ]
    initial_vals = [securities, foreign, 0, insurance_product, crypto, offshore, fx, deposit, gold]
    asset_balances = {}
    for idx, k in enumerate(asset_keys):
        amt = port_inputs[idx]
        rate = port_rate_inputs[idx]
        balances = [round(initial_vals[idx])]
        for y in range(years):
            prev = balances[-1]
            add_amt = amt*12
            bal = round(prev*(1+rate)+add_amt)
            balances.append(bal)
        asset_balances[k] = balances[1:]

    # iDeCo
    ideco_balances = []
    val = 0
    for y in range(years):
        if y < 65-age_main:
            val = round(val*(1+ideco_rate)+(ideco_month*12)/10000)
        elif y == 65-age_main:
            val = 0
        ideco_balances.append(val)
    asset_balances["iDeCo積立"] = ideco_balances

    # 現預金
    cash_balances = [round(savings)]
    for y in range(years):
        net = surplus[y]-sum(port_inputs)*12
        cash_balances.append(cash_balances[-1]+net)
    cash_balances = cash_balances[1:]

    total_asset = [cash_balances[i]+sum(asset_balances[k][i] for k in asset_balances) for i in range(years)]

    # === 表作成 ===
    records = []
    records += [
        ["ご主人年齢"]+ages_main,
        ["奥様年齢"]+ages_spouse,
        ["①子供年齢"]+child_list[0],
        ["②子供年齢"]+child_list[1],
        ["③子供年齢"]+child_list[2],
        ["④子供年齢"]+child_list[3],
        ["" for _ in range(years+1)],
    ]
    records += [
        ["ご主人年収（万円）"]+incomes_main,
        ["奥様年収（万円）"]+incomes_spouse,
        ["ご主人退職金（万円）"]+retire_main_paid,
        ["奥様退職金（万円）"]+retire_spouse_paid,
        ["ストック収入（万円）"]+stock_incomes,
        ["その他収入（万円）"]+other_incomes,
        ["" for _ in range(years+1)],
    ]
    records += [
        ["ご主人年金（万円）"]+nenkin_main,
        ["奥様年金（万円）"]+nenkin_spouse,
        ["ご主人iDeCo（万円）"]+ideco_main,
        ["奥様iDeCo（万円）"]+ideco_spouse,
        ["収入合計（万円）"]+total_income,
        ["年金・iDeCo合計（万円）"]+total_pension,
        ["収入+年金合計（万円）"]+total_income_all,
        ["" for _ in range(years+1)],
    ]
    records += [
        ["基本生活費（月・万円）"]+[round(living*12) for _ in range(years)],
        ["住居費（月・万円）"]+[round(house*12) for _ in range(years)],
        ["車両費（月・万円）"]+[round(car*12) for _ in range(years)],
        ["教育費（月・万円）"]+[round(edu*12) for _ in range(years)],
        ["保険料（月・万円）"]+[round(ins*12) for _ in range(years)],
        ["その他（月・万円）"]+[round(other*12) for _ in range(years)],
        ["臨時支出（万円）"]+[round(extra) for _ in range(years)],
        ["イベント支出（万円）"]+[round(event) for _ in range(years)],
        ["支出合計（万円）"]+annual_expense,
        ["" for _ in range(years+1)],
    ]
    records += [
        ["年間収支（収入+年金合計-支出）"]+surplus,
        ["" for _ in range(years+1)],
        ["資産運用積立（年額）"]+asset_invest_sums,
        ["" for _ in range(years+1)],
    ]
    records += [["現預金（万円）"]+cash_balances]
    for k in asset_keys:
        records.append([f"{k.replace('積立','')}残高（万円）"]+asset_balances[k])
    records.append(["iDeCo残高（万円）"]+asset_balances["iDeCo積立"])
    records.append(["資産合計（万円）"]+total_asset)

    df = pd.DataFrame(records)
    df.columns = ["項目"]+columns
    st.subheader("ライフプラン50年表（A3横型・資産推移・全項目）")
    st.dataframe(df, height=900, width=2400)
    st.download_button("CSVでダウンロード", data=df.to_csv(index=False), file_name="lifeplan_fullwide.csv", mime="text/csv")
