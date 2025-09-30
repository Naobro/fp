# auth.py
import streamlit as st
from supabase import create_client
from datetime import date

# Supabase クライアント
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(url, key)

def get_current_month_password():
    month_key = date.today().strftime("%Y-%m")
    res = supabase.table("monthly_passwords").select("password").eq("month", month_key).limit(1).execute()
    if res.data and len(res.data) > 0:
        return res.data[0].get("password")
    return None

def check_password_input(input_pw: str) -> bool:
    """新仕様: 引数を受けて照合する"""
    current_pw = get_current_month_password()
    if current_pw is None:
        return False
    return input_pw == current_pw

def check_password():
    """旧仕様: ページ先頭で呼び出し→ログインフォームを表示"""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        pwd = st.text_input("パスワードを入力してください", type="password")
        if st.button("ログイン"):
            if check_password_input(pwd):
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("パスワードが違います")
        st.stop()
