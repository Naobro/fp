import os
import streamlit as st
from supabase import create_client
from datetime import date
import random, string, requests

# --------------------------
# Supabase クライアント
# --------------------------
url = os.environ.get("SUPABASE_URL", st.secrets.get("SUPABASE_URL"))
key = os.environ.get("SUPABASE_SERVICE_KEY", st.secrets.get("SUPABASE_SERVICE_KEY"))
supabase = create_client(url, key)

# --------------------------
# LINE設定（本番用）
# --------------------------
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", st.secrets.get("LINE_CHANNEL_ACCESS_TOKEN"))
LINE_USER_ID = os.environ.get("LINE_USER_ID", st.secrets.get("LINE_USER_ID"))
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", st.secrets.get("ADMIN_PASSWORD"))

# 本番用 LINE 友だち追加URL & QRコード
LINE_FRIEND_ADD_URL = "https://lin.ee/V1bwuO8"
LINE_FRIEND_QR = "https://qr-official.line.me/gs/M_277qthwd_GW.png?oat_content=qr"

# --------------------------
# LINE 通知関数
# --------------------------
def notify_line(user_id: str, message: str):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    payload = {"to": user_id, "messages": [{"type": "text", "text": message}]}
    return requests.post(url, headers=headers, json=payload)

def notify_all_members(message: str):
    if LINE_USER_ID:
        notify_line(LINE_USER_ID, message)

# --------------------------
# パスワード管理
# --------------------------
def generate_password(length: int = 10) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))

def get_or_create_current_password():
    """今月のパスワードを取得。無ければ生成→Supabase保存→LINE通知"""
    month_key = date.today().strftime("%Y-%m")
    res = supabase.table("monthly_passwords").select("month, password").eq("month", month_key).execute()
    if res.data and len(res.data) > 0:
        return res.data[0]["password"].strip()
    else:
        new_pw = generate_password()
        # 古いレコード削除
        old = supabase.table("monthly_passwords").select("month").neq("month", month_key).execute()
        if old.data:
            for rec in old.data:
                supabase.table("monthly_passwords").delete().eq("month", rec["month"]).execute()
        # 新規挿入
        supabase.table("monthly_passwords").insert({"month": month_key, "password": new_pw}).execute()
        notify_all_members(f"🔑 今月({month_key})のパスワードは: {new_pw}")
        return new_pw

# --------------------------
# 認証処理（利用者用）
# --------------------------
def check_password_input(input_pw: str) -> bool:
    current_pw = get_or_create_current_password()
    return input_pw.strip() == current_pw

def login_ui():
    """未ログイン時にLINE登録案内＋ログインフォームを表示"""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.markdown("### 🔐 利用には LINE 登録が必要です")
        col1, col2, col3 = st.columns([1,1,2])
        with col1:
            st.image(LINE_FRIEND_QR, caption="LINE登録はこちら", use_container_width=True)
        with col2:
            st.markdown(f"[👉 友だち追加はこちら]({LINE_FRIEND_ADD_URL})")
        with col3:
            pw = st.text_input("パスワードを入力してください", type="password", key="login_pw")
            if st.button("ログイン"):
                if check_password_input(pw):
                    st.session_state["authenticated"] = True
                    st.success("ログインに成功しました。")
                    st.rerun()
                else:
                    st.error("パスワードが違います")
    return st.session_state["authenticated"]

# --------------------------
# 管理者専用ログイン
# --------------------------
def check_admin():
    if "admin_authenticated" not in st.session_state:
        st.session_state["admin_authenticated"] = False

    if not st.session_state["admin_authenticated"]:
        st.markdown("### 👑 管理者ログイン")
        pwd = st.text_input("管理者パスワードを入力してください", type="password", key="admin_pw")
        if st.button("管理者ログイン"):
            if pwd == ADMIN_PASSWORD:
                st.session_state["admin_authenticated"] = True
                st.success("管理者ログイン成功！")
                st.rerun()
            else:
                st.error("管理者パスワードが違います")
    return st.session_state["admin_authenticated"]
