import os
from flask import Flask, request, jsonify
from supabase import create_client
from datetime import datetime
import random, string

SUPABASE_URL = "https://pyopdfzwpwpoeqgvaaew.supabase.co"
SUPABASE_KEY = os.environ.get(
    "SUPABASE_SERVICE_ROLE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB5b3BkZnp3cHdwb2VxZ3ZhYWV3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjM1Njg4MCwiZXhwIjoyMDcxOTMyODgwfQ.8_0HTmF62eBNP4fc9UKAtTWvWVz9KO-bvlS6xed0xPc",
)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
TABLE_NAME = "client_profiles"

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

        name = (raw_name or "").strip()
        if not name:
            name = line_name or f"LINEユーザー({line_user_id[:8]})"

        client_id = gen_client_id()
        now = datetime.now().isoformat()

        # ✅ admin.py と完全に同じキー構成
        base_meta = {
            "client_id": client_id,
            "created_at": now,
            "customer_type": "購入",
            "name": name,
            "furigana": data.get("furigana", ""),
            "phone": data.get("phone", ""),
            "email": data.get("email", ""),
            "current_station": data.get("current_station", ""),
            "current_layout": data.get("current_layout", ""),
            "current_rent": data.get("current_rent", ""),
            "family_structure": data.get("family_structure", ""),
            "wife_working": data.get("wife_working", ""),
            "workplace": data.get("workplace", ""),
            "workplace_station": data.get("workplace_station", ""),
            "annual_income": data.get("annual_income", ""),
            "own_funds": data.get("own_funds", ""),
            "spouse_workplace": data.get("spouse_workplace", ""),
            "spouse_workplace_station": data.get("spouse_workplace_station", ""),
            "spouse_annual_income": data.get("spouse_annual_income", ""),
            "household_annual_income": data.get("household_annual_income", ""),
            "budget": data.get("budget", ""),
            "desired_area": data.get("desired_area", ""),
            "desired_spec": data.get("desired_spec", ""),
            "memo": f"LINE表示名: {line_name}\nLumoアンケート経由で自動登録\n家族構成: {data.get('family_structure', '')}\n奥様状況: {data.get('wife_working', '')}",
            "line_user_id": line_user_id,
            "line_name": line_name,
        }

        record = {
            "client_id": client_id,
            "name": name,
            "meta": base_meta,
            "profile": base_meta,
            "updated_at": now,
        }

        supabase.table(TABLE_NAME).upsert(record, on_conflict="client_id").execute()

        print(f"✅ 登録完了: {name} 様 ({client_id}) 家族構成: {data.get('family_structure', '')} 奥様: {data.get('wife_working', '')}")
        return jsonify({"status": "success", "client_id": client_id, "name": name})

    except Exception as e:
        print("❌ エラー発生:", e)
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "service": "lumo-segment-system"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
