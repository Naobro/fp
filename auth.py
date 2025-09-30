# auth.py
import streamlit as st
from supabase import create_client
from datetime import date

# Supabase クライアント（読み取りは anon key でOK）
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(url, key)

def get_current_month_password():
    month_key = date.today().strftime("%Y-%m")
    res = supabase.table("monthly_passwords").select("password").eq("month", month_key).limit(1).execute()
    if res.data and len(res.data) > 0:
        return res.data[0].get("password")
    return None

def check_password(input_pw: str) -> bool:
    current_pw = get_current_month_password()
    if current_pw is None:
        return False
    return input_pw == current_pw
