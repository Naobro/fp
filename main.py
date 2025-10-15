# ===============================
# LINE → Lステップ Webhook連携（Replit版）
# ===============================

from flask import Flask, request
import requests
import threading
import os

# ===============================
# 初期設定
# ===============================
app = Flask(__name__)

# --- 環境変数（ReplitのSecretsに登録推奨） ---
LINE_NOTIFY_TOKEN = os.getenv("LINE_NOTIFY_TOKEN", "ここにあなたのLINE Notifyトークン")
LSTEP_WEBHOOK_URL = "https://rcv.linestep.net/v3/call/2000010853"

# ===============================
# LINE Notify送信関数
# ===============================
def notify_line(msg: str):
    headers = {"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"}
    payload = {"message": msg}
    try:
        res = requests.post("https://notify-api.line.me/api/notify", headers=headers, data=payload)
        print("LINE Notify送信結果:", res.status_code, res.text)
    except Exception as e:
        print("LINE Notify送信エラー:", e)

# ===============================
# LINE Webhook受信
# ===============================
@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.json
    print("Webhook body:", body)

    def handle_event(event):
        try:
            if event.get("type") == "follow":  # 新規友だち追加
                user_id = event["source"]["userId"]

                # --- Lステップ転送 ---
                lst_payload = {"userId": user_id}
                print("Lステップ転送ペイロード:", lst_payload)
                res = requests.post(LSTEP_WEBHOOK_URL, json=lst_payload)
                print("LステップWebhook転送結果:", res.status_code, res.text)

                # --- LINE Notify通知 ---
                msg = f"👤 新しいフォロー: {user_id}"
                threading.Thread(target=notify_line, args=(msg,)).start()

        except Exception as e:
            print("イベント処理エラー:", e)

    # イベントを順次処理
    for event in body.get("events", []):
        threading.Thread(target=handle_event, args=(event,)).start()

    return "OK", 200

# ===============================
# テスト用（ブラウザアクセス確認）
# ===============================
@app.route("/")
def home():
    return "✅ LINE Webhook（Replit版）稼働中", 200

# ===============================
# メイン起動
# ===============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
