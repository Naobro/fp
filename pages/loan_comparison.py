# pages/loan_comparison.py
import streamlit as st
import pandas as pd
from math import isfinite

st.set_page_config(page_title="住宅ローン比較（年次×金利・月額・累計）", page_icon="🏠", layout="wide")

# -----------------------
# 元利均等 ＝ 利率変更時に残存期間で再計算（再アモタイゼーション）
# -----------------------
def monthly_payment(balance_yen: float, annual_rate_pct: float, remaining_months: int) -> float:
    """残債 balance_yen を、年利 annual_rate_pct(%)・残り remaining_months で元利均等返済する月額"""
    r = (annual_rate_pct / 100.0) / 12.0
    if remaining_months <= 0:
        return 0.0
    if abs(r) < 1e-12:
        return balance_yen / remaining_months
    return balance_yen * r * (1 + r) ** remaining_months / ((1 + r) ** remaining_months - 1)

def simulate_yearly(principal_man: int, years: int, year_rate: dict[int, float]) -> dict[int, dict]:
    """
    年ごとの金利 year_rate（{年: 年利%}）を使って 1年ごとに金利変更を反映。
    戻り: {年: {"rate":%, "monthly":円, "cum":円, "balance":円}}
    """
    balance = principal_man * 10000.0
    total_paid = 0.0
    out: dict[int, dict] = {}

    current_rate = None
    monthly = 0.0
    total_months = years * 12

    for m in range(1, total_months + 1):
        y = (m - 1) // 12 + 1  # 当該月が属する「年」
        # 年頭に金利が指定されていたら切替し、残存期間で月額を再計算
        if (y in year_rate) or (m == 1 and 1 in year_rate):
            current_rate = year_rate.get(y, current_rate)
            remaining_months = total_months - m + 1
            monthly = monthly_payment(balance, current_rate, remaining_months)

        # 月次返済
        r_m = (current_rate / 100.0) / 12.0 if current_rate is not None else 0.0
        interest = balance * r_m
        principal_pay = monthly - interest
        balance -= principal_pay
        total_paid += monthly

        # 年末（12の倍数月）に記録
        if m % 12 == 0:
            out[y] = {
                "rate": round(current_rate, 4) if current_rate is not None and isfinite(current_rate) else 0.0,
                "monthly": round(monthly),
                "cum": round(total_paid),
                "balance": round(max(balance, 0.0))
            }
    return out

def expand_step_schedule(years: int, base: float, step: float) -> dict[int, float]:
    """初期金利 base から毎年 step ずつ変化するシンプルスケジュールを 1..years で作る"""
    return {y: base + step * (y - 1) for y in range(1, years + 1)}

def expand_editor_schedule(years: int, df: pd.DataFrame, col_year="年", col_rate="金利(%)") -> dict[int, float]:
    """
    データエディタ入力（任意の年に金利ポイント）を、1..years の全年へ前方補間で展開。
    入力例：行 {年:1, 金利:0.52}, {年:11, 金利:0.6}, {年:20, 金利:2.0}
    """
    if df.empty:
        return {1: 0.0, **{y: 0.0 for y in range(2, years + 1)}}
    temp = df[[col_year, col_rate]].dropna()
    temp = temp[temp[col_year].between(1, years)]
    temp = temp.sort_values(col_year).drop_duplicates(col_year, keep="last")
    # 前方補間（指定のない年は直近の金利を継続）
    schedule = {}
    last_rate = None
    pointer = 0
    points = temp.to_dict("records")
    for y in range(1, years + 1):
        while pointer < len(points) and points[pointer][col_year] == y:
            last_rate = float(points[pointer][col_rate])
            pointer += 1
        if last_rate is None:
            # 年1が未指定なら0%にせず、最初に与えられた値を初年に採用
            first_rate = float(points[0][col_rate]) if points else 0.0
            last_rate = first_rate
        schedule[y] = last_rate
    return schedule

# -----------------------
# UI（入力）
# -----------------------
st.title("🏠 住宅ローン比較テーブル（年次×金利・月額・累計 別列）")

