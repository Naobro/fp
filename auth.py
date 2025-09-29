import streamlit as st

def check_password():
    """通常ページ用のパスワードチェック"""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        pwd = st.text_input("パスワードを入力してください", type="password")
        if st.button("ログイン"):
            if pwd == st.secrets["APP_PASSWORD"]:  # secrets.toml に設定
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("パスワードが違います")
        st.stop()


def check_admin():
    """管理者ページ用のパスワードチェック"""
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