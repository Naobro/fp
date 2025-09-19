# pages/1_admin.py  — 管理画面（新規発行・一覧・検索・即アクセス・削除）
# ✅ データベース：Streamlit内キー/値ストア（ローカルJSONベース）
#  - SQLite/GSheetsを使わず、Key/ValueでUPSERT保存
#  - 単一ファイル kv_clients.json に { client_id: レコード } 形式で永続化
#  - 画面上で新規発行・一覧・検索・即アクセス・削除・バックアップDL対応
#  - 注意：Streamlit Cloudでは再デプロイ/コンテナ再生成でファイルは初期化されるため、定期的にバックアップDL推奨
import streamlit as st
import json, secrets, string, os, io, threading
from datetime import datetime
from contextlib import contextmanager

# 画面設定
st.set_page_config(page_title="管理：お客様ページ 管理", layout="wide")

# 共有URL（本番URLを secrets で上書き可）
# 既定は ルート直下 /?client=ID を発行（TOPでルータが client_portal を描画）
BASE_URL = st.secrets.get("BASE_URL", "https://naokifp.streamlit.app/")

def share_url_for(cid: str) -> str:
    """共有URL生成（https指定時は完全URL／未指定は /?client=ID）"""
    base = (BASE_URL or "/").rstrip("/")
    if base.startswith("http"):
        return f"{base}/?client={cid}"
    return f"{base}?client={cid}"

# ===============================
# Key/Value ストア（JSONファイル）
# ===============================
class KVStore:
    """
    シンプルなKey/Valueストア
    - ファイル：kv_clients.json
    - 形式：{"clients": { "<client_id>": { ...保存データ... }, ... }}
    - 競合対策：スレッドロック
    """
    def __init__(self, path: str = "kv_clients.json"):
        self.path = path
        self._lock = threading.RLock()
        # 初期化
        if not os.path.exists(self.path):
            self._write({"clients": {}})

    def _read(self) -> dict:
        with self._lock:
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {"clients": {}}

    def _write(self, data: dict) -> None:
        with self._lock:
            tmp_path = self.path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.path)

    # ------- Public API -------
    def get(self, key: str) -> dict | None:
        data = self._read()
        return data.get("clients", {}).get(key)

    def set(self, key: str, value: dict) -> None:
        data = self._read()
        if "clients" not in data:
            data["clients"] = {}
        data["clients"][key] = value
        self._write(data)

    def delete(self, key: str) -> bool:
        data = self._read()
        if key in data.get("clients", {}):
            del data["clients"][key]
            self._write(data)
            return True
        return False

    def all(self) -> dict:
        data = self._read()
        return data.get("clients", {})

    def count(self) -> int:
        return len(self.all())

    def snapshot_bytes(self) -> bytes:
        """現在の全データをJSONバイト列で返す（ダウンロード用）"""
        buf = io.StringIO()
        json.dump({"clients": self.all()}, buf, ensure_ascii=False, indent=2)
        return buf.getvalue().encode("utf-8")

# KV初期化（アプリ起動時1回）
@st.cache_resource(show_spinner=False)
def get_kv() -> KVStore:
    return KVStore(path=st.secrets.get("KV_PATH", "kv_clients.json"))

KV = get_kv()

# -------------------------------
# 共通ユーティリティ
# -------------------------------
def gen_id(n: int = 6) -> str:
    """クライアントID生成"""
    alphabet = string.ascii_lowercase + string.digits
    return "c-" + "".join(secrets.choice(alphabet) for _ in range(n))

def save_client(client_id: str, payload: dict):
    """クライアントデータをKey/Valueに保存（UPSERT）"""
    # メタ補完
    meta = payload.get("meta", {})
    if not meta.get("client_id"):
        meta["client_id"] = client_id
    if not meta.get("created_at"):
        meta["created_at"] = datetime.now().isoformat()
    payload["meta"] = meta
    # 保存
    KV.set(client_id, payload)

def load_client(client_id: str) -> dict | None:
    """特定のクライアントデータを読み込み"""
    return KV.get(client_id)

def load_all_clients() -> list[dict]:
    """全クライアントデータを読み込み（UI表示用に整形）"""
    raw = KV.all()
    # {id: payload} -> list[{...}]
    out = []
    for cid, payload in raw.items():
        meta = payload.get("meta", {})
        # 作成日時をdatetimeへ（表示用）
        created = None
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
            "raw": payload
        })
    # 既定：新しい順
    out.sort(key=lambda x: x["created"] or datetime.fromtimestamp(0), reverse=True)
    return out

def delete_client(client_id: str) -> bool:
    """クライアントを削除"""
    return KV.delete(client_id)

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
    save_client(client_id, payload)

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
def default_time(d):
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
            if "（" in label and "）" in label:
                cid = label.split("（")[-1].split("）")[0]
                pick_ids.append(cid)

        for cid in pick_ids:
            if delete_client(cid):
                deleted += 1

        if deleted > 0:
            st.success(f"{deleted} 件削除しました。")
            st.rerun()

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
            if st.button("🗑️", key=f"del-{c['id']}"):
                if delete_client(c["id"]):
                    st.success("削除しました")
                    st.rerun()
                else:
                    st.error("削除に失敗しました")

# -------------------------------
# データベース管理ユーティリティ（デバッグ用）
# -------------------------------
with st.expander("🔧 データベース管理（デバッグ用）"):
    st.caption("データベースの状態確認・メンテナンス用")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("DB統計表示"):
            st.write(f"総レコード数: {KV.count()}")
            # 期間はKVに明示保持していないため、created_at最小/最大を走査
            all_items = load_all_clients()
            oldest = min([c["created"] for c in all_items if c["created"]], default=None)
            newest = max([c["created"] for c in all_items if c["created"]], default=None)
            st.write(f"最古: {oldest.isoformat() if oldest else '-'}")
            st.write(f"最新: {newest.isoformat() if newest else '-'}")

    with col2:
        if st.button("DBバックアップ作成"):
            st.download_button(
                "📥 バックアップダウンロード",
                KV.snapshot_bytes(),
                file_name=f"clients_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

    with col3:
        if st.button("⚠️ DB全削除（危険）"):
            st.warning("この操作は全データを削除します！実行前に必ずバックアップを取ってください。")
