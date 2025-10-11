# /pages/住宅ローン提案.py
# 住宅ローン 提案シミュレーター（reportlab不使用 / fpdf2版）
# 修正内容：
# 1. フラット35の金利入力（UI/保存）の単位（パーセント→小数）の不一致を修正。
# 2. PDF生成時の特記事項描画で、ヘッダー描画が重複していた冗長かつ誤動作の原因となるコードを削除し、正しく特記事項が描画されるように修正。

import os
import io
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

import streamlit as st
from fpdf import FPDF
# from client_portal import db_insert_record, now_iso # 未使用なのでコメントアウト
from auth import login_ui
from supabase import create_client # create_client は supabase から直接インポート

# ===== 画面設定 =====
# ✅ ページ設定とサイドバー削除（最初の3行）
import streamlit as st
st.set_page_config(page_title="住宅ローン提案", layout="wide", initial_sidebar_state="collapsed")
st.markdown("<style>section[data-testid='stSidebar']{display:none;}</style>", unsafe_allow_html=True)
authenticated = login_ui()
if not authenticated:
    st.warning("🔑 このシミュレーターを利用するにはLINE登録とログインが必要です。")
    st.stop()


# ===== フォント探索 =====
def _resolve_font_path() -> str | None:
    here = Path(__file__).resolve().parent
    candidates = [
        here / "NotoSansJP-Regular.ttf",
        here / "fonts" / "NotoSansJP-Regular.ttf",
        Path.cwd() / "NotoSansJP-Regular.ttf",
        Path.cwd() / "fonts" / "NotoSansJP-Regular.ttf",
    ]
    for p in candidates:
        try:
            # 存在するファイルへの絶対パスを返す
            if p.exists() and p.is_file():
                return str(p.resolve())
        except Exception:
            pass
    return None

# ===== 固定定義 =====
BANKS = ["SBI新生銀行", "三菱UFJ銀行", "PayPay銀行", "じぶん銀行", "住信SBI銀行"]
PLANS = ["一般団信", "がん50", "がん100", "三大疾病", "7大疾病", "全疾病"]

SPECIAL_NOTES = {
    "SBI新生銀行": ["125%ルールなし", "ZEH -0.1%"],
    "三菱UFJ銀行": ["三大疾病50%", "ワイド団信+0.3%"],
    "PayPay銀行":  [ "ソフトバンク割 最大-0.13%", "125%ルールなし"],
    "じぶん銀行":  ["ワイド団信+0.3%", "じぶん割 最大-0.15%"],
    "住信SBI銀行": ["全疾病保障+三大疾病50%標準付帯", "125%ルールなし"],
    "フラット35":    ["上限：1人8000万円,9割まで残りは別融資"],
}

def extra_rate_percent(bank: str, plan: str, age: int) -> float:
    if bank == "SBI新生銀行":
        return 0.1 if plan == "がん100" else 0.0
    if bank == "三菱UFJ銀行":
        return {"がん50": 0.15, "7大疾病": 0.3, "全疾病": 0.5}.get(plan, 0.0)
    if bank == "PayPay銀行":
        return {"がん50": 0.05, "がん100": 0.15}.get(plan, 0.0)
    if bank == "じぶん銀行":
        return {"がん100": 0.054, "7大疾病": 0.1}.get(plan, 0.0)
    # 住信SBI銀行: 7大疾病（全疾病）は標準付帯のため0.0。三大疾病は別途上乗せ金利がつく
    if bank == "住信SBI銀行":
        # 三大疾病は年齢に応じて上乗せ（これは固定金利に対するもので、変動金利では通常は付帯しないか、全疾病が標準付帯）
        # ここではコードの既存ロジックに従い、三大疾病のみ上乗せ金利を適用
        if plan == "三大疾病":
             return 0.2 if age < 40 else 0.4
        return 0.0
    return 0.0

# ===== 保存（Supabase） =====
TABLE_RECORDS  = st.secrets.get("SUPABASE_TABLE_RECORDS", "client_portal_records")

@st.cache_resource(show_spinner=False)
def get_sb():
    # 接続情報がない場合はここでエラー
    if "SUPABASE_URL" not in st.secrets or "SUPABASE_ANON_KEY" not in st.secrets:
        st.error("🚨 Supabase接続情報がst.secretsに見つかりません。")
        st.stop()
    url  = st.secrets["SUPABASE_URL"]
    key  = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)

