# /pages/住宅ローン提案.py
# 住宅ローン 提案シミュレーター（reportlab不使用 / fpdf2版）
# 要件：
# - st.session_state は一切参照しない
# - “初期値に戻す” 概念なし（保存が無ければエラーで停止）
# - 保存は「金利を保存」ボタンでのみ
# - パスワード一致後に編集UIを表示（状態フラグ不使用）
# - 直感的な固定キー（ASCII）のみ使用

import os
import io
import json
from pathlib import Path

import streamlit as st
from fpdf import FPDF
from client_portal import db_insert_record, now_iso
from auth import login_ui


# ===== 画面設定 =====
st.set_page_config(page_title="住宅ローン 提案シミュレーター", layout="wide")
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
            if p.exists() and p.is_file():
                return str(p.resolve())
        except Exception:
            pass
    return None

# ===== 固定定義 =====
BANKS = ["SBI新生銀行", "三菱UFJ銀行", "PayPay銀行", "じぶん銀行", "住信SBI銀行"]
PLANS = ["一般団信", "がん50", "がん100", "三大疾病", "7大疾病", "全疾病"]

# 既存の SPECIAL_NOTES 辞書（例として）
# SPECIAL_NOTES = {
#     "みずほ銀行": ["金利優遇に条件あり"],
#     "三井住友銀行": ["保証料が別途必要"],
#     # ... 他の銀行 ...
#     "フラット35": ["機構団信に加入が必須"] # もし既存の記述があれば
# }

# 修正後の SPECIAL_NOTES 辞書 (データを追加)
if "フラット35" not in SPECIAL_NOTES:
    SPECIAL_NOTES["フラット35"] = []

# フラット35の特記事項リストに新しい項目を追加
SPECIAL_NOTES["フラット35"].append("融資上限は1人あたり8,000万円までです。")

def extra_rate_percent(bank: str, plan: str, age: int) -> float:
    if bank == "SBI新生銀行":
        return 0.1 if plan == "がん100" else 0.0
    if bank == "三菱UFJ銀行":
        return {"がん50": 0.15, "7大疾病": 0.3, "全疾病": 0.5}.get(plan, 0.0)
    if bank == "PayPay銀行":
        return {"がん50": 0.05, "がん100": 0.15}.get(plan, 0.0)
    if bank == "じぶん銀行":
        return {"がん100": 0.054, "7大疾病": 0.1}.get(plan, 0.0)
    if bank == "住信SBI銀行":
        return (0.2 if age < 40 else 0.4) if plan == "三大疾病" else 0.0
    return 0.0

# ===== 保存（PostgreSQL / Supabase） =====
# ※ 直Postgres接続（psycopg2）をやめ、Supabase REST（anon key）で保存/読込します
#    これで 5432 接続エラーを根本回避します（Cloudでも安定）

from datetime import datetime
from typing import Dict, Any
from supabase import create_client
import streamlit as st

# 使うテーブル：client_portal_records（既に作成済み）
# record_type = 'mortgage_rates' に、payload として {銀行名: 金利%} を保存
TABLE_RECORDS  = st.secrets.get("SUPABASE_TABLE_RECORDS", "client_portal_records")

@st.cache_resource(show_spinner=False)
def get_sb():
    url  = st.secrets["SUPABASE_URL"]
    key  = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)

def load_manual_rates() -> dict:
    """
    Supabase から最新の金利辞書を取得。
    client_id='global', record_type='mortgage_rates' の最新1件を読む。
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
    仕様:
      - 空欄(None)や不正値は無視
      - 0.0 は保存しない（未設定扱い）
      - 何も有効値がなければ False
    """
    try:
        # 既存を読み、差分マージ（空欄は既存を温存）
        current = load_manual_rates()
        merged: Dict[str, Any] = dict(current)
        updated_any = False
        for bank, val in d.items():
            if val is None:
                continue
            try:
                fv = float(val)
            except Exception:
                continue
            if fv == 0.0:
                continue
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
def monthly_payment(principal: float, annual_rate: float, years: int) -> float:
    r = annual_rate / 12.0
    n = years * 12
    if r == 0:
        return principal / n
    return principal * r / (1 - (1 + r) ** (-n))

