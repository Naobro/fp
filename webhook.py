import os
import requests
from flask import Flask, request, jsonify
from supabase import create_client
from datetime import date
import random, string

# --------------------------
# Supabase 接続
# --------------------------
import os
from supabase import create_client

supabase = create_client(
    "https://pyopdfzwpwpoeqgvaaew.supabase.co",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB5b3BkZnp3cHdwb2VxZ3ZhYWV3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjM1Njg4MCwiZXhwIjoyMDcxOTMyODgwfQ.8_0HTmF62eBNP4fc9UKAtTWvWVz9KO-bvlS6xed0xPc"
)
# --------------------------
# LINE 設定
# --------------------------
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")

def notify_line(user_id: str, message: str):
    """LINEプッシュ送信"""
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    payload = {"to": user_id, "messages": [{"type": "text", "text": message}]}
    res = requests.post(url, headers=headers, json=payload)
    print("LINE notify response:", res.status_code, res.text)
    return res

# --------------------------
# パスワード管理
# --------------------------
def generate_password(length: int = 10) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))

def get_or_create_current_password():
    """今月のパスワードを取得 or 生成"""
    month_key = date.today().strftime("%Y-%m")
    res = supabase.table("monthly_passwords").select("month, password").eq("month", month_key).execute()
    if res.data and len(res.data) > 0:
        return res.data[0]["password"].strip()
    else:
        new_pw = generate_password()
        supabase.table("monthly_passwords").insert({"month": month_key, "password": new_pw}).execute()
        return new_pw

# --------------------------
# Flask アプリ
# --------------------------
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.json
    print("Webhook body:", body)

    events = body.get("events", [])
    for event in events:
        if event.get("type") == "follow":  # 新規友だち追加時
            user_id = event["source"]["userId"]
            pw = get_or_create_current_password()

            # 送るのはパスワードだけ
            message = f"③ ログインパスワード\n👉 今月のパスワードは {pw}"
            notify_line(user_id, message)

    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