def load_manual_rates() -> dict:
    """
    Supabase から最新の金利辞書を取得。
    client_id='global', record_type='mortgage_rates' の最新1件を読む。
    返される値はパーセント表記（例: 0.389）または、フラット35のみ小数表記（例: 0.01234）。
    """
    try:
        sb = get_sb()
        res = (
            sb.table(TABLE_RECORDS)
              .select("payload")
              .eq("client_id", "global")
              .eq("record_type", "mortgage_rates")
              .order("created_at", desc=True)
              .limit(1)
              .execute()
        )
        data = getattr(res, "data", []) or []
        if not data:
            return {}
        payload = data[0].get("payload") or {}
        # 期待型に整形（{銀行名:str/float} → float）
        out: Dict[str, float] = {}
        for k, v in payload.items():
            try:
                # フラット35の金利は小数で保存されている前提
                if k in ["flat35_90", "flat35_100"]:
                     out[str(k)] = float(v)
                # 他の銀行の金利はパーセントで保存されている前提
                else:
                    out[str(k)] = float(v)
            except Exception:
                continue
        return out
    except Exception as e:
        st.error(f"金利読込エラー: {e}")
        return {}

def save_manual_rates(d: dict) -> bool:
    """
    入力された金利を Supabase に保存（新規行として append）。
    （d は、通常の銀行はパーセント値、フラット35は小数値が入っている想定）
    """
    try:
        # 既存を読み、差分マージ（空欄は既存を温存）
        current = load_manual_rates()
        merged: Dict[str, Any] = dict(current)
        updated_any = False

        # 通常の銀行の金利（パーセント）とフラット35の金利（小数）を処理
        for bank, val in d.items():
            if val is None:
                continue
            try:
                fv = float(val)
            except Exception:
                continue
            if fv == 0.0: # 0.0 は未設定扱い
                continue
            
            # 変更があったかチェック
            if bank not in merged or float(merged[bank]) != fv:
                merged[bank] = fv
                updated_any = True

        if not updated_any:
            return False

        sb = get_sb()
        row = {
            "client_id": "global",
            "record_type": "mortgage_rates",
            "payload": merged,
            "created_at": datetime.utcnow().isoformat()
        }
        sb.table(TABLE_RECORDS).insert(row).execute()
        return True
    except Exception as e:
        st.error(f"金利保存エラー: {e}")
        return False

# ===== 計算関数 =====
# ===== 計算関数 =====
def sbi_effective_percent(base_percent: float, ltv: float, years: int) -> float:
    """住信SBIネット銀行の金利補正ルールを適用（LTV・年数による上乗せ）"""
    rate = float(base_percent)
    if ltv <= 0.80:
        rate -= 0.09
    elif ltv > 1.00:
        rate += 0.07
    # 借入期間に応じた上乗せ（36〜40年：+0.07%、41年以上：+0.15%）
    if 36 <= years <= 40:
        rate += 0.07
    elif years >= 41:
        rate += 0.15
    return rate

def monthly_payment(principal: float, annual_rate: float, years: int, bank_name: str = "", plan: str = "一般団信") -> float:
    """銀行・プラン・期間別の金利上乗せルールを反映して月々返済額を算出"""

    # --- 基準金利（小数表記） ---
    base_rate = annual_rate

    # --- ① 住信SBIネット銀行 ---
    if "住信" in bank_name:
        if years > 40:
            base_rate += 0.0015  # +0.15%
        elif years > 35:
            base_rate += 0.0007  # +0.07%

    # --- ② PayPay銀行 ---
    if "PayPay" in bank_name:
        if plan in ["がん50", "がん100"]:
            base_rate += 0.001  # +0.1%
        # 期間50年まで対応

    # --- ③ じぶん銀行 ---
    if "じぶん" in bank_name:
        if plan in ["がん100", "7大疾病"]:
            base_rate += 0.001  # +0.1%

    # --- ④ 新生・三菱・フラット35 ---
    if any(b in bank_name for b in ["新生", "三菱", "フラット"]):
        years = min(years, 35)  # 35年超は不可

    # --- ⑤ 一般団信は期間延長しても上乗せなし ---
    if plan == "一般団信":
        pass  # 上乗せなし

    # --- 月々返済計算 ---
    r = base_rate / 12.0
    n = years * 12
    if r == 0:
        return principal / n
    return principal * r / (1 - (1 + r) ** (-n))

