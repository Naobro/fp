# pages/1_admin.py  — 管理画面（新規発行・一覧・検索・即アクセス・削除）
import streamlit as st
import json, secrets, string
from pathlib import Path
from datetime import datetime

# 画面設定
st.set_page_config(page_title="管理：お客様ページ 管理", layout="wide")

# 共有URL（本番URLを secrets で上書き可）
BASE_URL = st.secrets.get("BASE_URL", "https://naokifp.streamlit.app/")

# データ保存先
DATA_DIR = Path("data/clients")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------
# 共通ユーティリティ
# -------------------------------
def gen_id(n: int = 6) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "c-" + "".join(secrets.choice(alphabet) for _ in range(n))

def load_all_clients():
    """data/clients/*.json を読み込んで一覧返却"""
    clients = []
    for p in sorted(DATA_DIR.glob("*.json")):
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
            meta = obj.get("meta", {})
            cid = meta.get("client_id") or p.stem
            name = meta.get("name") or "(無名)"
            created_raw = meta.get("created_at")
            try:
                created = datetime.fromisoformat(created_raw) if created_raw else None
            except Exception:
                created = None
            clients.append({
                "id": cid,
                "name": name,
                "created": created,
                "path": p,
                "meta": meta,
                "raw": obj,
            })
        except Exception:
            # 壊れたJSONなどはスキップ
            continue
    return clients

def share_url_for(cid: str) -> str:
    return f"{BASE_URL}?client={cid}"

# -------------------------------
# 新規発行（PINなし）
# -------------------------------
st.header("お客様ページの新規発行（PINなし）")

with st.form("new_client"):
    c1, c2 = st.columns(2)
    with c1:
        name  = st.text_input("お客様名")
        phone = st.text_input("電話番号（任意）")
    with c2:
        email = st.text_input("メール（任意）")
        memo  = st.text_area("管理メモ（任意）", height=80)
    submitted = st.form_submit_button("新規作成", type="primary")

if submitted:
    client_id = gen_id()
    payload = {
        "meta": {
            "client_id": client_id,
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
            "balcony_type": None,
            "balcony_aspect": None,
            "view": None,
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
    out = DATA_DIR / f"{client_id}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    url = share_url_for(client_id)
    st.success("お客様用URLを発行しました。下のリンクを共有してください。")
    st.code(url, language="text")
    st.link_button("➡️ このままお客様ページを開く（新規タブ）", url, type="primary")

st.divider()

# -------------------------------
# 一覧・検索・即アクセス・削除
# -------------------------------
st.header("お客様ページ 一覧")

# 検索・並び替え
clients = load_all_clients()
total = len(clients)

c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    q = st.text_input("検索（お客様名／ID 含む）", value="")
with c2:
    sort_key = st.selectbox("並び順", ["作成が新しい順", "作成が古い順", "名前（A→Z）", "名前（Z→A）"])
with c3:
    st.metric("登録件数", total)

# フィルタ
if q:
    q_lower = q.strip().lower()
    clients = [c for c in clients if q_lower in (c["name"] or "").lower() or q_lower in (c["id"] or "").lower()]

# ソート
def default_time(d):  # None対策
    return d or datetime.fromtimestamp(0)

if sort_key == "作成が新しい順":
    clients.sort(key=lambda x: default_time(x["created"]), reverse=True)
elif sort_key == "作成が古い順":
    clients.sort(key=lambda x: default_time(x["created"]))
elif sort_key == "名前（A→Z）":
    clients.sort(key=lambda x: (x["name"] or "").lower())
else:
    clients.sort(key=lambda x: (x["name"] or "").lower(), reverse=True)

# 一括削除UI
st.subheader("一括削除")
left, right = st.columns([3, 2])
with left:
    ids_for_delete = st.multiselect(
        "削除したいお客様を選択",
        options=[f'{c["name"]}（{c["id"]}）' for c in clients],
        key="bulk_delete_select"
    )
with right:
    confirm_text = st.text_input('最終確認：DELETE と入力で実行', value="", key="bulk_delete_confirm")
    do_bulk = st.button("選択を削除する", type="secondary")

if do_bulk:
    if confirm_text.strip() != "DELETE":
        st.warning("削除を実行するには、確認欄に DELETE と入力してください。")
    else:
        deleted = 0
        # 選択表示から id 抜き出し
        pick_ids = []
        for label in ids_for_delete:
            # "名前（c-xxxxx）" から ()内のIDを抽出
            if "（" in label and "）" in label:
                cid = label.split("（")[-1].split("）")[0]
                pick_ids.append(cid)
        for c in clients:
            if c["id"] in pick_ids and c["path"].exists():
                try:
                    c["path"].unlink()
                    deleted += 1
                except Exception:
                    pass
        st.success(f"{deleted} 件削除しました。画面を再読込してください。")

st.divider()

# 行表示（即アクセス＋個別削除）
st.subheader("一覧")

if not clients:
    st.info("該当データはありません。")
else:
    for c in clients:
        url = share_url_for(c["id"])
        cols = st.columns([3, 2, 2, 3, 1])
        with cols[0]:
            st.write(f"**{c['name']}**")
            st.caption(f"ID: {c['id']}")
        with cols[1]:
            st.caption("作成日時")
            st.write(c["created"].strftime("%Y-%m-%d %H:%M") if c["created"] else "-")
        with cols[2]:
            st.caption("共有URL")
            st.code(url, language="text")
        with cols[3]:
            st.caption("操作")
            st.link_button("開く（新規タブ）", url, type="primary")
        with cols[4]:
            # 個別削除
            if st.button("🗑️", key=f"del-{c['id']}"):
                try:
                    if c["path"].exists():
                        c["path"].unlink()
                        st.experimental_rerun()
                except Exception:
                    st.error("削除に失敗しました")