with st.container():
    c1, c2, c3 = st.columns(3)
    with c1:
        principal = st.number_input("借入金額（万円）", min_value=1, value=5000, step=100)
    with c2:
        years = st.number_input("返済期間（年）", min_value=1, max_value=50, value=35, step=1)
    with c3:
        show_all_years = st.checkbox("全年度（1〜最終年）を表示", value=False)

    if show_all_years:
        target_years = list(range(1, years + 1))
    else:
        # 表示年（自由に追加できる）
        default_years = [1, 2, 3, 5, 10, 11, 20, 30, 35, 40, 50]
        target_years = sorted([y for y in default_years if 1 <= y <= years])
        user_years = st.text_input("追加で表示したい年（半角カンマ区切り）例: 4,6,7",
                                   value="")
        if user_years.strip():
            try:
                extra = [int(x.strip()) for x in user_years.split(",") if x.strip().isdigit()]
                target_years = sorted(set(target_years + [y for y in extra if 1 <= y <= years]))
            except Exception:
                pass

st.markdown("### 変動金利（あなたが全て入力）")
vc1, vc2, vc3, vc4 = st.columns(4)
with vc1:
    var_base = st.number_input("変動①：現状維持（初期%）", value=0.52, step=0.01)
with vc2:
    var_up01 = st.number_input("変動②：毎年 +0.10%（初期%）", value=0.52, step=0.01)
with vc3:
    var_up025 = st.number_input("変動③：毎年 +0.25%（初期%）", value=0.52, step=0.01)
with vc4:
    var_down01 = st.number_input("変動④：毎年 -0.10%（初期%）", value=0.52, step=0.01)

st.caption("※ 下限・上限の自動制限はかけません。入力通りに計算します。")

st.markdown("#### 変動⑤：自由入力（年⇄金利% を表で編集）")
init_df = pd.DataFrame({"年": [1, 11, 12, 20], "金利(%)": [0.52, 0.60, 0.40, 2.00]})
var_editor_df = st.data_editor(
    init_df,
    num_rows="dynamic",
    use_container_width=True,
    key="var_editor",
)

st.markdown("### 固定金利（終了後の扱いを選択可能）")
fc1, fc2, fc3 = st.columns(3)
with fc1:
    fix2_rate = st.number_input("固定2年：当初金利(%)", value=1.00, step=0.01)
with fc2:
    after2_choice = st.selectbox("2年終了後の選択", ["変動へ移行（変動①を使用）", "再固定（1回だけ）"], index=0)
with fc3:
    after2_fix_rate = st.number_input("再固定：金利(%)（2年終了後）", value=1.20, step=0.01, disabled=(after2_choice != "再固定（1回だけ）"))
af2_fix_years = st.number_input("再固定：期間（年）", min_value=1, value=3, step=1, disabled=(after2_choice != "再固定（1回だけ）"))

gc1, gc2, gc3 = st.columns(3)
with gc1:
    fix10_rate = st.number_input("固定10年：当初金利(%)", value=1.20, step=0.01)
with gc2:
    after10_choice = st.selectbox("10年終了後の選択", ["変動へ移行（変動①を使用）", "再固定（1回だけ）"], index=0)
with gc3:
    after10_fix_rate = st.number_input("再固定：金利(%)（10年終了後）", value=1.50, step=0.01, disabled=(after10_choice != "再固定（1回だけ）"))
af10_fix_years = st.number_input("再固定：期間（年）", min_value=1, value=5, step=1, disabled=(after10_choice != "再固定（1回だけ）"))

st.markdown("### フラット35（基準のみ入力。優遇は差し引きで自動）")
fb1, fb2, fb3, fb4 = st.columns(4)
with fb1:
    flat_base = st.number_input("フラット35：基準金利(%)", value=1.50, step=0.01)
with fb2:
    flat_s_delta = st.number_input("フラット35S：優遇幅(%)（例: 0.25）", value=0.25, step=0.01)
with fb3:
    flat_s_years = st.selectbox("フラット35S：優遇年数", [5, 10], index=1)
with fb4:
    flat_child_delta = st.number_input("子育て：優遇幅(%)（例: 0.25）", value=0.25, step=0.01)
child_years = st.selectbox("子育て：優遇年数", [5, 10], index=1)

# -----------------------
# 金利スケジュールの作成
# -----------------------
def build_variable_schedules() -> dict[str, dict[int, float]]:
    s = {}
    # ① 現状維持
    s["変動① 現状維持"] = {1: var_base, **{y: var_base for y in range(2, years + 1)}}
    # ② +0.10
    s["変動② 毎年+0.10%"] = expand_step_schedule(years, var_up01, +0.10)
    # ③ +0.25
    s["変動③ 毎年+0.25%"] = expand_step_schedule(years, var_up025, +0.25)
    # ④ -0.10
    s["変動④ 毎年-0.10%"] = expand_step_schedule(years, var_down01, -0.10)
    # ⑤ 自由入力（表を前方補間で展開）
    s["変動⑤ 自由入力"] = expand_editor_schedule(years, var_editor_df, col_year="年", col_rate="金利(%)")
    return s

