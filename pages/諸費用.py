# fp/pages/諸費用明細.py
# クライアント専用：諸費用明細（全データをSupabaseへ保存・復元）

import os
import re
import io
import zipfile
from pathlib import Path
import tempfile
import requests
import streamlit as st
from fpdf import FPDF

from client_portal import get_sb, now_iso

# ============ Supabase 初期化 ============
SB = get_sb()

# ============ データロード ============
def load_profile_data(client_id: str):
    """Supabaseからclient_profiles.profileを取得"""
    if not SB:
        return {}
    try:
        res = SB.table("client_profiles").select("profile").eq("client_id", client_id).limit(1).execute()
        if res.data:
            return res.data[0].get("profile", {})
    except Exception as e:
        st.warning(f"保存データの読み込み失敗: {e}")
    return {}

# ============ データ保存 ============
def save_profile_data(client_id: str, new_data: dict):
    """profile内のfees_detailを全上書き保存"""
    if not SB:
        st.error("Supabase接続がありません。")
        return
    existing = load_profile_data(client_id)
    existing["fees_detail"] = new_data
    data = {
        "client_id": client_id,
        "profile": existing,
        "updated_at": now_iso()
    }
    SB.table("client_profiles").upsert(data, on_conflict="client_id").execute()

# ============ ページ設定 ============
st.set_page_config(page_title="資金計画書（諸費用明細）", layout="centered")
st.title("資金計画書（諸費用明細）")

client_id = st.query_params.get("client", "unknown")
profile = load_profile_data(client_id)
saved = profile.get("fees_detail", {})

# ============ ユーティリティ ============
def fmt_jpy(n: int) -> str:
    return f"{int(n):,} 円"

def number_input_commas(label, value, step=1):
    s = st.text_input(label, f"{value:,}")
    s = re.sub(r"[^\d]", "", s)
    try:
        v = int(s)
    except Exception:
        v = value
    return v

def monthly_payment(loan_amount: int, years: int, annual_rate: float) -> int:
    n = years * 12
    r = annual_rate / 100 / 12
    if n <= 0: return 0
    if r == 0: return int(loan_amount / n)
    try:
        return int(loan_amount * r * (1 + r) ** n / ((1 + r) ** n - 1))
    except ZeroDivisionError:
        return 0

def calc_stamp_tax(price_yen: int) -> int:
    p = price_yen
    if p <= 5_000_000: return 5_000
    if p <= 10_000_000: return 10_000
    if p <= 50_000_000: return 10_000
    if p <= 100_000_000: return 30_000
    if p <= 500_000_000: return 60_000
    if p <= 1_000_000_000: return 160_000
    if p <= 5_000_000_000: return 320_000
    return 480_000

# ============ 入力エリア ============
st.subheader("🧾 基本情報")

customer_name = st.text_input("お客様名", saved.get("customer_name", ""))
property_name = st.text_input("物件名", saved.get("property_name", ""))
property_price = st.number_input("物件価格（万円）", min_value=100, max_value=200_000, value=int(saved.get("property_price", 5800) / 10000), step=10) * 10_000
deposit = number_input_commas("手付金（円）", saved.get("deposit", 0))
kanri_month = number_input_commas("管理費・修繕積立（月額円）", saved.get("kanri_month", 18000))
base_rate = st.number_input("基準金利（年%）", min_value=0.0, max_value=5.0, value=float(saved.get("base_rate", 0.78)), step=0.01)
base_years = 35

# ============ 借入金（万円単位入力） ============
st.markdown("### 💰 借入条件（自由入力）")

loan_amount_man = st.number_input("借入金額（万円）", min_value=0, max_value=300_000,
                                 value=int(saved.get("loan_amount", property_price / 10000)),
                                 step=10)
loan_amount = loan_amount_man * 10_000  # ← 円に変換して計算
loan_rate = st.number_input("金利（年%）", min_value=0.0, max_value=5.0, value=float(saved.get("loan_rate", base_rate)), step=0.01)
loan_years = st.number_input("返済期間（年）", min_value=1, max_value=50, value=int(saved.get("loan_years", 35)), step=1)

# ============ 計算部分 ============
stamp_fee = calc_stamp_tax(property_price)
monthly = monthly_payment(loan_amount, loan_years, loan_rate)
total_expenses = int(stamp_fee + 400_000 + 200_000 + 100_000)
total = int(property_price + total_expenses)

st.markdown("### 💡 概算結果")
st.write(f"- 物件価格：**{fmt_jpy(property_price)}**")
st.write(f"- 借入金額：**{fmt_jpy(loan_amount)}**（入力：{loan_amount_man:,} 万円）")
st.write(f"- 諸費用合計：**{fmt_jpy(total_expenses)}**")
st.write(f"- 総額（物件＋諸費用）：**{fmt_jpy(total)}**")
st.write(f"- 月々返済額：**{fmt_jpy(monthly)}**")

# ============ PDF生成関数 ============
def build_pdf(customer_name, property_name, property_price, loan_amount, loan_rate, loan_years, monthly, total):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, f"{customer_name} 様", ln=1)
    pdf.cell(0, 10, f"物件名：{property_name}", ln=1)
    pdf.cell(0, 10, f"物件価格：{fmt_jpy(property_price)}", ln=1)
    pdf.cell(0, 10, f"借入金額：{fmt_jpy(loan_amount)}（{loan_rate:.2f}%／{loan_years}年）", ln=1)
    pdf.cell(0, 10, f"月々返済額：{fmt_jpy(monthly)}", ln=1)
    pdf.cell(0, 10, f"総合計：{fmt_jpy(total)}", ln=1)
    return bytes(pdf.output(dest="S"))

pdf_bytes = build_pdf(customer_name, property_name, property_price, loan_amount, loan_rate, loan_years, monthly, total)

# ============ 保存処理 ============
if st.button("💾 この内容を保存（Supabaseへ上書き）"):
    payload = {
        "customer_name": customer_name,
        "property_name": property_name,
        "property_price": property_price,
        "deposit": deposit,
        "kanri_month": kanri_month,
        "base_rate": base_rate,
        "loan_amount": loan_amount,
        "loan_rate": loan_rate,
        "loan_years": loan_years,
        "monthly": monthly,
        "total_expenses": total_expenses,
        "total": total,
        "saved_at": now_iso(),
    }
    save_profile_data(client_id, payload)
    st.success("全データをSupabaseに上書き保存しました ✅")

# ============ PDFダウンロード ============
st.download_button(
    "📄 資金計画書（PDF）ダウンロード",
    data=pdf_bytes,
    file_name=f"{property_name}_諸費用明細.pdf",
    mime="application/pdf",
)
