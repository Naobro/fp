# pages/22_reserve_forecast_pdf.py
# 目的：
# - 長期修繕計画を「名目（単価据え置き）」と「インフレ考慮（年率gを複利適用）」の2本で試算
# - 現在・5年後・10年後に必要となる「円／㎡・月（専有基準）」を算出しPDFで明示
# - 延床→専有換算は「専有比率（専有面積/延床）」で行う
# - すべて整数（円）表示

import os, io, math, datetime as dt, requests
import numpy as np
import pandas as pd
import streamlit as st
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# -----------------------------
# ページ設定
# -----------------------------
st.set_page_config(page_title="インフレ考慮の修繕積立金シナリオ（PDF出力）", layout="wide")

# -----------------------------
# 共通ユーティリティ
# -----------------------------
def I(x):
    """四捨五入→整数。None/NaNは0."""
    try:
        if x is None:
            return 0
        if isinstance(x, (float, np.floating)) and (np.isnan(x) or np.isinf(x)):
            return 0
        return int(round(x))
    except:
        return 0

def ratio_pct(p):
    """%を0-1比率へ（整数%前提）"""
    try:
        return max(0.0, float(int(p))) / 100.0
    except:
        return 0.0

# 日本語フォント
FONT_DIR = "fonts"
FONT_PATH = os.path.join(FONT_DIR, "NotoSansJP-Regular.ttf")
def ensure_font():
    os.makedirs(FONT_DIR, exist_ok=True)
    if not os.path.exists(FONT_PATH):
        url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansJP-Regular.otf"
        r = requests.get(url, timeout=30); r.raise_for_status()
        with open(FONT_PATH, "wb") as f: f.write(r.content)
    try:
        pdfmetrics.registerFont(TTFont("NotoSansJP", FONT_PATH))
    except:
        pass
ensure_font()

# -----------------------------
# 画面UI
# -----------------------------
st.title("修繕積立金の予想推移（名目 vs インフレ考慮）｜PDF出力")

with st.sidebar:
    st.header("基本情報")
    total_floor = st.number_input("延床面積（㎡）", min_value=1, step=1, value=19500)
    units = st.number_input("総戸数（戸）", min_value=1, step=1, value=300)
    floors = st.number_input("地上階数（階）", min_value=1, step=1, value=20)
    building_age = st.number_input("築年数（年）", min_value=0, step=1, value=15)
    plan_years = st.radio("長期修繕計画 期間（年）", [35, 30], index=0, horizontal=True)
    # 専有比率：専有合計/延床（例：75%）
    private_ratio_pct = st.number_input("専有比率（専有面積/延床）[%]", min_value=50, max_value=95, step=1, value=75)
    st.caption("※ 円/㎡・月は『専有合計㎡』で割った単価を表示（区分所有者の実感値）")

    st.markdown("---")
    st.header("インフレ・補正等")
    g_pct = st.number_input("インフレ率（年率%・複利）", min_value=0, max_value=20, step=1, value=3)
    # 係数：外壁・仮設の難度による概算
    if floors <= 5: floor_factor_default, band = 100, "低層"
    elif floors <= 10: floor_factor_default, band = 110, "中層"
    elif floors <= 20: floor_factor_default, band = 125, "高層"
    else: floor_factor_default, band = 140, "タワー"
    floor_factor_pct = st.number_input("階数補正 [%]", min_value=80, max_value=200, step=1, value=floor_factor_default)
    st.caption(f"推奨：{band}（足場・外壁面積の増加を概算反映）")

    st.markdown("---")
    st.header("EV・機械式ほか")
    elevators = st.number_input("エレベーター基数", min_value=0, step=1, value=4)
    ev_cost_myen = st.number_input("EV 1基あたり更新費（万円）", min_value=0, step=10, value=2000)
    ev_cycle = st.number_input("EV 更新サイクル（年）", min_value=1, step=1, value=25)
    mech_units = st.number_input("機械式駐車場（台）", min_value=0, step=1, value=0)
    mech_add_each = st.number_input("機械式1台あたり（月額・円）", min_value=0, step=100, value=11000)

    st.markdown("---")
    st.header("現行の徴収水準（判定用）")
    current_per_unit = st.number_input("現行：1戸あたり（月額・円）", min_value=0, step=100, value=12000)

