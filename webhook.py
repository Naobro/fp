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
    return "c-" + "".join(random.choices(string.ascii_lowercase + string.digits, k=n))

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("🔔 Lumoから受信したデータ:", data)
    
    if not data:
        return jsonify({"error": "データなし"}), 400

    try:
        line_user_id = data.get("line_user_id", "")
        line_name = data.get("line_name", "")
        raw_name = data.get("name", "")
        
        name = raw_name.strip() if raw_name else ""
        if not name:
            name = line_name if line_name else f"LINEユーザー({line_user_id[:8]})"
        
        client_id = gen_client_id()
        now = datetime.now().isoformat()

        # ✅ admin.pyと完全に同じ構造でデータを保存
        meta = {
            "client_id": client_id,
            "created_at": now,
            "customer_type": "購入",  # LINEアンケート経由は購入希望者として設定
            
            # 基本情報
            "name": name,
            "furigana": data.get("furigana", ""),
            "phone": data.get("phone", ""),
            "email": data.get("email", ""),  # ← メールアドレス追加対応
            
            # 現在の状況
            "current_station": data.get("current_station", ""),
            "current_layout": data.get("current_layout", ""),
            "current_rent": data.get("current_rent", ""),
            "family_structure": data.get("family_structure", ""),
            
            # 勤務先情報
            "workplace": data.get("workplace", ""),
            "workplace_station": data.get("workplace_station", ""),
            "annual_income": data.get("annual_income", ""),
            "own_funds": data.get("own_funds", ""),
            
            # 購入希望条件
            "budget": data.get("budget", ""),
            "desired_area": data.get("desired_area", ""),
            "desired_spec": data.get("desired_spec", ""),
            
            # メモ・管理情報
            "memo": f"LINE表示名: {line_name}\nLINEアンケート経由で自動登録\n回答日時: {now}",
            "line_user_id": line_user_id,
        }

        record = {
            "client_id": client_id,
            "name": name,
            "meta": meta,
            "profile": {},
            "updated_at": now,
        }
        
        supabase.table("client_profiles").upsert(
            record, on_conflict="client_id"
        ).execute()
        
        print(f"✅ Streamlit管理画面に登録完了: {name} 様 ({client_id})")
        return jsonify({"status": "success", "client_id": client_id, "name": name})

    except Exception as e:
        print(f"❌ エラー発生: {str(e)}")
        import traceback
        print(f"📋 詳細エラー: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy", 
        "service": "lumo-to-streamlit-complete",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
