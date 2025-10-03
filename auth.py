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
# LINE設定
# --------------------------
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", st.secrets.get("LINE_CHANNEL_ACCESS_TOKEN"))
LINE_USER_ID = os.environ.get("LINE_USER_ID", st.secrets.get("LINE_USER_ID"))
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", st.secrets.get("ADMIN_PASSWORD"))
LINE_USER_IDS = [LINE_USER_ID]

def notify_line(user_id: str, message: str):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    payload = {"to": user_id, "messages": [{"type": "text", "text": message}]}
    res = requests.post(url, headers=headers, json=payload)

    # ★ GitHub Actions のログで送信結果を確認できるように
    print("LINE notify response:", res.status_code, res.text)

    return res

def notify_all_members(message: str):
    for uid in LINE_USER_IDS:
        notify_line(uid, message)

# --------------------------
# パスワード管理
# --------------------------
def generate_password(length: int = 10) -> str:
    """ランダム英数字パスワード生成"""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))

def get_or_create_current_password():
    """今月のパスワードを取得。なければ生成→Supabase保存→LINE通知"""
    month_key = date.today().strftime("%Y-%m")
    
    # 今月のレコードを検索
    res = supabase.table("monthly_passwords").select("month, password").eq("month", month_key).execute()
    
    if res.data and len(res.data) > 0:
        # 今月のパスワードが既に存在
        return res.data[0]["password"].strip()
    else:
        # 今月のパスワードが存在しない場合、新規生成
        new_pw = generate_password()
        
        # 古いレコードを削除
        old_records = supabase.table("monthly_passwords").select("month").neq("month", month_key).execute()
        if old_records.data:
            for old_record in old_records.data:
                supabase.table("monthly_passwords").delete().eq("month", old_record["month"]).execute()
        
        # 新しいパスワードを挿入
        supabase.table("monthly_passwords").insert(
            {"month": month_key, "password": new_pw}
        ).execute()
        
        # LINE通知
        notify_all_members(f"🔑 今月({month_key})のパスワードは: {new_pw}")
        return new_pw

# --------------------------
# 認証処理
# --------------------------
def check_password_input(input_pw: str) -> bool:
    current_pw = get_or_create_current_password()
    return input_pw.strip() == current_pw

def check_password():
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
    if "admin_authenticated" not in st.session_state:
        st.session_state["admin_authenticated"] = False
    
    if not st.session_state["admin_authenticated"]:
        pwd = st.text_input("管理者パスワードを入力してください", type="password")
        if st.button("管理者ログイン"):
            if pwd == ADMIN_PASSWORD:
                st.session_state["admin_authenticated"] = True
                st.rerun()
            else:
                st.error("管理者パスワードが違います")
        st.stop()

# --------------------------
# テスト実行(Actions用)
# --------------------------
if __name__ == "__main__":
    pw = get_or_create_current_password()
    print("✅ 今月のパスワード:", pw)

    # 追加：LINE通知が必ず走るように
    notify_all_members(f"🔑 今月のパスワードは: {pw}")