st.caption("注：数値は概算モデル。実務は長期修繕計画・見積・専門家レビューで精査。")

# -----------------------------
# プリセット（1〜9カテゴリ要点）
# 単価=円/㎡、サイクル=年（初期値。画面で編集したい場合はここを調整）
# -----------------------------
PRESETS = {
    "1. 外装・屋根": [
        ("外壁塗装/タイル・シール改修", 6000, 12),
        ("屋根・バルコニー・庇 防水改修", 2800, 12),
    ],
    "2. 鉄部塗装": [
        ("手すり・階段等 鉄部塗装", 1000, 12),
    ],
    "3. 共用部仕上げ": [
        ("廊下・階段 長尺等", 1400, 12),
        ("エントランス床・タイル補修", 1000, 12),
        ("共用照明 LED更新", 700, 12),
    ],
    "4. 給排水設備": [
        ("給水/排水管 更生・更新（㎡按分）", 4400, 24),
        ("ポンプ/受水槽/高架水槽 清掃更新", 1200, 12),
    ],
    "5. 電気・機械設備": [
        ("分電盤/配電盤/受変電 設備更新", 1500, 24),
        ("インターホン更新（モニター化）", 1800, 20),
    ],
    "6. EV（本体は別枠で設定）": [
        ("EV内装リニューアル（㎡按分）", 700, 15),
    ],
    "7. 外構・その他": [
        ("駐車場舗装・ライン引き直し", 800, 12),
        ("駐輪場屋根/ラック更新", 600, 12),
        ("植栽剪定・外構修繕", 800, 12),
    ],
    "8. 防災・安全": [
        ("消火設備更新（消火栓等）", 1200, 20),
        ("非常照明・誘導灯更新", 700, 12),
        ("防犯カメラ設置・更新（㎡按分）", 500, 12),
    ],
    "9. 室内関連（共用起因）": [
        ("専有影響部補修（共用起因・㎡按分）", 400, 12),
        ("サッシ/玄関扉 更新（共用扱い）", 1500, 25),
    ],
}

st.subheader("主要工事項目（編集可）")
edited_items = []
for cat, items in PRESETS.items():
    with st.expander(cat, expanded=False):
        for idx, (name, unit, cyc) in enumerate(items):
            c1, c2 = st.columns(2)
            u = c1.number_input(f"{name} 単価（円/㎡）", min_value=0, step=100, value=unit, key=f"{cat}_{idx}_u")
            c = c2.number_input(f"{name} サイクル（年）", min_value=1, step=1, value=cyc, key=f"{cat}_{idx}_c")
            edited_items.append((name, u, c))

# -----------------------------
# 計算ロジック
# -----------------------------
g = ratio_pct(g_pct)                           # 年率インフレ（複利）
floor_factor = floor_factor_pct / 100.0
private_ratio = ratio_pct(private_ratio_pct)   # 専有比率
private_area = max(1.0, total_floor * private_ratio)  # 専有合計面積（㎡）
mech_monthly = mech_units * mech_add_each     # 機械式の月額加算

def event_times(cycle, age, horizon):
    """サイクル・築年数・計画年数から、今後の発生年tを列挙（t>=0, t<=horizon）。"""
    C = max(1, int(cycle))
    A = max(0, int(age))
    rem = C - (A % C)
    first = 0 if rem == C else rem
    times = []
    t = first
    while t <= horizon:
        times.append(t)
        t += C
    return times

