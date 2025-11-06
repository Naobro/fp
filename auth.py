import os
import streamlit as st
from supabase import create_client
from datetime import date, datetime, time
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
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", st.secrets.get("ADMIN_PASSWORD", "naoki2480"))

# 本番用 LINE 友だち追加URL & QRコード
LINE_FRIEND_ADD_URL = "https://lin.ee/V1bwuO8"
LINE_FRIEND_QR = "https://qr-official.line.me/gs/M_277qthwd_GW.png?oat_content=qr"

# =========================================================
# 📩 LINE 送信 関数群
# =========================================================
def notify_line(user_id: str, message: str):
    """指定ユーザーにLINE送信"""
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
    """全LINE登録者へ送信（Supabase: line_subscribers テーブル）"""
    try:
        res = supabase.table("line_subscribers").select("user_id").execute()
        users = [r["user_id"] for r in res.data if "user_id" in r]
    except Exception as e:
        users = []
        st.warning(f"line_subscribers 読み込みエラー: {e}")

    if not users:
        st.error("⚠️ Supabaseの line_subscribers に登録者がいません。")
        return

    success, failed = 0, 0
    for uid in users:
        code = notify_line(uid, message)
        if code == 200:
            success += 1
        else:
            failed += 1
    st.success(f"✅ 送信完了（成功: {success}件 / 失敗: {failed}件）")


# =========================================================
# 🔑 パスワード管理
# =========================================================
def generate_password(length: int = 10) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def get_or_create_current_password():
    """固定パスワードを返す（自動生成・更新を停止）"""
    return "terassnishiyama"

# =========================================================
# 👋 新規登録者への自動送信
# =========================================================
def send_welcome_message(user_id: str):
    """LINE新規登録者への初回メッセージ（パスワード付き）"""
    pw = get_or_create_current_password()
    message = (
        "🎉 ご登録ありがとうございます！\n\n"
        "🔑 今月の住宅ローンサイトパスワードはこちら👇\n"
        f"【{pw}】\n\n"
        "以下のリンクからログインできます。\n"
        "https://naokifp.streamlit.app/"
    )
    notify_line(user_id, message)


# =========================================================
# 👑 管理画面ログイン
# =========================================================
def check_admin():
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


# =========================================================
# 🧭 管理画面UI（手動一斉送信用）
# =========================================================
def admin_send_ui():
    check_admin()
    st.markdown("### 📤 今月のパスワードを全LINE登録者に一斉送信")
    if st.button("送信する"):
        month_key = date.today().strftime("%Y-%m")
        pw = get_or_create_current_password()
        msg = f"🔑 今月({month_key})の住宅ローンサイトのパスワードは『{pw}』です。"
        notify_all_members(msg)