def sbi_effective_percent(base_percent: float, ltv: float, years: int) -> float:
    rate = float(base_percent)
    if ltv <= 0.80:
        rate += -0.09
    elif ltv > 1.00:
        rate += 0.07
    if 36 <= years <= 40:
        rate += 0.07
    elif years >= 41:
        rate += 0.15
    return rate

def borrowing_limit(income: float, exam_rate: float, ratio: float, age_now: int) -> int:
    exam_years = min(35, 79 - age_now)
    annual = income * ratio
    m = annual / 12
    r = exam_rate / 12
    n = exam_years * 12
    raw = (m * n) if r == 0 else (m * (1 - (1 + r) ** -n) / r)
    return int(raw // 100000 * 100000)

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

client_id = st.query_params.get("client", "unknown")
saved = load_saved_mortgage(client_id)

if saved:
    principal = saved.get("borrow_amount", 50000000)  # 借入額
    self_fund = saved.get("own_fund", 0)              # 自己資金
    annual_income = saved.get("income", 0)            # 年収
    age = saved.get("age", 35)                        # 年齢
    years = saved.get("period", 35)                   # 返済期間
    rate = saved.get("rate", 0.5)                     # 金利

col1, col2, col3, col4 = st.columns(4)
with col1:
    property_price_input = st.number_input("物件価格 (万円)", min_value=500, max_value=200000, value=5000, key="inp_property") * 10000
with col2:
    self_fund = st.number_input("自己資金 (万円)", min_value=0, max_value=100000, value=200, key="inp_self_fund") * 10000
with col3:
    annual_income = st.number_input("年収 (万円)", min_value=100, max_value=10000, value=1000, key="inp_income") * 10000
with col4:
    age = st.number_input("年齢", min_value=18, max_value=80, value=35, key="inp_age")

# 借入額は「物件価格 − 自己資金」で自動計算
principal = property_price_input - self_fund

max_year = max(1, 79 - int(age))
years = st.slider("返済期間 (年)", min_value=1, max_value=max_year, value=min(35, max_year), key="inp_years")
if st.button("💾 入力条件を保存", type="primary"):
    try:
        sb = get_sb()
        current_rates = load_manual_rates()

        row = {
            "client_id": client_id,
            "borrow_amount": int(principal),
            "own_fund": int(self_fund),
            "income": int(annual_income),
            "age": int(age),
            "period": int(years),
            "rate": float(current_rates.get("住信SBI銀行", 0.0)),

            "rate_sbi_shinsei": float(current_rates.get("SBI新生銀行", 0.0)),
            "rate_mufg": float(current_rates.get("三菱UFJ銀行", 0.0)),
            "rate_paypay": float(current_rates.get("PayPay銀行", 0.0)),
            "rate_jibun": float(current_rates.get("じぶん銀行", 0.0)),
            "rate_sumishin_sbi": float(current_rates.get("住信SBI銀行", 0.0)),

            "saved_at": datetime.utcnow().isoformat()
        }

        res = sb.table("mortgage_detail").insert(row).execute()
        st.write("🔎 Supabase返却:", res)   # ← デバッグ出力
        st.success("✅ 入力条件と金利を保存しました")

    except Exception as e:
        st.error(f"保存エラー詳細: {e}")
# LTV概算
property_price_guess = (principal + self_fund) / 1.07 if 1.07 != 0 else (principal + self_fund)
ltv = principal / property_price_guess if property_price_guess else 1.0

# ===== 金利の読込 =====
rates = load_manual_rates()
_missing = [b for b in BANKS if b not in rates or str(rates.get(b, "")).strip() == ""]
if _missing:
    st.warning("未設定の金利があるため、該当銀行のセルは空欄になります： " + " / ".join(_missing))

# ===== 借入上限額 =====
banks_exam = {
    "SBI新生銀行": {"審査金利": 0.03,   "返済比率": 0.40},
    "三菱UFJ銀行": {"審査金利": 0.0354, "返済比率": 0.35},
    "PayPay銀行":  {"審査金利": 0.03,   "返済比率": 0.40},
    "じぶん銀行":  {"審査金利": 0.0257, "返済比率": 0.35},
    "住信SBI銀行": {"審査金利": 0.0325, "返済比率": 0.35},
    "フラット35":    {"審査金利": 0.035,  "返済比率": None},  # 返済比率は年収で設定
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
    lim = borrowing_limit(annual_income, info["審査金利"], info["返済比率"], int(age))
    limits[bank] = lim
    rows_limit_html.append((bank, f"{int(lim // 10000):,} 万円"))

st.subheader("💰 年収からの借入上限額")
st.markdown(
    "<style>.blimit th, .blimit td {border:1.2px solid #aaa; padding:12px; font-size:18px;} .blimit th{background:#F2F6FA;} .blimit{border-collapse:collapse; width:480px; margin-bottom:20px;}</style>",
    unsafe_allow_html=True
)
tbl = "<table class='blimit'><thead><tr><th style='width:250px;text-align:center'>銀行名</th><th style='width:230px;text-align:center'>借入上限額</th></tr></thead><tbody>"
for bank, val in rows_limit_html:
    # 銀行リンクマップを追加してリンク化
    url_map = {
        "SBI新生銀行": "https://naokifp.streamlit.app/SBI_Shinssei",
        "三菱UFJ銀行": "https://naokifp.streamlit.app/MUFG",
        "PayPay銀行": "https://naokifp.streamlit.app/PayPay",
        "じぶん銀行": "https://naokifp.streamlit.app/Jibun",
        "住信SBI銀行": "https://naokifp.streamlit.app/SumishinSBI",
    }
    url = url_map.get(bank, "#")
    tbl += f"<tr><td align='center'><a href='{url}' target='_blank' style='color:#226BB3;text-decoration:none;font-weight:bold;'>{bank}</a></td><td align='right'>{val}</td></tr>"

tbl += "</tbody></table>"
st.markdown(tbl, unsafe_allow_html=True)
st.markdown("<div style='font-size:13px;color:#666;margin-top:6px;'>※フラット35※1人上限8,000万円</div>", unsafe_allow_html=True)



# ===== 返済額テーブル計算 + 描画付き =====
def build_table(principal: float, years_req: int, age_now: int):
    def cap_years(bank_name: str, req: int) -> int:
        y = min(79 - age_now, req)
        if bank_name in ["SBI新生銀行", "三菱UFJ銀行"]:
            y = min(y, 35)
        return y

    table_rows_local = []
    highlights_local = []

    for plan in PLANS:
        row = []
        vals = []
        # 銀行ごとの列
        for bank in BANKS:
            if principal > limits.get(bank, 0):
                row.append({"rate": None, "monthly": None, "years": None})
                continue
            if bank not in rates:
                row.append({"rate": None, "monthly": None, "years": None})
                continue
            if plan != "一般団信" and extra_rate_percent(bank, plan, age_now) == 0.0:
                row.append({"rate": None, "monthly": None, "years": None})
                continue

            y = cap_years(bank, years_req)
            try:
                base_percent_saved = float(rates[bank])
            except:
                row.append({"rate": None, "monthly": None, "years": None})
                continue

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
            vals.append((len(row) - 1, m))

                # フラット35は「一般団信のみ」計算、それ以外は空欄
        if plan == "一般団信":
            if principal > 8000 * 10000:  # 借入額が8000万円を超えると空欄
                row.append({"rate": None, "monthly": None, "years": None})
            else:
                # 借入比率で金利を判定
                borrowing_ratio = principal / property_price_input

                y_flat = cap_years("フラット35", years_req)
                if borrowing_ratio <= 0.90 and "flat35_90" in rates:
                    base_flat = float(rates["flat35_90"])  # ← ここで小数（例: 0.015）が入っている
                elif "flat35_100" in rates:
                    base_flat = float(rates["flat35_100"])
                else:
                    base_flat = 0.0189  # デフォルト（1.89%）

                add_flat = 0.0
                m_flat = monthly_payment(principal, base_flat + add_flat, y_flat)

                row.append({
                    "rate": base_flat + add_flat,
                    "monthly": m_flat,
                    "years": y_flat
                })
                vals.append((len(row) - 1, m_flat))
        else:
            row.append({"rate": None, "monthly": None, "years": None})
        # 最小返済額の強調
        mins = set()
        if vals:
            mv = min(v for _, v in vals)
            for idx, v in vals:
                if abs(v - mv) < 0.5:
                    mins.add(idx)

        table_rows_local.append(row)
        highlights_local.append(mins)

    # ===== 最長50年行 =====
    row50_local = []
    vals50 = []
    for bank in BANKS:
        if bank in ["SBI新生銀行", "三菱UFJ銀行"]:
            row50_local.append({"rate": None, "monthly": None, "years": None})
            continue
        if principal > limits.get(bank, 0):
            row50_local.append({"rate": None, "monthly": None, "years": None})
            continue
        if bank not in rates:
            row50_local.append({"rate": None, "monthly": None, "years": None})
            continue

        y50 = min(79 - age_now, 50)
        try:
            base_percent_saved = float(rates[bank])
        except:
            row50_local.append({"rate": None, "monthly": None, "years": None})
            continue

        if bank == "住信SBI銀行":
            eff_pct = sbi_effective_percent(base_percent_saved, ltv, y50)
            base = eff_pct / 100.0
        else:
            base = base_percent_saved / 100.0
            if bank in ["PayPay銀行", "じぶん銀行"] and y50 > 35:
                base += 0.10 / 100.0

        add = extra_rate_percent(bank, "一般団信", age_now) / 100.0
        m50 = monthly_payment(principal, base + add, y50)
        row50_local.append({"rate": base + add, "monthly": m50, "years": y50})
        vals50.append((len(row50_local) - 1, m50))

    # フラット35の50年欄は常に空欄
    row50_local.append({"rate": None, "monthly": None, "years": None})

    mins50 = set()
    if vals50:
        mv50 = min(v for _, v in vals50)
        for idx, v in vals50:
            if abs(v - mv50) < 0.5:
                mins50.add(idx)

    return table_rows_local, highlights_local, row50_local, mins50


# ===== HTML 描画部 =====
table_rows, highlights, row50, mins50 = build_table(principal, years, age)

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
    label = b  # ← フラット35もそのまま表示
    html += f"<th style='{bank_w}text-align:center;font-size:18px'>{label}</th>"
html += "</tr></thead><tbody>"

for i, plan in enumerate(PLANS):
    html += f"<tr><td style='{plan_w}text-align:center;font-weight:bold;font-size:18px;'>{plan}</td>"
    for col_idx in range(len(BANKS) + 1):
        cell = table_rows[i][col_idx]
        html += td_cell(cell, (col_idx in highlights[i] and cell['monthly'] is not None), bank_w)
    if plan == "一般団信":
        html += "<tr>"
        html += f"<td style='{plan_w}text-align:center;font-weight:bold;font-size:17px;background-color:#F9F6EF;'>最長50年</td>"
        for col_idx in range(len(BANKS) + 1):
            c50 = row50[col_idx]
            html += td_cell(c50, (col_idx in mins50 and c50['monthly'] is not None), bank_w)
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
        header_label = b
        if b == "フラット35":
            header_label = "フラット35\n※1人上限8,000万"
        pdf.multi_cell(bank_w_mm, 10, header_label, align="C", border=0)
        x += bank_w_mm

    y_cursor = y_top + 10

    def _cell_text(d: dict):
        if d["rate"] is None:
            return ["", "", ""]
        return [f"{d['rate']*100:.3f}%", f"¥{d['monthly']:,.0f}", f"({d['years']}年)"]

    def _draw_row(label: str, cells: list[dict], y: float, fill_rgb: tuple | None = None, label_fill: tuple | None = None):
        if label_fill:
            pdf.set_fill_color(*label_fill)
            pdf.rect(x_left, y, plan_w_mm, cell_h, style="F")
        pdf.rect(x_left, y, plan_w_mm, cell_h)
        pdf.set_xy(x_left, y + (cell_h - line_h) / 2)
        pdf.multi_cell(plan_w_mm, line_h, label, align="C", border=0)

        x = x_left + plan_w_mm
        if fill_rgb:
            pdf.set_fill_color(*fill_rgb)
        for d in cells:
            if fill_rgb:
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
    notes_line_h = 5.2
    pad_v = 1.5
    max_lines = max(len(SPECIAL_NOTES.get(b, [])) for b in BANKS + ["フラット35"])
    notes_h = max_lines * notes_line_h + pad_v * 2
    y_notes = y_cursor + 2

    pdf.set_fill_color(252, 249, 240)
    pdf.rect(x_left, y_notes, plan_w_mm, notes_h, style="F")
    pdf.rect(x_left, y_notes, plan_w_mm, notes_h)
    pdf.set_xy(x_left, y_notes + (notes_h - notes_line_h) / 2)
    pdf.multi_cell(plan_w_mm, notes_line_h, "特記事項", align="C", border=0)

    x = x_left + plan_w_mm
    for b in BANKS + ["フラット35"]:
        pdf.rect(x, y_top, bank_w_mm, 10, style="F")
        pdf.rect(x, y_top, bank_w_mm, 10)
        pdf.set_xy(x, y_top)
        header_label = b
        # if b == "フラット35":
        #     header_label = "フラット35\n※1人上限8,000万"  # ← 削除またはコメントアウト
        pdf.multi_cell(bank_w_mm, 10, header_label, align="C", border=0)
        x += bank_w_mm

    pdf.set_xy(x_left, y_notes + notes_h + 2)
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
                init_str = "" if bank not in current_saved else f"{float(current_saved[bank]):.3f}"
                s = st.text_input(
                    f"{bank}（年利％）",
                    value=init_str,
                    key=key,
                    placeholder="未設定（例: 0.389）"
                )
                try:
                    new_rates_dict[bank] = float(s) if s.strip() != "" else None
                except Exception:
                    new_rates_dict[bank] = None

        # フラット35 用 90%、100% の金利入力欄を追加
        col90, col100 = st.columns(2)
        with col90:
            s90 = st.text_input(
                "フラット35（90%用 年利％）",
                value="" if "flat35_90" not in current_saved else f"{float(current_saved['flat35_90']):.3f}",
                key="flat35_rate_90",
                placeholder="例: 1.234"
            )
            try:
                # 入力をパーセント → 小数に変換
                new_rates_dict["flat35_90"] = float(s90) / 100.0 if s90.strip() != "" else None
            except:
                new_rates_dict["flat35_90"] = None

        with col100:
            s100 = st.text_input(
                "フラット35（100%用 年利％）",
                value="" if "flat35_100" not in current_saved else f"{float(current_saved['flat35_100']):.3f}",
                key="flat35_rate_100",
                placeholder="例: 1.567"
            )
            try:
                new_rates_dict["flat35_100"] = float(s100) / 100.0 if s100.strip() != "" else None
            except:
                new_rates_dict["flat35_100"] = None

        st.markdown("")
        if st.button("💾 金利を保存", type="primary", key="btn_rates_save"):
            ok = save_manual_rates(new_rates_dict)
            if ok:
                st.success("✅ 金利を保存しました（上部の表にも反映されます）")
            else:
                st.info("ℹ️ 入力に変更がなかったため保存していません")