def total_future_cost(items, total_floor, floor_factor, g, age, horizon, ev_pack):
    """将来発生する工事費の合計（名目とインフレ考慮の両方）を返す。"""
    # items: [(name, unit_per_sqm, cycle)]
    # ev_pack: (elevators, ev_cost_yen, ev_cycle)
    base_sum = 0.0     # 名目（単価据え置き）
    infl_sum = 0.0     # インフレ適用
    for (_n, unit, cyc) in items:
        cost_once_now = unit * total_floor * floor_factor
        for t in event_times(cyc, age, horizon):
            base_sum += cost_once_now
            infl_sum += cost_once_now * ((1.0 + g) ** t)
    # EV（本体更新）
    ev_count, ev_cost_yen, ev_cyc = ev_pack
    if ev_count > 0 and ev_cost_yen > 0 and ev_cyc > 0:
        ev_once = ev_count * ev_cost_yen
        for t in event_times(ev_cyc, age, horizon):
            base_sum += ev_once
            infl_sum += ev_once * ((1.0 + g) ** t)
    return base_sum, infl_sum

# EVコストを円に
ev_cost_yen = ev_cost_myen * 10000

base_total, infl_total = total_future_cost(
    edited_items, total_floor, floor_factor, g, building_age, plan_years, (elevators, ev_cost_yen, ev_cycle)
)

# 名目・インフレ各月額（延床ベースの総額→月額）
months_total = plan_years * 12
base_monthly_total = base_total / months_total + mech_monthly
infl_monthly_total = infl_total / months_total + mech_monthly

# 「専有合計㎡」で割って円/㎡・月へ正規化
base_per_sqm_month = base_monthly_total / private_area
infl_per_sqm_month = infl_monthly_total / private_area

# 5年後・10年後に「その時点から開始」した場合の必要単価（インフレ＋残余期間で割る）
def future_required_per_sqm(start_in_years):
    rem_years = max(1, plan_years - start_in_years)
    # start以降に発生するコストのみ合計
    infl_remain = 0.0
    for (_n, unit, cyc) in edited_items:
        cost_once_now = unit * total_floor * floor_factor
        for t in event_times(cyc, building_age, plan_years):
            if t >= start_in_years:
                infl_remain += cost_once_now * ((1.0 + g) ** t)
    # EV
    for t in event_times(ev_cycle, building_age, plan_years):
        if t >= start_in_years:
            infl_remain += (elevators * ev_cost_yen) * ((1.0 + g) ** t)
    monthly_total = infl_remain / (rem_years * 12) + mech_monthly
    return monthly_total / private_area, monthly_total

per_sqm_in_5, total_month_in_5 = future_required_per_sqm(5)
per_sqm_in_10, total_month_in_10 = future_required_per_sqm(10)

# 現行水準とのギャップ（いま不足）
shortage_now = None
suggest_increase_per_unit = None
if current_per_unit > 0 and units > 0:
    current_total_month = current_per_unit * units
    shortage_now = I(infl_monthly_total - current_total_month)  # インフレ考慮計画ベースで判定
    suggest_increase_per_unit = I(max(0, infl_monthly_total - current_total_month) / units)

# -----------------------------
# 画面表示
# -----------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("名目：必要単価（円／㎡・月）", f"{I(base_per_sqm_month):,}")
c2.metric("インフレ考慮：必要単価（円／㎡・月）", f"{I(infl_per_sqm_month):,}")
c3.metric("5年後：必要単価（円／㎡・月）", f"{I(per_sqm_in_5):,}")
c4.metric("10年後：必要単価（円／㎡・月）", f"{I(per_sqm_in_10):,}")

st.caption(f"専有比率：{private_ratio_pct}%（専有合計 {I(private_area):,} ㎡）｜階数補正：{floor_factor_pct}%｜インフレ：年率{g_pct}%（複利）｜計画{plan_years}年")

if shortage_now is not None:
    d1, d2 = st.columns(2)
    d1.metric("不足（＋）／過剰（−）総額（円／月）", f"{shortage_now:,}")
    d2.metric("推奨増額（円／戸・月）", f"{(suggest_increase_per_unit or 0):,}")

