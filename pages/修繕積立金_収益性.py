# pages/修繕積立金_収益性.py
# 目的：
# ・入力8項目だけで、横＝年度（右に進むほど未来）、縦＝項目（建築/設備/足場仮設＋工事項目＋周期）で
#   「万円」単位の長期修繕表を pandas で生成・表示する
# ・雛形の体裁（横テーブル）を固定。中身の数字のみ自動計算。
# ・インフレ率3%（複利）、税10%、諸経費10% を内部固定。単価・周期も内部固定でUI非表示。
#
# 入力（8項目）：
#   現在の修繕積立金（月額・マンション全体）
#   専有面積（あなたの住戸・㎡）  ※専有比率の参考用（表には出さない）
#   延べ床面積（㎡）
#   築年（西暦）
#   戸数（戸）
#   階数（階）
#   EV台数（基）
#   近隣家賃相場（円/㎡・月）     ※表には出さない
#
# 表示：
#   ・「万 円」単位の横テーブル（右：2025→2060、縦：項目）
#   ・上段＝建築、設備、足場仮設（工事項目行＋周期列）
#   ・中段＝諸経費/消費税/支出合計
#   ・下段＝期首繰越/修繕積立金収入/収入合計/当期収支/期末残高
#
# 備考：
#   ・外壁面積などの詳細は入力させず、延べ床・階数から推定して概算する（内部推定）。
#   ・数値は整数・カンマ付きで見やすく表示（pandas→文字列化）。

import math
import datetime as dt
import numpy as np
import pandas as pd
import streamlit as st

# =====================
# 内部固定パラメータ
# =====================
INFL = 0.03         # インフレ年3%（複利）
TAX = 0.10          # 消費税10%
OH = 0.10           # 諸経費（現管・一般管・法定福利等）＝工事費小計の10%
PRIVATE_RATIO_BUILDING = 0.75  # 延べ床→専有合計の代表比率（表に出さない）

# 外壁・屋上の面積推定（延べ床/階 × 係数）
FACADE_COEF = 1.25  # 外壁係数（凹凸考慮の代表値）
STEEL_RATIO = 0.10  # 鉄部塗装面積 ≒ 外壁面積の10%

def floor_factor_by_floors(f:int)->float:
    if f <= 5:   return 1.00
    if f <= 10:  return 1.10
    if f <= 20:  return 1.25
    return 1.40

# 工事項目（大カテゴリ, 小項目, 周期(年), 単価タイプ, 単価（円/単位））
# 単価タイプ：'sqm'（㎡単価×推定面積） / 'lump'（一式・総額） / 'per_unit'（戸数×単価） / 'ev'（EV台数×単価）
ITEMS = [
    ("建築", "外壁塗装・タイル補修・シーリング", 12, "sqm",    6_000),
    ("建築", "屋上・バルコニー・庇 防水改修",   12, "sqm",    2_800),
    ("建築", "鉄部塗装（手すり・階段・フェンス等）", 12, "sqm", 1_000),
    ("設備", "給水設備（ポンプ・受水槽等）更新", 12, "sqm",    1_200),
    ("設備", "給排水管 更生/更新（㎡按分）",      24, "sqm",    4_400),
    ("設備", "分電盤・配電盤・受変電設備 更新",    24, "sqm",    1_500),
    ("設備", "インターホン更新（モニター化）",     20, "per_unit", 70_000),  # 戸×7万円
    ("設備", "エレベーター更新（本体）",          25, "ev",   20_000_000),   # 台×2,000万円
    ("設備", "外構・舗装・植栽 等",               12, "sqm",      800),
    ("足場仮設", "足場仮設（共通）",              12, "sqm",    2_000),
]

# ==========
# 関数群
# ==========
def fmt_man(n_yen: float) -> str:
    """円→万円、整数＆カンマ書式"""
    man = int(round(n_yen / 10_000))
    return f"{man:,}"

def inflated(base_yen: float, years_from_start: int) -> float:
    return base_yen * ((1.0 + INFL) ** max(0, years_from_start))

def schedule_years(built_year:int, cycle:int, start_year:int, end_year:int):
    years = []
    y = built_year + cycle
    while y <= end_year + cycle*2:
        if start_year <= y <= end_year:
            years.append(y)
        y += cycle
    return years

# ==========
# 入力（8項目）
# ==========
st.set_page_config(page_title="横テーブル（万円）｜長期修繕 概算シミュレーション", layout="wide")
st.title("長期修繕 概算シミュレーション（横テーブル／単位：万円）")

with st.sidebar:
    st.header("入力（整数）")
    monthly_total_now = st.number_input("現在の修繕積立金（月額・マンション全体・円）", min_value=0, step=1000, value=1_000_000)
    my_private_area   = st.number_input("専有面積（あなたの住戸・㎡）", min_value=1, step=1, value=70)
    total_floor_area  = st.number_input("延べ床面積（㎡）", min_value=100, step=10, value=19_500)
    built_year        = st.number_input("築年（西暦）", min_value=1900, max_value=2100, step=1, value=2000)
    units             = st.number_input("戸数（戸）", min_value=1, step=1, value=300)
    floors            = st.number_input("階数（階）", min_value=1, step=1, value=20)
    ev_count          = st.number_input("EV台数（基）", min_value=0, step=1, value=4)
    rent_psqm         = st.number_input("近隣家賃相場（円/㎡・月）", min_value=0, step=100, value=4000)

