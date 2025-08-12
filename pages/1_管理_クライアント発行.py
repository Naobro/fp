import streamlit as st
import secrets, string, json
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="管理：お客様発行", layout="centered")

DATA_DIR = Path("data/clients")
DATA_DIR.mkdir(parents=True, exist_ok=True)

def gen_id(n=6):
    alphabet = string.ascii_lowercase + string.digits
    return "c-" + "".join(secrets.choice(alphabet) for _ in range(n))

def gen_pin():
    return "".join(secrets.choice(string.digits) for _ in range(4))

st.title("管理：お客様ページの発行")

with st.form("new_client"):
    name  = st.text_input("お客様名（例：鵜沢様）")
    phone = st.text_input("電話番号（任意）")
    email = st.text_input("メール（任意）")
    memo  = st.text_area("管理メモ（任意）")
    submitted = st.form_submit_button("新規作成")

if submitted:
    client_id = gen_id()
    pin = gen_pin()
    payload = {
        "meta": {
            "client_id": client_id,
            "pin": pin,
            "created_at": datetime.now().isoformat(),
            "name": name,
            "phone": phone,
            "email": email,
            "memo": memo,
        },
        # 最低限の初期データ
        "baseline": {
            "housing_cost_m": None,
            "walk_min": None,
            "area_m2": None,
            "floor": None,
            "corner": None,
            "inner_corridor": None,
            "balcony_type": None,   # standard / wide / roof / garden
            "balcony_aspect": None, # N/E/S/W
            "view": None,           # open / partial / blocked
            "husband_commute_min": None,
            "wife_commute_min": None,
            # 専有/共用の現在スペック（True/False/NONE）
            "spec_current": {}
        },
        "prefs": {
            "importance": {  # 1〜5（初期3）
                "price": 3, "location": 3, "size_layout": 3, "spec": 3, "management": 3
            },
            "budget_max_m": None,
            "min_floor": None,      # 何階以上
            "min_floor_tolerance": 0,  # 許容幅（マイナスOK）
            # ◎○△× の選好（'must'/'want'/'neutral'/'no_need'）
            "spec_wish": {}
        },
        "listings": []
    }
    out = DATA_DIR / f"{client_id}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    url = f"/2_お客様ページ_ロードマップ?client={client_id}&pin={pin}"
    st.success("お客様を作成しました。")
    st.code(f"URL: {url}\nID: {client_id}\nPIN: {pin}", language="text")
    st.info("このURL/ID/PINをメールでご案内してください。")