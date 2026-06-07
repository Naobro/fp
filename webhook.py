import os
import requests
from flask import Flask, request, jsonify
from supabase import create_client
from datetime import datetime
import random, string
from threading import Thread

# --------------------------
# Supabase 接続
# --------------------------
supabase = create_client(
    "https://pyopdfzwpwpoeqgvaaew.supabase.co",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB5b3BkZnp3cHdwb2VxZ3ZhYWV3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjM1Njg4MCwiZXhwIjoyMDcxOTMyODgwfQ.8_0HTmF62eBNP4fc9UKAtTWvWVz9KO-bvlS6xed0xPc"
)

# --------------------------
# LINE 設定
# --------------------------
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")

def notify_line(user_id: str, message: str):
    """LINEプッシュ送信（必要に応じて使用）"""
    if not LINE_CHANNEL_ACCESS_TOKEN:
        print("⚠️ LINE_CHANNEL_ACCESS_TOKEN が設定されていません")
        return
    
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    payload = {"to": user_id, "messages": [{"type": "text", "text": message}]}
    
    try:
        res = requests.post(url, headers=headers, json=payload)
        print("LINE notify response:", res.status_code, res.text)
        return res
    except Exception as e:
        print("LINE送信エラー:", e)

def gen_client_id(n: int = 6) -> str:
    """Streamlit管理画面と同じ形式のお客様IDを生成"""
    return "c-" + "".join(random.choices(string.ascii_lowercase + string.digits, k=n))

# --------------------------
# Flask アプリ
# --------------------------
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.json
    print("🔔 Webhook受信:", body)

    # ==========================================
    # ① Lumoへの完全転送（最優先・即座に実行）
    # ==========================================
    def forward_to_lumo(payload):
        try:
            lumo_webhook = "https://webhook.lumo.cx/workspaces/823254/line/01KRFRC22YPKQ5A61SQWJFDVHB"
            res = requests.post(lumo_webhook, json=payload, timeout=10)
            print("✅ Lumo転送成功:", res.status_code)
        except Exception as e:
            print("❌ Lumo転送エラー:", e)

    # Lumoに即座に転送（非同期）
    Thread(target=forward_to_lumo, args=(body,)).start()

    # ==========================================
    # ② 独自処理（Streamlit管理画面への登録のみ）
    # ==========================================
    def handle_event(events):
        for event in events:
            event_type = event.get("type")
            
            # メッセージ受信時のみ処理（友だち追加は何もしない）
            if event_type == "message":
                message_data = event.get("message", {})
                if message_data.get("type") == "text":
                    user_id = event["source"]["userId"]
                    text = message_data.get("text", "")
                    
                    # Streamlit管理画面用のデータ構造で保存
                    client_id = gen_client_id()
                    now = datetime.now().isoformat()
                    
                    meta = {
                        "client_id": client_id,
                        "created_at": now,
                        "customer_type": "LINE経由",
                        "name": f"LINEユーザー（{user_id[:8]}）",
                        "furigana": "",
                        "phone": "",
                        "email": "",
                        "current_station": "",
                        "current_layout": "",
                        "current_rent": "",
                        "family_structure": "",
                        "workplace": "",
                        "workplace_station": "",
                        "annual_income": "",
                        "own_funds": "",
                        "memo": f"LINEメッセージ: {text}",
                        "other_details": text,
                        "line_user_id": user_id,
                    }

                    record = {
                        "client_id": client_id,
                        "name": meta["name"],
                        "meta": meta,
                        "profile": {},
                        "updated_at": now,
                    }

                    # Supabaseに保存（Streamlit管理画面と同じテーブル）
                    try:
                        supabase.table("client_profiles").upsert(
                            record, on_conflict="client_id"
                        ).execute()
                        print(f"✅ Streamlit管理画面に登録完了: {client_id}")
                        
                        # 注：自動返信はLumoと重複を避けるため無効化
                        # 必要に応じて以下のコメントを外してください
                        # notify_line(user_id, "お問い合わせありがとうございます。")
                        
                    except Exception as e:
                        print("❌ Supabase登録エラー:", e)

    # イベント処理を非同期で実行
    events = body.get("events", [])
    if events:
        Thread(target=handle_event, args=(events,)).start()

    return jsonify({"status": "ok"})

@app.route("/health", methods=["GET"])
def health_check():
    """ヘルスチェック用エンドポイント"""
    return jsonify({
        "status": "healthy",
        "service": "line-webhook-simple",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == "__main__":
    # Render対応（PORTを環境変数から取得）
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
