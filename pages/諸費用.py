# fp/pages/諸費用明細.py
import os
import re
import io
import zipfile
import tempfile
from pathlib import Path
from datetime import datetime

import streamlit as st
import requests
from fpdf import FPDF
from client_portal import get_sb, now_iso

SB = get_sb()

# ------------------ データロード／保存共通 ------------------
def load_profile_data(client_id: str):
    """client_profiles.profile 内の fees_detail を読み込む"""
    if not SB:
        return {}
    try:
        res = SB.table("client_profiles").select("profile").eq("client_id", client_id).limit(1).execute()
        if res.data:
            profile = res.data[0].get("profile") or {}
            return profile.get("fees_detail", {})
    except Exception as e:
        st.warning(f"データ読込失敗: {e}")
    return {}

def save_profile_data(client_id: str, fees_data: dict):
    """client_profiles.profile に fees_detail をマージ保存"""
    if not SB:
        return
    try:
        existing = SB.table("client_profiles").select("profile").eq("client_id", client_id).limit(1).execute()
        if existing.data and isinstance(existing.data[0].get("profile"), dict):
            profile = existing.data[0]["profile"]
        else:
            profile = {}
        profile["fees_detail"] = fees_data
        SB.table("client_profiles").upsert({
            "client_id": client_id,
            "profile": profile,
            "updated_at": datetime.now().isoformat()
        }, on_conflict="client_id").execute()
    except Exception as e:
        st.error(f"保存エラー: {e}")

# ------------------ 初期化 ------------------
client_id = st.query_params.get("client", "unknown")
saved = load_profile_data(client_id)

st.set_page_config(page_title="資金計画書（諸費用明細）", layout="centered")
st.title("資金計画書（諸費用明細）")

# ===== 以前の保存値を適用 =====
def s(key, default=""):
    return saved.get(key, default)

# ============ 入力項目（基本） ============
st.session_state["customer_name"] = st.text_input("お客様名（例：山田太郎）", s("customer_name"))
st.session_state["property_name"] = st.text_input("物件名", s("property_name"))
price_man = st.number_input("物件価格（万円）", min_value=100, max_value=200_000, value=int(s("price_man", 5800)), step=10)
property_price = int(price_man) * 10_000
deposit = int(s("deposit", property_price * 0.05))
base_rate = st.number_input("基準金利（年%）", min_value=0.0, max_value=5.0, value=float(s("base_rate", 0.78)), step=0.01)
total_expenses = int(s("total_expenses", 0))
total = int(s("total", property_price))
monthly_full = int(s("monthly_full", 0))
monthly_only = int(s("monthly_only", 0))
monthly_A = int(s("monthly_A", 0))
monthly_B = int(s("monthly_B", 0))

# ============ 保存ボタン ============
if st.button("💾 諸費用データを保存（全体マージ）"):
    fees_data = {
        "customer_name": st.session_state.get("customer_name", ""),
        "property_name": st.session_state.get("property_name", ""),
        "price_man": price_man,
        "property_price": property_price,
        "deposit": deposit,
        "base_rate": base_rate,
        "total_expenses": total_expenses,
        "total": total,
        "monthly_full": monthly_full,
        "monthly_only": monthly_only,
        "monthly_A": monthly_A,
        "monthly_B": monthly_B,
        "saved_at": now_iso(),
    }
    save_profile_data(client_id, fees_data)
    st.success("✅ 諸費用データを client_profiles に保存しました（全データ維持）")

# ============ PDF生成など他機能（省略可） ============
st.write("（この下にPDF生成ロジック・明細計算など既存処理をそのまま配置）")
