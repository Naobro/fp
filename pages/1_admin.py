# pages/1_admin.py

import streamlit as st
import secrets, string, json
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="管理：お客様発行", layout="centered")

# 共有用ベースURL（secrets優先。無ければ本番URL）
BASE_URL = st.secrets.get("BASE_URL", "https://naokifp.streamlit.app")
BASE_URL = BASE_URL.rstrip("/")  # 末尾スラッシュを除去しておく

DATA_DIR = Path("data/clients")
DATA_DIR.mkdir(parents=True, exist_ok=True)

def gen_id(n: int = 6) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "c-" + "".join(secrets.choice(alphabet) for _ in range(n))

def gen_pin() -> str:
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

    # 初期ペイロード
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
        "baseline": {
            "housing_cost_m": None,
            "walk_min": None,
            "area_m2": None,
            "floor": None,
            "corner": None,
            "inner_corridor": None,
            "balcony_type": None,    # standard / wide / roof / garden
            "balcony_aspect": None,  # N/E/S/W
            "view": None,            # open / partial / blocked
            "husband_commute_min": None,
            "wife_commute_min": None,
            "spec_current": {}
        },
        "prefs": {
            "importance": {"price": 3, "location": 3, "size_layout": 3, "spec": 3, "management": 3},
            "budget_max_m": None,
            "min_floor": None,
            "min_floor_tolerance": 0,
            "spec_wish": {}
        },
        "listings": []
    }

    # 保存
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / f"{client_id}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # 共有URL（ルート + クエリ。app.pyが自動でお客様ページに飛ばす）
    share_url = f"{BASE_URL}/?client={client_id}&pin={pin}"

    st.success("お客様を作成しました。下のリンクを共有してください。")
    st.code(f"URL: {share_url}\nID: {client_id}\nPIN: {pin}", language="text")

    # 外部リンクボタンで確実に新規タブを開く
    st.link_button("➡️ このままお客様ページを開く（新規タブ）", share_url, type="primary")