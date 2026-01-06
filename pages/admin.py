# pages/1_admin.py  — 管理画面（新規発行・一覧・検索・即アクセス・削除）
# ✅ Supabase 連携／Key-Value 保存／削除・バックアップ機能付き（最新版）
import streamlit as st
import json, secrets, string, io
from datetime import datetime
from auth import check_admin
check_admin()

# ------------------------------------
# ページ設定
# ------------------------------------
st.set_page_config(page_title="管理：お客様ページ 管理", layout="wide")

BASE_URL = st.secrets.get("BASE_URL", "https://naokifp.streamlit.app/")

def share_url_for(cid: str) -> str:
    base = (BASE_URL or "/").rstrip("/")
    if base.startswith("http"):
        return f"{base}/?client={cid}"
    return f"{base}?client={cid}"

# ------------------------------------
# Supabase Key-Value ストア
# ------------------------------------
from client_portal import get_sb
SB = get_sb()
TABLE_NAME = "client_profiles"


class KVStore:
    """Supabase に安全保存する Key-Value ストア"""

    def __init__(self):
        self.sb = SB

    def get(self, key: str) -> dict | None:
        if not self.sb:
            return None
        res = (
            self.sb.table(TABLE_NAME)
            .select("*")
            .eq("client_id", key)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    def set(self, key: str, value: dict) -> None:
        if not self.sb or not isinstance(value, dict):
            return

        meta_src = value.get("meta") if isinstance(value.get("meta"), dict) else {}
        name = value.get("name") or meta_src.get("name")
        if not name or str(name).strip() == "":
            name = "(未入力)"

        src_meta = dict(meta_src)
        src_meta["client_id"] = key
        src_meta["name"] = name
        src_meta["created_at"] = src_meta.get("created_at") or datetime.now().isoformat()

        def safe_json(d: dict) -> dict:
            clean = {}
            for k, v in d.items():
                try:
                    json.dumps(v)
                    clean[k] = v
                except Exception:
                    continue
            return clean

        clean_meta = safe_json(src_meta)
        clean_profile = safe_json(value.get("profile") if isinstance(value.get("profile"), dict) else {})

        record = {
            "client_id": key,
            "name": name,
            "meta": clean_meta,
            "profile": clean_profile,
            "updated_at": datetime.now().isoformat(),
        }

        try:
            self.sb.table(TABLE_NAME).upsert(record, on_conflict="client_id").execute()
        except Exception as e:
            st.error(f"Supabase upsert 失敗: {e}")
            raise

    def delete(self, key: str) -> bool:
        if not self.sb:
            return False
        try:
            self.sb.table(TABLE_NAME).delete().eq("client_id", key).execute()
            return True
        except Exception as e:
            st.error(f"削除失敗: {e}")
            return False

    def all(self) -> dict:
    if not self.sb:
        return {}
    res = self.sb.table(TABLE_NAME).select("*").timeout(10).execute()
    out = {}
    for row in res.data:
        out[row["client_id"]] = row
    return out

    def count(self) -> int:
        return len(self.all())

    def snapshot_bytes(self) -> bytes:
        buf = io.StringIO()
        json.dump({"clients": self.all()}, buf, ensure_ascii=False, indent=2)
        return buf.getvalue().encode("utf-8")


@st.cache_resource(show_spinner=False)
def get_kv() -> KVStore:
    return KVStore()


KV = get_kv()

# ------------------------------------
# ユーティリティ
# ------------------------------------
def gen_id(n: int = 6) -> str:
    return "c-" + "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(n))

def save_client(client_id: str, payload: dict):
    meta = payload.get("meta", {})
    name = meta.get("name") or payload.get("name")

    meta["name"] = name
    meta["client_id"] = client_id
    meta["created_at"] = meta.get("created_at") or datetime.now().isoformat()
    payload["meta"] = meta
    payload["name"] = name
    KV.set(client_id, payload)
    st.toast(f"💾 {name} 様を保存しました", icon="✅")

def load_all_clients() -> list[dict]:
    raw = KV.all()
    out = []
    for cid, payload in raw.items():
        meta = payload.get("meta", {})
        try:
            created = datetime.fromisoformat(meta.get("created_at")) if meta.get("created_at") else None
        except Exception:
            created = None
        out.append({
            "id": cid,
            "name": meta.get("name") or "(無名)",
            "created": created,
            "phone": meta.get("phone"),
            "email": meta.get("email"),
            "memo": meta.get("memo"),
        })
    out.sort(key=lambda x: x["created"] or datetime.fromtimestamp(0), reverse=True)
    return out

def delete_client(client_id: str) -> bool:
    return KV.delete(client_id)

# ------------------------------------
# 新規発行（必須入力+バリデーション対応）
# ------------------------------------
st.header("🆕 お客様ページの新規発行（PINなし）")

with st.form("new_client"):
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("お客様名")  # ← required=True は削除済み
        phone = st.text_input("電話番号（任意）")
    with c2:
        email = st.text_input("メール（任意）")
        memo  = st.text_area("管理メモ（任意）", height=80)
    submitted = st.form_submit_button("新規作成", type="primary")

if submitted:
    if not name.strip():
        st.error("お客様名を入力してください。")
    else:
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
            "baseline": {},
            "prefs": {},
            "listings": []
        }
        save_client(client_id, payload)
        url = share_url_for(client_id)
        st.success("お客様用URLを発行しました。下のリンクを共有してください。")
        st.code(url, language="text")
        st.link_button("➡️ このままお客様ページを開く（新規タブ）", url, type="primary")