# -----------------------------
# PDF出力
# -----------------------------
def build_pdf():
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    margin = 36
    x, y = margin, H - margin

    def set_font(size=12, bold=False):
        try:
            c.setFont("NotoSansJP", size)
        except:
            c.setFont("Helvetica-Bold" if bold else "Helvetica", size)

    def line(text, step=18, size=12, bold=False):
        nonlocal y
        set_font(size, bold)
        c.drawString(x, y, str(text))
        y -= step

    # ヘッダ
    set_font(16, True)
    c.drawString(x, y, "修繕積立金の予想推移（名目 vs インフレ考慮）")
    y -= 24
    set_font(10, False)
    c.drawString(x, y, f"作成日：{dt.datetime.now().strftime('%Y-%m-%d')}")
    y -= 16
    line(f"前提：計画{plan_years}年｜延床{I(total_floor):,}㎡｜総戸数{I(units):,}｜階数{I(floors)}｜専有比率{private_ratio_pct}%（専有{I(private_area):,}㎡）")
    line(f"インフレ率（年率・複利）：{g_pct}%｜階数補正：{floor_factor_pct}%｜EV {I(elevators)}基×{I(ev_cost_myen):,}万円/基（{I(ev_cycle)}年）")
    line(f"機械式駐車場：{I(mech_units)}台×{I(mech_add_each):,}円/月", step=20)

    # 主要結果
    line("主要結果（円／㎡・月：専有基準）", size=13, bold=True)
    line(f"名目 必要単価　　　　　　：{I(base_per_sqm_month):,}")
    line(f"インフレ考慮 必要単価　　：{I(infl_per_sqm_month):,}")
    line(f"5年後 必要単価（開始時点）：{I(per_sqm_in_5):,}")
    line(f"10年後 必要単価（開始時点）：{I(per_sqm_in_10):,}", step=22)

    # 不足判定
    line("不足判定（インフレ考慮計画での月次総額）", size=13, bold=True)
    if current_per_unit > 0 and units > 0:
        current_total_month = current_per_unit * units
        line(f"現行：{I(current_per_unit):,} 円/戸・月 × {I(units):,}戸 ＝ {I(current_total_month):,} 円/月")
        line(f"必要：{I(infl_monthly_total):,} 円/月")
        line(f"差額（不足＋/過剰−）：{I(infl_monthly_total - current_total_month):,} 円/月")
        line(f"推奨増額の目安　　　：{I(max(0, infl_monthly_total - current_total_month)/units):,} 円/戸・月", step=22)
    else:
        line("現行水準未入力のため、過不足判定は省略", step=22)

    # コメント（買主向け説明テンプレ）
    line("コメント（買主向け説明）", size=13, bold=True)
    line("・現行の長期修繕計画は名目（単価据え置き）が一般的。インフレを織り込むと不足は必然。")
    line("・将来の値上げは前提として捉えるべき。対策は(1)段階的増額 (2)一部運用 (3)支出削減。")
    line("・大規模物件では積立金を安全運用して利息を得る事例もある。", step=18)
    line("例：武蔵小杉のタワーマンションでは20億円超の運用で2億円以上の運用益（参考）。", step=22)

    c.showPage()
    c.save()
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes

st.download_button(
    label="PDFをダウンロード（日本語対応）",
    data=build_pdf(),
    file_name=f"reserve_forecast_{dt.datetime.now().strftime('%Y%m%d')}.pdf",
    mime="application/pdf",
)

# 参考用の表（画面表示）
df_summary = pd.DataFrame([
    ["名目 必要単価（円/㎡・月）", I(base_per_sqm_month)],
    ["インフレ考慮 必要単価（円/㎡・月）", I(infl_per_sqm_month)],
    ["5年後 必要単価（円/㎡・月）", I(per_sqm_in_5)],
    ["10年後 必要単価（円/㎡・月）", I(per_sqm_in_10)],
], columns=["指標", "金額"])
st.subheader("サマリー（画面）")
st.dataframe(df_summary, use_container_width=True)