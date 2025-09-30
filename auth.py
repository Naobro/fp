# auth.py
import streamlit as st
from supabase import create_client
from datetime import date

# Supabase クライアント
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(url, key)

def get_current_month_password():
    """当月のパスワードを Supabase から取得"""
    month_key = date.today().strftime("%Y-%m")
    # テーブル monthly_passwords から取得
    res = supabase.table("monthly_passwords").select("month,password,created_at").eq("month", month_key).limit(1).execute()
    # デバッグ出力
    st.write("DEBUG - month_key サーバー側:", month_key)
    st.write("DEBUG - Supabase raw:", res.data)
    if res.data and len(res.data) > 0:
        return res.data[0].get("password")
    return None

def check_password_input(input_pw: str) -> bool:
    """入力値を Supabase に保存された当月パスワードと照合"""
    current_pw = get_current_month_password()
    if current_pw is None:
        return False
    return input_pw == current_pw

def check_password():
    """通常ページ用のログインフォーム"""
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

def check_admin():
    """管理者ページ用のログインフォーム"""
    if "admin_authenticated" not in st.session_state:
        st.session_state["admin_authenticated"] = False

    if not st.session_state["admin_authenticated"]:
        pwd = st.text_input("管理者パスワードを入力してください", type="password")
        if st.button("管理者ログイン"):
            if pwd == st.secrets["ADMIN_PASSWORD"]:  # secrets.toml に設定
                st.session_state["admin_authenticated"] = True
                st.rerun()
            else:
                st.error("管理者パスワードが違います")
        st.stop()

# デバッグ用関数（必要に応じて呼び出す）
def debug_info():
    month_key = date.today().strftime("%Y-%m")
    res = supabase.table("monthly_passwords").select("month,password,created_at").eq("month", month_key).limit(1).execute()
    st.write("DEBUG - month_key サーバー側:", month_key)
    st.write("DEBUG - Supabase raw:", res.data)
    if res.data and len(res.data) > 0:
        st.write("DEBUG - Supabaseから取得したpassword:", res.data[0].get("password"))
    else:
        st.write("DEBUG - Supabaseから取得したpassword: None")