def build_fixed_schedule(initial_rate: float, initial_years: int, after_choice: str,
                         after_fix_rate: float, after_fix_years: int,
                         var_follow_rate: float) -> dict[int, float]:
    """
    固定→（変動① or 再固定→その後 変動①）の1回切替を想定。
    """
    sched: dict[int, float] = {}
    # 当初固定
    for y in range(1, min(initial_years, years) + 1):
        sched[y] = initial_rate
    # 終了後
    next_start = initial_years + 1
    if next_start <= years:
        if after_choice == "再固定（1回だけ）":
            # 再固定期間
            for y in range(next_start, min(next_start + after_fix_years - 1, years) + 1):
                sched[y] = after_fix_rate
            # さらにその後は変動①へ
            next2 = next_start + after_fix_years
            for y in range(next2, years + 1):
                sched[y] = var_follow_rate
        else:
            # 変動①へ移行
            for y in range(next_start, years + 1):
                sched[y] = var_follow_rate
    return sched

def build_flat_schedules() -> dict[str, dict[int, float]]:
    s = {}
    # フラット35 基準
    s["フラット35 基準"] = {y: flat_base for y in range(1, years + 1)}
    # フラット35S（優遇→基準）
    s["フラット35S"] = {y: (flat_base - flat_s_delta if y <= flat_s_years else flat_base) for y in range(1, years + 1)}
    # 子育て（優遇→基準）
    s["フラット 子育て"] = {y: (flat_base - flat_child_delta if y <= child_years else flat_base) for y in range(1, years + 1)}
    # 35S子育て（両方の優遇を同一とみなす場合は max を使用。実務仕様は各行で設定に合わせて調整）
    s["フラット35S 子育て"] = {
        y: (flat_base - max(flat_s_delta if y <= flat_s_years else 0.0,
                            flat_child_delta if y <= child_years else 0.0))
        for y in range(1, years + 1)
    }
    return s

# 変動（5パターン）
var_schedules = build_variable_schedules()
# 固定2年・固定10年（終了後の扱いは選択）
fix2_schedule = build_fixed_schedule(fix2_rate, 2, after2_choice, after2_fix_rate, int(af2_fix_years), var_base)
fix10_schedule = build_fixed_schedule(fix10_rate, 10, after10_choice, after10_fix_rate, int(af10_fix_years), var_base)
# フラット群
flat_schedules = build_flat_schedules()

# -----------------------
# シミュレーション実行
# -----------------------
scenarios: dict[str, dict[int, float]] = {}
scenarios.update(var_schedules)
scenarios["固定2年"] = fix2_schedule
scenarios["固定10年"] = fix10_schedule
scenarios.update(flat_schedules)

sim_results: dict[str, dict[int, dict]] = {name: simulate_yearly(principal, years, sched) for name, sched in scenarios.items()}

# -----------------------
# 表（年次 × 金利 / 月額 / 累計 を別列）
# -----------------------
cols = []
for y in target_years:
    cols += [f"{y}年 金利(%)", f"{y}年 月額(円)", f"{y}年 累計(円)"]

table_rows = []
for name, yearly in sim_results.items():
    row = {"商品": name}
    for y in target_years:
        data = yearly.get(y)
        if data:
            row[f"{y}年 金利(%)"] = data["rate"]
            row[f"{y}年 月額(円)"] = data["monthly"]
            row[f"{y}年 累計(円)"] = data["cum"]
        else:
            row[f"{y}年 金利(%)"] = ""
            row[f"{y}年 月額(円)"] = ""
            row[f"{y}年 累計(円)"] = ""
    table_rows.append(row)

df = pd.DataFrame(table_rows, columns=["商品"] + cols)

st.markdown("### 📊 比較テーブル（年次×金利・月額・累計）")
st.dataframe(
    df.style.format(
        {c: "{:,.0f}" for c in df.columns if c.endswith("月額(円)") or c.endswith("累計(円)")}
    ),
    use_container_width=True,
)
