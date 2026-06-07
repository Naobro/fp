import os
from flask import Flask, request, jsonify
from supabase import create_client
from datetime import datetime
import random, string

# --------------------------
# Supabase 接続
# --------------------------
SUPABASE_URL = "https://pyopdfzwpwpoeqgvaaew.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", 
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB5b3BkZnp3cHdwb2VxZ3ZhYWV3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjM1Njg4MCwiZXhwIjoyMDcxOTMyODgwfQ.8_0HTmF62eBNP4fc9UKAtTWvWVz9KO-bvlS6xed0xPc")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def gen_client_id(n: int = 6) -> str:
    """Streamlit管理画面と同じ形式のお客様IDを生成"""
    return "c-" + "".join(random.choices(string.ascii_lowercase + string.digits, k=n))

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Lumoから送られてきた完成されたお客様データを受け取り、
    Streamlit管理画面と同じ形式でSupabaseに保存する
    """
    data = request.json
    print("🔔 Lumoからお客様データを受信:", data)

    if not data:
        return jsonify({"error": "データがありません"}), 400

    try:
        # LumoのJSONからデータを抽出
        line_user_id = data.get("line_user_id", "")
        line_name = data.get("line_name", "")
        
        # お客様が入力した名前（最優先）
        name = data.get("name", "").strip()
        if not name:
            # 名前が未入力の場合はLINEの表示名を使用
            name = line_name if line_name else f"LINEユーザー({line_user_id[:8]})"

        client_id = gen_client_id()
        now = datetime.now().isoformat()

        # admin.pyと完全に同じデータ構造を作成
        meta = {
            "client_id": client_id,
            "created_at": now,
            "customer_type": "LINEアンケート経由",
            
            # ✅ Lumoから受け取った完璧なデータをそのまま使用
            "name": name,
            "furigana": data.get("furigana", ""),
            "phone": data.get("phone", ""),
            "email": data.get("email", ""),
            
            # 現在の状況
            "current_station": data.get("nearest_station", ""),
            "current_layout": "",
            "current_rent": "",
            "family_structure": data.get("family_structure", ""),
            
            # 勤務先情報
            "workplace": data.get("company_name", ""),
            "workplace_station": data.get("company_station", ""),
            "annual_income": data.get("annual_income", ""),
            "own_funds": "",
            
            # メモ欄に追加情報を記録
            "memo": f"LINE表示名: {line_name}\n勤続年数: {data.get('years_of_service', '')}\nLumo経由で自動登録",
            
            # LINE関連情報も保存
            "line_user_id": line_user_id,
        }

        # Supabaseに保存するレコード（admin.pyと同じ構造）
        record = {
            "client_id": client_id,
            "name": name,
            "meta": meta,
            "profile": {},
            "updated_at": now,
        }

        # Supabaseのclient_profilesテーブルに保存
        supabase.table("client_profiles").upsert(
            record, on_conflict="client_id"
        ).execute()
        
        print(f"✅ Streamlit管理画面に登録完了: {name} 様 ({client_id})")
        return jsonify({"status": "success", "client_id": client_id, "name": name})

    except Exception as e:
        print("❌ 登録エラー:", e)
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health_check():
    """サーバーの動作確認用"""
    return jsonify({
        "status": "healthy", 
        "service": "lumo-to-streamlit",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
