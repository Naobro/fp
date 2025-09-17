# client_portal.py — お客様専用ページ（URLの ?client=ID で表示／DBはSQLite）
import streamlit as st
import sqlite3, json
from datetime import datetime
from contextlib import contextmanager

# -------------------------------
# 画面設定
# -------------------------------
st.set_page_config(page_title="お客様 専用ページ", layout="wide")

# -------------------------------
# 設定（admin と同じDBを使用／Streamlit以外＝SQLiteで永続化）
# -------------------------------
DB_PATH = "clients.db"  # pages/1_admin.py と同じパスを利用
BASE_URL = st.secrets.get("BASE_URL", "/client_portal")  # 例: /client_portal または https://<app>/client_portal


# -------------------------------
# DBユーティリティ（読み取り専用運用）
# -------------------------------
@contextmanager
def get_db():
    # 読み取り主体のためWAL等は未設定。初期化やDROP等の書込みは一切しない。
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def load_client(client_id: str) -> dict | None:
    if not client_id:
        return None
    with get_db() as conn:
        row = conn.execute(
            "SELECT data FROM clients WHERE client_id = ?",
            (client_id,)
        ).fetchone()
        if not row:
            return None
        try:
            return json.loads(row["data"])
        except Exception:
            return None

def share_url_for(cid: str) -> str:
    # secretsに本番URLがあればそれを優先。なければ相対パスで返す。
    if BASE_URL:
        return f"{BASE_URL.rstrip('/')}?client={cid}"
    # 相対（同一アプリ内遷移用）
    return f"./client_portal?client={cid}"

# -------------------------------
# クエリパラメータから client を取得
# -------------------------------
qp = st.query_params
client_id = qp.get("client", [None])[0] if isinstance(qp.get("client", None), list) else qp.get("client", None)

# -------------------------------
# ID未指定時：ID入力→同一ページにクエリ付与して再表示
# -------------------------------
with st.container():
    st.title("お客様 専用ページ")

    if not client_id:
        st.info("URLに `?client=ID` を付けてアクセスするか、下の欄にIDを入力してください。")
        id_in = st.text_input("クライアントID（例：c-abc123）", value="")
        col_a, col_b = st.columns([1, 3])
        with col_a:
            if st.button("開く"):
                _id = id_in.strip()
                if _id:
                    # クエリパラメータを書き換えてリロード（セッション状態に依存しない＝初期化バグ回避）
                    st.query_params.update({"client": _id})
                    st.rerun()
        st.stop()

# -------------------------------
# クライアント読込
# -------------------------------
payload = load_client(client_id)

if not payload:
    st.error("指定されたクライアントIDのデータが見つかりませんでした。IDを確認してください。")
    # 代替入力UI
    with st.expander("IDを再入力する"):
        id_in = st.text_input("クライアントIDを再入力", key="retry_id")
        if st.button("このIDで開く", key="retry_btn"):
            _id = id_in.strip()
            if _id:
                st.query_params.update({"client": _id})
                st.rerun()
    st.stop()

# -------------------------------
# 表示用メタの取り出し
# -------------------------------
meta = payload.get("meta", {})
name = (meta.get("name") or "").strip()
display_name = name if name else "(無名)"

# 「〇〇様 専用ページ」— admin入力の氏名をそのまま反映
st.header(f"{display_name}様 専用ページ")

# 概要カード
cid = meta.get("client_id") or client_id
created_raw = meta.get("created_at")
try:
    created_dt = datetime.fromisoformat(created_raw) if created_raw else None
except Exception:
    created_dt = None

c1, c2, c3 = st.columns([2,2,3])
with c1:
    st.caption("クライアントID")
    st.code(cid, language="text")
with c2:
    st.caption("作成日時")
    st.write(created_dt.strftime("%Y-%m-%d %H:%M") if created_dt else "-")
with c3:
    st.caption("共有URL")
    st.code(share_url_for(cid), language="text")
    st.link_button("このURLを開く（新規タブ）", share_url_for(cid))

st.divider()

# -------------------------------
# ここから各種セクション（必要に応じて拡張）
# ※ セッションに依存せず、DBの値を“表示”中心にすることで初期化バグを回避
# -------------------------------

# 基本指標（存在すれば表示）
baseline = payload.get("baseline", {})
prefs    = payload.get("prefs", {})
listings = payload.get("listings", [])

with st.expander("ご登録情報（読み取り）", expanded=True):
    colA, colB = st.columns(2)
    with colA:
        st.subheader("希望条件（prefs）", divider="gray")
        st.json(prefs)
    with colB:
        st.subheader("基礎データ（baseline）", divider="gray")
        st.json(baseline)

st.subheader("候補物件リスト（listings）", divider="gray")
if not listings:
    st.info("現在、候補物件は登録されていません。")
else:
    # 表示専用（編集はadmin側で）
    for i, item in enumerate(listings, start=1):
        with st.container(border=True):
            st.write(f"#{i}")
            st.json(item)

st.caption("※ 本ページは読み取り中心。編集・新規登録・削除等の操作は管理画面（admin）で実施してください。")
