import os
import streamlit as st
from supabase import create_client
from datetime import date, datetime
import random, string, requests

# --------------------------
# Supabase クライアント
# --------------------------
url = os.environ.get("SUPABASE_URL", st.secrets.get("SUPABASE_URL"))
key = os.environ.get("SUPABASE_SERVICE_KEY", st.secrets.get("SUPABASE_SERVICE_KEY"))
supabase = create_client(url, key)

# --------------------------
# LINE設定
# --------------------------
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", st.secrets.get("LINE_CHANNEL_ACCESS_TOKEN"))
LINE_USER_ID = os.environ.get("LINE_USER_ID", st.secrets.get("LINE_USER_ID"))
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", st.secrets.get("ADMIN_PASSWORD", "naoki2480"))

# 本番用 LINE 友だち追加URL & QRコード
LINE_FRIEND_ADD_URL = "https://lin.ee/V1bwuO8"
LINE_FRIEND_QR = "https://qr-official.line.me/gs/M_277qthwd_GW.png?oat_content=qr"

# --------------------------
# LINE 通知関数
# --------------------------
def notify_line(user_id: str, message: str):
    """特定ユーザーにLINE送信"""
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    payload = {"to": user_id, "messages": [{"type": "text", "text": message}]}
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        return res.status_code
    except Exception as e:
        st.error(f"LINE送信エラー: {e}")
        return None

def notify_all_members(message: str):
    """全員（固定1ID）に送信"""
    if LINE_USER_ID:
        notify_line(LINE_USER_ID, message)
    else:
        st.warning("環境変数 LINE_USER_ID が設定されていません。")

# --------------------------
# パスワード管理
# --------------------------
def generate_password(length: int = 10) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))

def get_or_create_current_password():
    """今月のパスワードを取得。なければ生成→Supabase保存→LINE通知"""
    month_key = date.today().strftime("%Y-%m")
    today = datetime.now()

    res = supabase.table("monthly_passwords").select("month, password").eq("month", month_key).execute()

    if res.data and len(res.data) > 0:
        pw = res.data[0]["password"].strip()
        # 毎月1日8:00〜8:59に再送
        if today.day == 1 and 8 <= today.hour < 9:
            notify_all_members(f"🔑 今月({month_key})のパスワードは: {pw}")
        return pw

    # パスワード未作成なら新規生成
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
# 管理者ログイン
# --------------------------
def check_admin():
    """管理者ログイン"""
    if "admin_authenticated" not in st.session_state:
        st.session_state["admin_authenticated"] = False
    if not st.session_state["admin_authenticated"]:
        st.markdown("### 👑 管理者ログイン")
        pwd = st.text_input("管理者パスワード", type="password", key="admin_pw")
        if st.button("ログイン"):
            if pwd == ADMIN_PASSWORD:
                st.session_state["admin_authenticated"] = True
                st.success("ログイン成功！")
                st.rerun()
            else:
                st.error("パスワードが違います")
        st.stop()
    return True

# --------------------------
# 今月のパスワードを全員に送信
# --------------------------
def send_password_to_all():
    """今月のパスワードをLINE登録者全員に送信"""
    month_key = date.today().strftime("%Y-%m")
    res = supabase.table("monthly_passwords").select("password").eq("month", month_key).execute()
    if not res.data:
        pw = get_or_create_current_password()
    else:
        pw = res.data[0]["password"].strip()
    message = f"🔑 今月({month_key})の住宅ローンサイトのパスワードは『{pw}』です。"
    notify_all_members(message)
    st.success("LINE登録者全員に送信しました。")

# --------------------------
# 管理画面UI
# --------------------------
def admin_send_ui():
    """管理者用UI"""
    check_admin()
    st.markdown("### 📤 今月のパスワードをLINE登録者に一斉送信")
    if st.button("送信する"):
        send_password_to_all()