def borrowing_limit(income: float, exam_rate: float, ratio: float, age_now: int, years: int = 35, bank_name: str = "") -> int:
    """年収・審査金利・返済比率・年齢・銀行別に借入上限額を算出"""
    # 完済年齢79歳を上限
    max_exam_years = max(1, 79 - age_now)

    # 銀行別上限ルール
    if bank_name in ["SBI新生銀行", "三菱UFJ銀行", "住信SBI銀行"]:
        exam_years = min(35, max_exam_years)
    elif bank_name in ["PayPay銀行", "じぶん銀行"]:
        exam_years = min(years, max_exam_years)  # スライダー値を優先
    else:
        exam_years = min(35, max_exam_years)

    annual = income * ratio
    m = annual / 12
    r = exam_rate / 12
    n = exam_years * 12

    raw = (m * n) if r == 0 else (m * (1 - (1 + r) ** -n) / r)
    return int(raw // 100000 * 100000)

# --- DBから過去保存データを読み込み ---
def load_saved_mortgage(client_id: str):
    try:
        sb = get_sb()
        res = (
            sb.table("mortgage_detail")
              .select("*")
              .eq("client_id", client_id)
              .order("saved_at", desc=True)
              .limit(1)
              .execute()
        )
        if res.data:
            return res.data[0]
    except Exception as e:
        st.warning(f"保存データの読み込み失敗: {e}")
    return None

# ===== UI：基本入力 =====
st.markdown("<h3 style='font-size:22px;'>住宅ローン 提案シミュレーター</h3>", unsafe_allow_html=True)
# ===== 提携金利 見出し =====
st.markdown(
    """
    <div style='margin-top:8px; margin-bottom:10px;'>
        <div style='font-size:21px; font-weight:bold; color:#2B3A67;'>
            💡 TERASSなら、新生銀行・PayPay銀行・auじぶん銀行 提携金利 —
            <span style='color:#1A73E8;'>公式HPと比べてください</span>
        </div>
        <div style='font-size:19px; font-weight:bold; color:#444; margin-top:4px;'>
            他社や個人で申込するよりお得な金利・条件
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ===== 変動・固定 比較ページリンク =====
st.markdown(
    """
    <div style='margin-top:10px; margin-bottom:25px;'>
        <a href='/loan_comparison'
            target='_blank'
            style='display:inline-block;
                     font-size:20px;
                     font-weight:bold;
                     color:#1A73E8;
                     text-decoration:none;
                     border:2px solid #1A73E8;
                     border-radius:8px;
                     padding:10px 18px;
                     background-color:#F7FBFF;'>
            🔍 変動金利・固定金利の比較はこちら
        </a>
    </div>
    """,
    unsafe_allow_html=True
)

# --- DBから過去保存データを読み込み、初期値を設定 ---
client_id = st.query_params.get("client", "unknown")
saved = load_saved_mortgage(client_id)

# 初期値
default_principal = 50000000
default_self_fund = 0
default_annual_income = 10000000
default_age = 35
default_years = 35

# saved データからの初期値設定
principal_init = saved.get("borrow_amount", default_principal) if saved else default_principal
self_fund_init = saved.get("own_fund", default_self_fund) if saved else default_self_fund
annual_income_init = saved.get("income", default_annual_income) if saved else default_annual_income
age_init = saved.get("age", default_age) if saved else default_age
years_init = saved.get("period", default_years) if saved else default_years
# rate_init = saved.get("rate", 0.5) if saved else 0.5 # 未使用

# 物件価格は借入額と自己資金から逆算し、デフォルトで5200万円（5000 + 200）
property_price_init = principal_init + self_fund_init if principal_init + self_fund_init > 0 else 52000000


col1, col2, col3, col4 = st.columns(4)
with col1:
    property_price_input = st.number_input("物件価格 (万円)", min_value=500, max_value=200000, 
                                           value=int(property_price_init / 10000), key="inp_property") * 10000
with col2:
    self_fund = st.number_input("自己資金 (万円)", min_value=0, max_value=100000, 
                                value=int(self_fund_init / 10000), key="inp_self_fund") * 10000
with col3:
    annual_income = st.number_input("年収 (万円)", min_value=100, max_value=10000, 
                                    value=int(annual_income_init / 10000), key="inp_income") * 10000
with col4:
    age = st.number_input("年齢", min_value=18, max_value=80, 
                          value=age_init, key="inp_age")

# 借入額は「物件価格 − 自己資金」で自動計算
principal = property_price_input - self_fund
# 借入額が0以下になる場合は、0にクランプ（実際にはStreamlitのnumber_inputで対応）
principal = max(0, principal) 

max_year = min(79 - int(age), 50)
years = st.slider("返済期間 (年)", min_value=1, max_value=max_year, value=min(years_init, max_year), key="inp_years")
# --- 入力条件の保存ボタン処理 ---
if st.button("💾 入力条件を保存", type="primary"):
    try:
        sb = get_sb()
        # 最新の金利を再度読み込み
        current_rates = load_manual_rates() 

        # rate は住信SBI銀行の金利（パーセント）を想定して保存
        rate_sumishin_sbi = float(current_rates.get("住信SBI銀行", 0.0))
        
        row = {
            "client_id": client_id,
            "borrow_amount": int(principal),
            "own_fund": int(self_fund),
            "income": int(annual_income),
            "age": int(age),
            "period": int(years),
            "rate": rate_sumishin_sbi, # 住信SBI銀行の金利（パーセント）を保存

            # 各銀行の金利（パーセント）を保存
            "rate_sbi_shinsei": float(current_rates.get("SBI新生銀行", 0.0)),
            "rate_mufg": float(current_rates.get("三菱UFJ銀行", 0.0)),
            "rate_paypay": float(current_rates.get("PayPay銀行", 0.0)),
            "rate_jibun": float(current_rates.get("じぶん銀行", 0.0)),
            "rate_sumishin_sbi": rate_sumishin_sbi,

            "saved_at": datetime.utcnow().isoformat()
        }

        res = sb.table("mortgage_detail").insert(row).execute()
        # st.write("🔎 Supabase返却:", res) # ← デバッグ出力はコメントアウト
        st.success("✅ 入力条件と金利を保存しました")

    except Exception as e:
        st.error(f"保存エラー詳細: {e}")
# LTV概算
# LTVは物件価格に対する借入額の比率。物件価格（融資対象）は諸費用を含まない価格を想定
ltv = principal / property_price_input if property_price_input else 1.0


# ===== 金利の読込 =====
rates = load_manual_rates() # rates はパーセント（SBIなど）と小数（フラット35）が混在
_missing = [b for b in BANKS if b not in rates or str(rates.get(b, "")).strip() == ""]
if _missing:
    st.warning("未設定の金利があるため、該当銀行のセルは空欄になります： " + " / ".join(_missing))

# ===== 借入上限額（省略） =====

# ===== 返済額テーブル計算 + 描画付き =====
# ※ sbi_effective_percent / borrowing_limit が上で定義されている必要があります
def build_table(principal: float, years_req: int, age_now: int):
    def cap_years(bank_name: str, req: int, plan: str) -> int:
        """銀行・プラン別に返済年数を決定"""
        # フラット35 → 常に35年固定
        if bank_name == "フラット35":
            return 35
        # 銀行固有制限（SBI新生銀行・三菱UFJ銀行）は最大35年
        elif bank_name in ["SBI新生銀行", "三菱UFJ銀行"]:
            return min(req, 35)
        # 一般団信 → 最大35年（79歳完済も考慮）
        elif plan == "一般団信":
            return min(req, 35, 79 - age_now)
        # がん・疾病系 → スライダー値を尊重（ただし79歳完済上限）
        elif plan in ["がん50", "がん100", "三大疾病", "7大疾病", "全疾病"]:
            return min(req, 79 - age_now)
        # その他 → スライダー値をそのまま
        else:
            return req

    table_rows_local = []
    highlights_local = []

    # ===== 各プラン行（一般団信〜疾病系） =====
    for plan in PLANS:
        row = []
        vals = []
        for col_idx, bank in enumerate(BANKS):
            if principal > limits.get(bank, float("inf")):
                row.append({"rate": None, "monthly": None, "years": None})
                continue
            if bank not in rates:
                row.append({"rate": None, "monthly": None, "years": None})
                continue
            if plan != "一般団信" and extra_rate_percent(bank, plan, age_now) == 0.0:
                row.append({"rate": None, "monthly": None, "years": None})
                continue

            # ✅ 年数ロジック統一
            y = cap_years(bank, years_req, plan)

            try:
                base_percent_saved = float(rates[bank])
            except Exception:
                row.append({"rate": None, "monthly": None, "years": None})
                continue

            # ✅ 銀行別金利調整
            if bank == "住信SBI銀行":
                eff_pct = sbi_effective_percent(base_percent_saved, ltv, y)
                base = eff_pct / 100.0
            else:
                base = base_percent_saved / 100.0
                if bank in ["PayPay銀行", "じぶん銀行"] and y > 35:
                    base += 0.10 / 100.0

            add = extra_rate_percent(bank, plan, age_now) / 100.0
            m = monthly_payment(principal, base + add, y)
            row.append({"rate": base + add, "monthly": m, "years": y})
            vals.append((col_idx, m))

        # ===== フラット35列 =====
        col_idx = len(BANKS)
        if plan == "一般団信":
            if principal > 8000 * 10000:
                row.append({"rate": None, "monthly": None, "years": None})
            else:
                borrowing_ratio = principal / property_price_input
                y_flat = 35
                base_flat_rate = 0.0189
                if borrowing_ratio <= 0.90:
                    if "flat35_90" in rates and rates["flat35_90"] is not None:
                        base_flat_rate = float(rates["flat35_90"])
                else:
                    if "flat35_100" in rates and rates["flat35_100"] is not None:
                        base_flat_rate = float(rates["flat35_100"])
                base_flat = base_flat_rate
                m_flat = monthly_payment(principal, base_flat, y_flat)
                row.append({"rate": base_flat, "monthly": m_flat, "years": y_flat})
                vals.append((col_idx, m_flat))
        else:
            row.append({"rate": None, "monthly": None, "years": None})

        # ✅ 最小返済額ハイライト処理
        mins = set()
        if vals:
            mv = min(v for _, v in vals)
            for idx, v in vals:
                if abs(v - mv) < 0.5:
                    mins.add(idx)

        table_rows_local.append(row)
        highlights_local.append(mins)

    # ===== 最長50年行（スライダー上限 or 79歳完済上限） =====
    row50_local = []
    vals50 = []
    for col_idx, bank in enumerate(BANKS):
        # 新生・三菱は35年まで
        if bank in ["SBI新生銀行", "三菱UFJ銀行"]:
            row50_local.append({"rate": None, "monthly": None, "years": None})
            continue
        if principal > limits.get(bank, float("inf")) or bank not in rates:
            row50_local.append({"rate": None, "monthly": None, "years": None})
            continue

        # ✅ 年齢制限（79歳完済）を考慮
        y50 = min(79 - age_now, 50)
        try:
            base_percent_saved = float(rates[bank])
        except Exception:
            row50_local.append({"rate": None, "monthly": None, "years": None})
            continue
        if bank == "住信SBI銀行":
            # ✅ 住信SBIネット銀行：期間補正は sbi_effective_percent に一本化
            eff_pct = sbi_effective_percent(base_percent_saved, ltv, y50)
            base = eff_pct / 100.0
        else:
            base = base_percent_saved / 100.0
            if bank in ["PayPay銀行", "じぶん銀行"] and y50 > 35:
                base += 0.10 / 100.0

        add = extra_rate_percent(bank, "一般団信", age_now) / 100.0
        m50 = monthly_payment(principal, base + add, y50)
        row50_local.append({"rate": base + add, "monthly": m50, "years": y50})
        vals50.append((col_idx, m50))

    # フラット35は空欄
    row50_local.append({"rate": None, "monthly": None, "years": None})

    # ✅ 最小返済額ハイライト
    mins50 = set()
    if vals50:
        mv50 = min(v for _, v in vals50)
        for idx, v in vals50:
            if abs(v - mv50) < 0.5:
                mins50.add(idx)

    return table_rows_local, highlights_local, row50_local, mins50

# ===== UI：借入上限額（再表示） =====
# ... (既存の借入上限額の計算とHTML表示のロジック) ...
# ※ 借入上限額の表示は既存のコードと重複するため省略（ただし、修正は不要です）

# --- 借入上限額表示の再計算 ---
banks_exam = {
    "SBI新生銀行": {"審査金利": 0.03,    "返済比率": 0.40},
    "三菱UFJ銀行": {"審査金利": 0.0354, "返済比率": 0.35},
    "PayPay銀行":  {"審査金利": 0.03,    "返済比率": 0.40},
    "じぶん銀行":  {"審査金利": 0.0257, "返済比率": 0.35},
    "住信SBI銀行": {"審査金利": 0.0325, "返済比率": 0.35},
    "フラット35":    {"審査金利": 0.035,  "返済比率": None}, 
}
limits = {}
rows_limit_html = []

# フラット35 の返済比率を年収に応じて設定
for bank, info in banks_exam.items():
    if bank == "フラット35":
        if annual_income < 4_000_000:
            info["返済比率"] = 0.30
        else:
            info["返済比率"] = 0.35

for bank, info in banks_exam.items():
    # ✅ 銀行ごとに審査年数を設定して借入上限額を算出
    if bank in ["PayPay銀行", "じぶん銀行"]:
        # スライダーの返済期間（years）を反映（最大50年まで）
        lim = borrowing_limit(annual_income, info["審査金利"], info["返済比率"], int(age), years, bank)
    elif bank in ["SBI新生銀行", "三菱UFJ銀行", "住信SBI銀行"]:
        # スライダーが短ければその年数、長くても35年上限
        lim = borrowing_limit(annual_income, info["審査金利"], info["返済比率"], int(age), years, bank)
    else:
        # フラット35は常に35年固定
        lim = borrowing_limit(annual_income, info["審査金利"], info["返済比率"], int(age), 35, bank)
    limits[bank] = lim
    rows_limit_html.append((bank, f"{int(lim // 10000):,} 万円"))

st.subheader("💰 年収からの借入上限額")
st.markdown(
    "<style>.blimit th, .blimit td {border:1.2px solid #aaa; padding:12px; font-size:18px;} .blimit th{background:#F2F6FA;} .blimit{border-collapse:collapse; width:480px; margin-bottom:20px;}</style>",
    unsafe_allow_html=True
)
tbl = "<table class='blimit'><thead><tr><th style='width:250px;text-align:center'>銀行名</th><th style='width:230px;text-align:center'>借入上限額</th></tr></thead><tbody>"
url_map = {
    "SBI新生銀行": "https://naokifp.streamlit.app/SBI_Shinssei",
    "三菱UFJ銀行": "https://naokifp.streamlit.app/MUFG",
    "PayPay銀行": "https://naokifp.streamlit.app/PayPay",
    "じぶん銀行": "https://naokifp.streamlit.app/Jibun",
    "住信SBI銀行": "https://naokifp.streamlit.app/SumishinSBI",
}
for bank, val in rows_limit_html:
    # フラット35のみ公式サイトリンクを付与
    if bank == "フラット35":
        url = "https://www.sbiaruhi.co.jp/product/flat35/"
    else:
        url = url_map.get(bank, "#")
    
    tbl += f"<tr><td align='center'><a href='{url}' target='_blank' style='color:#226BB3;text-decoration:none;font-weight:bold;'>{bank}</a></td><td align='right'>{val}</td></tr>"

tbl += "</tbody></table>"
st.markdown(tbl, unsafe_allow_html=True)
st.markdown("<div style='font-size:13px;color:#666;margin-top:6px;'>※フラット35※1人上限8,000万円</div>", unsafe_allow_html=True)


# ===== 返済額テーブル計算 + 描画付き（再実行） =====
table_rows, highlights, row50, mins50 = build_table(principal, years, age)

# ===== HTML 描画部（省略） =====
# ... (既存の HTML 描画ロジック) ...
def td_cell(d: dict, is_min: bool, wcss: str) -> str:
    r, m, y = d["rate"], d["monthly"], d["years"]
    base = "text-align:center;vertical-align:middle;"
    bg = "background-color:#FFF8C8;" if is_min else ""
    if r is None:
        return f"<td style='{wcss}{base}'></td>"
    return (
        f"<td style='{wcss}height:68px;{base}{bg}'>"
        f"<div style='font-size:22px;font-weight:bold;color:#1B232A'>{r*100:.3f}%</div>"
        f"<div style='font-size:22px;font-weight:bold;color:#226BB3'>¥{m:,.0f}</div>"
        f"<div style='font-size:14px;color:#666;'>({y}年返済)</div>"
        f"</td>"
    )

plan_w = "min-width:220px;max-width:220px;width:220px;"
bank_w = "min-width:180px;max-width:180px;width:180px;"
html = """
<style>
.loan-table, .loan-table th, .loan-table td {border:1.2px solid #aaa; border-collapse: collapse;}
.loan-table th, .loan-table td {padding: 13px;}
.loan-table {background-color:#fff; width:100%; table-layout:fixed;}
.loan-table th {background-color:#F2F6FA; font-size:18px;}
.loan-table td {font-size:18px;}
</style>
<table class="loan-table">
<thead><tr>
"""
html += f"<th style='{plan_w}text-align:center;font-size:18px;'>プラン</th>"
for b in BANKS + ["フラット35"]:
    label = b 
    html += f"<th style='{bank_w}text-align:center;font-size:18px'>{label}</th>"
html += "</tr></thead><tbody>"

for i, plan in enumerate(PLANS):
    html += f"<tr><td style='{plan_w}text-align:center;font-weight:bold;font-size:18px;'>{plan}</td>"
    for col_idx in range(len(BANKS) + 1):
        # 修正: table_rowsの範囲チェック
        if i < len(table_rows) and col_idx < len(table_rows[i]):
            cell = table_rows[i][col_idx]
            # 修正: highlightsの範囲チェックとNoneチェック
            is_min_highlighted = (col_idx in highlights[i] and cell is not None and cell.get('monthly') is not None)
            html += td_cell(cell, is_min_highlighted, bank_w)
        else:
             html += f"<td style='{bank_w}text-align:center;vertical-align:middle;'></td>" # データなしの場合
             
    if plan == "一般団信":
        html += "<tr>"
        html += f"<td style='{plan_w}text-align:center;font-weight:bold;font-size:17px;background-color:#F9F6EF;'>最長50年</td>"
        for col_idx in range(len(BANKS) + 1):
            if col_idx < len(row50):
                c50 = row50[col_idx]
                is_min_highlighted_50 = (col_idx in mins50 and c50 is not None and c50.get('monthly') is not None)
                html += td_cell(c50, is_min_highlighted_50, bank_w)
            else:
                 html += f"<td style='{bank_w}text-align:center;vertical-align:middle;'></td>" # データなしの場合
        html += "</tr>"

html += "<tr>"
html += f"<td style='{plan_w}text-align:center;font-weight:bold;font-size:14px;background-color:#FCF9F0;'>特記事項</td>"
for b in BANKS + ["フラット35"]:
    html += f"<td style='{bank_w}font-size:13px;text-align:left;vertical-align:top;background-color:#FCF9F0;padding:20px 6px;line-height:1.7;'>{'<br>'.join(SPECIAL_NOTES.get(b, []))}</td>"
html += "</tr></tbody></table>"


st.markdown(html, unsafe_allow_html=True)
# ===== PDF出力 =====
def _pdf_to_bytesio(pdf) -> io.BytesIO:
    pdf_bytes = pdf.output(dest="S")
    if isinstance(pdf_bytes, memoryview):
        pdf_bytes = pdf_bytes.tobytes()
    elif not isinstance(pdf_bytes, (bytes, bytearray)):
        pdf_bytes = bytes(pdf_bytes)
    out = io.BytesIO(pdf_bytes)
    out.seek(0)
    return out

def create_pdf() -> io.BytesIO:
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    resolved = _resolve_font_path()
    if not resolved:
        raise FileNotFoundError("PDF用フォントが見つかりません")
    pdf.add_font("NotoSansJP", "", resolved, uni=True)
    pdf.set_font("NotoSansJP", size=14)

    # タイトル
    pdf.cell(0, 10, txt="住宅ローン提案書", ln=1, align="C")
    pdf.set_font("NotoSansJP", size=11)
    pdf.cell(0, 8, txt=f"■ 借入金額：¥{principal:,.0f}", ln=1, align="C")
    pdf.ln(2)

    plan_w_mm = 45
    bank_w_mm = 40
    line_h = 5.4
    cell_h = line_h * 3
    x_left = 10
    y_top = pdf.get_y()

    # ヘッダー
    pdf.set_font("NotoSansJP", size=10)
    pdf.set_fill_color(242, 246, 250)
    pdf.rect(x_left, y_top, plan_w_mm, 10, style="F")
    pdf.rect(x_left, y_top, plan_w_mm, 10)
    pdf.set_xy(x_left, y_top)
    pdf.multi_cell(plan_w_mm, 10, "プラン", align="C", border=0)

    x = x_left + plan_w_mm
    for b in BANKS + ["フラット35"]:
        pdf.rect(x, y_top, bank_w_mm, 10, style="F")
        pdf.rect(x, y_top, bank_w_mm, 10)
        pdf.set_xy(x, y_top)
        pdf.multi_cell(bank_w_mm, 10, b, align="C", border=0)
        x += bank_w_mm

    y_cursor = y_top + 10

    def _cell_text(d: dict):
        if d["rate"] is None:
            return ["", "", ""]
        return [f"{d['rate']*100:.3f}%", f"¥{d['monthly']:,.0f}", f"({d['years']}年)"]

    def _draw_row(label: str, cells: list[dict], y: float, fill_rgb=None, label_fill=None):
        if label_fill:
            pdf.set_fill_color(*label_fill)
            pdf.rect(x_left, y, plan_w_mm, cell_h, style="F")
        pdf.rect(x_left, y, plan_w_mm, cell_h)
        pdf.set_xy(x_left, y + (cell_h - line_h) / 2)
        pdf.multi_cell(plan_w_mm, line_h, label, align="C", border=0)

        x = x_left + plan_w_mm
        for col_idx, d in enumerate(cells):
            if fill_rgb:
                pdf.set_fill_color(*fill_rgb)
                pdf.rect(x, y, bank_w_mm, cell_h, style="F")
            pdf.rect(x, y, bank_w_mm, cell_h)
            t1, t2, t3 = _cell_text(d)
            pdf.set_xy(x, y)
            pdf.multi_cell(bank_w_mm, line_h, t1, align="C", border=0)
            pdf.set_xy(x, y + line_h)
            pdf.multi_cell(bank_w_mm, line_h, t2, align="C", border=0)
            pdf.set_xy(x, y + 2 * line_h)
            pdf.multi_cell(bank_w_mm, line_h, t3, align="C", border=0)
            x += bank_w_mm

    pdf.set_font("NotoSansJP", size=10)
    for i, plan in enumerate(PLANS):
        _draw_row(plan, table_rows[i], y_cursor)
        y_cursor += cell_h
        if plan == "一般団信":
            _draw_row("最長50年", row50, y_cursor, fill_rgb=(249, 246, 239), label_fill=(249, 246, 239))
            y_cursor += cell_h

    # 特記事項  
    pdf.set_font("NotoSansJP", size=9)  
    notes_line_h = 5.6  
    pad_v = 2.0  
    max_lines = max(len(SPECIAL_NOTES.get(b, [])) for b in BANKS + ["フラット35"])  
    notes_h = max_lines * notes_line_h + pad_v * 2.0 + 7.0  
    y_notes = y_cursor + 1.5  

    pdf.set_fill_color(252, 249, 240)  
    pdf.rect(x_left, y_notes, plan_w_mm, notes_h, style="F")  
    pdf.rect(x_left, y_notes, plan_w_mm, notes_h)  
    pdf.set_xy(x_left, y_notes + (notes_h - notes_line_h) / 2)  
    pdf.multi_cell(plan_w_mm, notes_line_h, "特記事項", align="C", border=0)  

    x = x_left + plan_w_mm  
    for b in BANKS + ["フラット35"]:  
        txt = "\n".join(SPECIAL_NOTES.get(b, []))  
        pdf.rect(x, y_notes, bank_w_mm, notes_h, style="F")  
        pdf.rect(x, y_notes, bank_w_mm, notes_h)  
        pdf.set_xy(x + 1, y_notes + pad_v)  
        pdf.multi_cell(bank_w_mm - 2, notes_line_h, txt, align="L", border=0)  
        x += bank_w_mm  

    # ✅ これを追加（戻り値）
    return _pdf_to_bytesio(pdf)
    
# ===== PDFダウンロードボタン =====
try:
    pdf_bytes = create_pdf()
    st.download_button(
        label="📄 PDFをダウンロード",
        data=pdf_bytes,
        file_name="住宅ローン提案書.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
except Exception as e:
    st.error(f"PDF生成エラー: {e}")

# ===== 金利修正（パスワード一致で表示） =====
st.markdown("---")
pwd = st.text_input("🔒 営業担当パスワード", type="password", key="pwd_rates_edit")
exp_open = (pwd == "naoki0510")

with st.expander("🔧 金利を修正する（営業担当専用）", expanded=exp_open):
    if not exp_open:
        st.info("パスワードが一致すると編集欄が開きます。")
    else:
        bank_key_map = {
            "SBI新生銀行": "mortgage_rate_sbi_shinsei",
            "三菱UFJ銀行": "mortgage_rate_mufg",
            "PayPay銀行":  "mortgage_rate_paypay",
            "じぶん銀行":  "mortgage_rate_jibun",
            "住信SBI銀行": "mortgage_rate_sumishin_sbi",
        }

        current_saved = load_manual_rates()
        cols = st.columns(len(BANKS))
        new_rates_dict = {}

        for bank, col in zip(BANKS, cols):
            with col:
                key = bank_key_map[bank]
                # 初期値はパーセント表記で表示
                init_str = "" if bank not in current_saved else f"{float(current_saved[bank]):.3f}"
                s = st.text_input(
                    f"{bank}（年利％）",
                    value=init_str,
                    key=key,
                    placeholder="未設定（例: 0.389）"
                )
                try:
                    # 通常の銀行はパーセント値のまま保存 (既存のロジックを維持)
                    new_rates_dict[bank] = float(s) if s.strip() != "" else None
                except Exception:
                    new_rates_dict[bank] = None

        # フラット35 用 90%、100% の金利入力欄を追加
        col90, col100 = st.columns(2)
        with col90:
            # 初期値は小数で保存されているので、パーセントに戻して表示
            init_val = current_saved.get('flat35_90')
            init_str = "" if init_val is None else f"{float(init_val) * 100.0:.3f}"
            s90 = st.text_input(
                "フラット35（90%用 年利％）",
                value=init_str,
                key="flat35_rate_90",
                placeholder="例: 1.234"
            )
            try:
                # 修正: 入力されたパーセントを小数（0.0XX）に変換して保存
                new_rates_dict["flat35_90"] = float(s90) / 100.0 if s90.strip() != "" else None
            except:
                new_rates_dict["flat35_90"] = None

        with col100:
            # 初期値は小数で保存されているので、パーセントに戻して表示
            init_val = current_saved.get('flat35_100')
            init_str = "" if init_val is None else f"{float(init_val) * 100.0:.3f}"
            s100 = st.text_input(
                "フラット35（100%用 年利％）",
                value=init_str,
                key="flat35_rate_100",
                placeholder="例: 1.567"
            )
            try:
                # 修正: 入力されたパーセントを小数（0.0XX）に変換して保存
                new_rates_dict["flat35_100"] = float(s100) / 100.0 if s100.strip() != "" else None
            except:
                new_rates_dict["flat35_100"] = None

        st.markdown("")
        if st.button("💾 金利を保存", type="primary", key="btn_rates_save"):
            ok = save_manual_rates(new_rates_dict)
            if ok:
                st.success("✅ 金利を保存しました（上部の表にも反映されます）")
                # 成功した場合はUIを再描画して最新の金利をロード
                st.experimental_rerun()
            else:
                st.info("ℹ️ 入力に変更がなかったため保存していません")
