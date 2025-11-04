import os
import streamlit as st
from supabase import create_client
from datetime import date, datetime, time
import random, string, requests
import json
from fastapi import FastAPI, Request

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
    """特定ユーザーにLINE送信"""
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    payload = {"to": user_id, "messages": [{"type": "text", "text": message}]}
    return requests.post(url, headers=headers, json=payload)

def notify_all_members(message: str):
    """全員（固定1ID）に送信"""
    if LINE_USER_ID:
        notify_line(LINE_USER_ID, message)

# --------------------------
# パスワード管理
# --------------------------
def generate_password(length: int = 10) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))

def get_or_create_current_password():
    """今月のパスワードを取得。なければ生成→Supabase保存→LINE通知
       さらに毎月1日 8:00 にも再送する
    """
    month_key = date.today().strftime("%Y-%m")
    today = datetime.now()

    # 今月のレコード取得
    res = supabase.table("monthly_passwords").select("month, password").eq("month", month_key).execute()

    # --------------------------
    # 既に存在する場合
    # --------------------------
    if res.data and len(res.data) > 0:
        pw = res.data[0]["password"].strip()

        # 毎月1日8:00に再送（8:00〜8:59の間に起動すれば送信される）
        if today.day == 1 and 8 <= today.hour < 9:
            notify_all_members(f"🔑 今月({month_key})のパスワードは: {pw}")

        return pw

    # --------------------------
    # 存在しない場合 → 新規生成＆通知
    # --------------------------
    new_pw = generate_password()

    # 古いレコード削除
    old = supabase.table("monthly_passwords").select("month").neq("month", month_key).execute()
    if old.data:
        for rec in old.data:
            supabase.table("monthly_passwords").delete().eq("month", rec["month"]).execute()

    # 新規挿入
    supabase.table("monthly_passwords").insert({"month": month_key, "password": new_pw}).execute()

    # LINE通知
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
    """管理者ログインUI"""
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", st.secrets.get("ADMIN_PASSWORD", "naoki2480"))
    if "admin_authenticated" not in st.session_state:
        st.session_state["admin_authenticated"] = False

    if not st.session_state["admin_authenticated"]:
        st.markdown("### 👑 管理者ログイン")
        pwd = st.text_input("管理者パスワードを入力してください", type="password", key="admin_pw")
        if st.button("ログイン"):
            if pwd == ADMIN_PASSWORD and pwd != "":
                st.session_state["admin_authenticated"] = True
                st.success("ログイン成功！")
                st.rerun()
            else:
                st.error("パスワードが違います")
        st.stop()
    return True

# ==========================
# Lステップ用 Webhook エンドポイント
# ==========================
app = FastAPI()

@app.post("/webhook")
async def webhook(request: Request):
    """LステップからのWebhookでパスワード返信"""
    body = await request.json()
    try:
        user_id = body["events"][0]["source"]["userId"]
        text = body["events"][0]["message"]["text"].strip()
    except Exception:
        return {"status": "error", "reason": "invalid payload"}

    if text in ["パスワード", "password", "PASS", "パス"]:
        current_pw = get_or_create_current_password()
        message = f"🔑 今月の住宅ローンサイトのパスワードは『{current_pw}』です。"
        notify_line(user_id, message)
        return {"status": "ok", "reply": "password sent"}

    return {"status": "ignored"}

# ==========================
# 管理者が今月のパスワードを一斉送信する関数
# ==========================
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

# ==========================
# 管理画面にボタンを表示
# ==========================
def admin_send_ui():
    """管理者用UIから一斉送信ボタン"""
    check_admin()
    st.markdown("### 📤 今月のパスワードをLINE登録者に一斉送信")
    if st.button("送信する"):
        send_password_to_all()