st.divider()

# ------------------------------------
# 一覧・検索・削除
# ------------------------------------
st.header("📋 お客様ページ 一覧")

clients = load_all_clients()
total = len(clients)
c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    q = st.text_input("検索（お客様名／ID）", value="")
with c2:
    sort_key = st.selectbox("並び順", ["作成が新しい順", "作成が古い順", "名前（A→Z）", "名前（Z→A）"])
with c3:
    st.metric("登録件数", total)

if q:
    q_lower = q.strip().lower()
    clients = [c for c in clients if q_lower in (c["name"] or "").lower() or q_lower in c["id"].lower()]

if sort_key == "作成が新しい順":
    clients.sort(key=lambda x: x["created"] or datetime.fromtimestamp(0), reverse=True)
elif sort_key == "作成が古い順":
    clients.sort(key=lambda x: x["created"] or datetime.fromtimestamp(0))
elif sort_key == "名前（A→Z）":
    clients.sort(key=lambda x: x["name"].lower())
else:
    clients.sort(key=lambda x: x["name"].lower(), reverse=True)

if not clients:
    st.info("該当データはありません。")
else:
    for c in clients:
        url = share_url_for(c["id"])
        cols = st.columns([3, 3, 4, 1])
        with cols[0]:
            st.write(f"**{c['name']}**")
            st.caption(f"ID: {c['id']}")
        with cols[1]:
            st.caption("作成日時")
            st.write(c["created"].strftime("%Y-%m-%d %H:%M") if c["created"] else "-")
        with cols[2]:
            st.caption("共有URL")
            st.code(url, language="text")
            st.link_button("開く", url, type="primary")
        with cols[3]:
            if st.button("🗑️", key=f"del-{c['id']}"):
                if delete_client(c["id"]):
                    st.success("削除しました")
                    st.rerun()

st.divider()

# ------------------------------------
# データベース管理（バックアップ・統計）
# ------------------------------------
with st.expander("🔧 データベース管理（デバッグ用）"):
    st.caption("データベース状態確認・バックアップ")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📊 DB統計表示"):
            st.write(f"総レコード数: {KV.count()}")
            all_items = load_all_clients()
            oldest = min([c["created"] for c in all_items if c["created"]], default=None)
            newest = max([c["created"] for c in all_items if c["created"]], default=None)
            st.write(f"最古: {oldest.isoformat() if oldest else '-'}")
            st.write(f"最新: {newest.isoformat() if newest else '-'}")

    with col2:
        if st.button("📥 DBバックアップ作成"):
            st.download_button(
                "バックアップをダウンロード",
                KV.snapshot_bytes(),
                file_name=f"clients_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
from auth import admin_send_ui
admin_send_ui()