# 年レンジ
start_year = dt.date.today().year               # 今年スタート
horizon    = 35
end_year   = start_year + horizon - 1
years      = list(range(start_year, end_year + 1))

# 推定面積など
per_floor_area   = total_floor_area / max(1, floors)   # 1フロア面積
facade_area_est  = per_floor_area * FACADE_COEF        # 外壁推定面積
roof_area_est    = per_floor_area                      # 屋上・防水面積
steel_area_est   = facade_area_est * STEEL_RATIO       # 鉄部塗装の面積目安
floor_factor     = floor_factor_by_floors(int(floors)) # 仮設・外装系補正

# ㎡単価で使う「対象面積」の割当
def area_for_item(cat:str, name:str) -> float:
    if "外壁塗装" in name:               return facade_area_est * floor_factor
    if "防水" in name:                   return roof_area_est * floor_factor
    if "鉄部塗装" in name:               return steel_area_est * floor_factor
    if "外構・舗装・植栽" in name:        return per_floor_area * 0.5           # 簡易代表
    if cat == "足場仮設":                 return facade_area_est * floor_factor
    # 設備系（㎡按分とする代表）
    return total_floor_area

# ==========================
# 横テーブル（万円）を生成
# ==========================
# 行見出し： [工事区分, 工事項目, 周期（年）] ＋ 年度列
row_index = []
data = {y: [] for y in years}

# 1) 工事項目ごとの行
for cat, name, cycle, utype, unit_cost in ITEMS:
    row_index.append((cat, name, f"{cycle}年"))
    scheduled = set(schedule_years(int(built_year), int(cycle), start_year, end_year))
    for y in years:
        if y in scheduled:
            t = y - start_year
            if utype == "sqm":
                base = unit_cost * area_for_item(cat, name)
            elif utype == "per_unit":
                base = unit_cost * units
            elif utype == "ev":
                base = unit_cost * ev_count
            else:  # lump
                base = unit_cost
            amt = inflated(base, t)                   # 円
            data[y].append(fmt_man(amt))              # 万円（文字列）
        else:
            data[y].append("")

# 2) 工事費 小計（万円）/年（諸経費・税の前）
row_index.append(("支出集計", "工事費小計", ""))
for y in years:
    # 空でないセルを拾って万→円換算して合計
    subtotal_yen = 0
    for i, (cat,name,cyc) in enumerate(row_index[:-1]):  # 末尾は小計行自身なので除外
        val = data[y][i]
        if val != "":
            subtotal_yen += int(val.replace(",","")) * 10_000
    data[y].append(fmt_man(subtotal_yen))

# 3) 諸経費／消費税／A（支出合計）
for label, kind in [("諸経費（10%）","oh"), ("消費税（10%）","tax"), ("A.支出合計","sum")]:
    row_index.append(("支出集計", label, ""))
    for y in years:
        subtotal_yen = int(data[y][-1].replace(",","")) * 10_000  # 直前の工事費小計（円）
        if kind=="oh":
            v = subtotal_yen * OH
        elif kind=="tax":
            v = (subtotal_yen + subtotal_yen*OH) * TAX
        else:
            v = subtotal_yen + subtotal_yen*OH + (subtotal_yen + subtotal_yen*OH)*TAX
        data[y].append(fmt_man(v))

# 4) 収入・残高（万円）
#    期首繰越は0スタート（必要ならコード内で初期残高定数を設けて変更）
row_index.append(("収入・残高", "期首繰越", ""))
row_index.append(("収入・残高", "修繕積立金収入（年額）", ""))
row_index.append(("収入・残高", "当期収入合計", ""))
row_index.append(("収入・残高", "当期収支（収入合計－A）", ""))
row_index.append(("収入・残高", "期末残高（次期繰越）", ""))

for y_idx, y in enumerate(years):
    # 期首繰越
    if y_idx == 0:
        beg_yen = 0
    else:
        beg_yen = int(data[years[y_idx-1]][-1].replace(",","")) * 10_000  # 直前の期末残高（円）
    # 年間収入（現行積立月額×12）
    income_yen = monthly_total_now * 12
    income_total_yen = beg_yen + income_yen
    # 支出合計（A）
    a_yen = int(data[y][-3].replace(",","")) * 10_000  # 「A.支出合計」は末尾から3番目に入れた
    # 当期収支と期末残高
    net_yen = income_total_yen - a_yen
    end_yen = max(0, net_yen)  # マイナスでもそのまま出したい場合は max を外す

    # 追記（順に：期首／年収入／収入合計／当期収支／期末）
    data[y].extend([
        fmt_man(beg_yen),
        fmt_man(income_yen),
        fmt_man(income_total_yen),
        fmt_man(net_yen),
        fmt_man(end_yen),
    ])

# ==========================
# DataFrame 生成（表示用）
# ==========================
idx = pd.MultiIndex.from_tuples(row_index, names=["工事区分","工事項目","周期（目安）"])
df = pd.DataFrame({y: data[y] for y in years}, index=idx)

st.subheader(f"横テーブル（単位：万円）｜{start_year}〜{end_year}（{len(years)}年）")
st.dataframe(df, use_container_width=True)

st.caption("※ すべて概算。単価・周期・インフレ率3%は内部固定。外壁・屋上・鉄部の面積は延べ床と階数から推定。")