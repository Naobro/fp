import streamlit as st
import json, secrets, string
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import pandas as pd
import sqlite3
import os

# 画面設定
st.set_page_config(page_title="管理：お客様ページ 管理", layout="wide")

# データベース設定
# Streamlit Cloudの永続化パス
DB_PATH = os.path.join(os.path.dirname(__file__), 'client_data.db')

def get_db_connection():
    """SQLiteデータベースへの接続を確立する"""
    conn = sqlite3.connect(DB_PATH)
    return conn

def init_db():
    """データベースとテーブルを初期化する"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            client_id TEXT PRIMARY KEY,
            name TEXT,
            property TEXT,
            created_at_utc TEXT,
            data TEXT
        );
    """)
    conn.commit()
    conn.close()

# アプリ起動時にデータベースを初期化
init_db()

# 共有URL（本番URLを secrets で上書き可）
BASE_URL = st.secrets.get("BASE_URL", "https://naobro-fp.streamlit.app/client_portal")

# 定数
CLIENT_ID_LENGTH = 6
IDEMPOTENCY_KEY_LENGTH = 16

# -------------------------------
# データ管理
# -------------------------------
def load_all_clients():
    """SQLiteから全クライアントを読み込む"""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM clients;", conn)
    conn.close()

    df.columns = ["client_id", "name", "property", "created_at_utc", "data"]
    df = df.dropna(subset=["client_id"])
    
    items = []
    for _, row in df.iterrows():
        items.append({
            "id": row["client_id"],
            "name": row["name"] or "(無名)",
            "created_utc": row["created_at_utc"],
            "created_jst": to_jst_str(row["created_at_utc"]),
            "raw": json.loads(row["data"]) if row["data"] else {}
        })
    return items

def gen_id(n: int = CLIENT_ID_LENGTH) -> str:
    """クライアントID生成"""
    alphabet = string.ascii_lowercase + string.digits
    return "c-" + "".join(secrets.choice(alphabet) for _ in range(n))

def save_client(client_id: str, name: str, payload: dict):
    """SQLiteにクライアントを保存"""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO clients (client_id, name, created_at_utc, data) VALUES (?, ?, ?, ?);",
                  (client_id, name, utc_now_iso(), json.dumps(payload, ensure_ascii=False)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # 重複エラー
        return False
    finally:
        conn.close()

def delete_client(client_id: str) -> bool:
    """SQLiteからクライアントを削除"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM clients WHERE client_id = ?;", (client_id,))
    rows_deleted = c.rowcount
    conn.commit()
    conn.close()
    return rows_deleted > 0

def share_url_for(cid: str) -> str:
    base = BASE_URL.rstrip("/")
    return f"{base}?client={cid}"

def utc_now_iso() -> str:
    """UTCのISO8601（末尾Z）"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def to_jst_str(utc_iso: str) -> str:
    """UTC(ISO) → JST 文字列"""
    if not utc_iso:
        return "-"
    try:
        if utc_iso.endswith("Z"):
            dt = datetime.strptime(utc_iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        else:
            dt = datetime.fromisoformat(utc_iso)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return f"Invalid date format: {utc_iso}"
    except Exception as e:
        return f"Error converting date: {e} ({utc_iso})"

# -------------------------------
# 新規発行
# -------------------------------
st.header("お客様ページの新規発行")

if "__create_idem__" not in st.session_state:
    st.session_state["__create_idem__"] = None

with st.form("new_client"):
    name = st.text_input("お客様名")
    submitted = st.form_submit_button("新規作成", type="primary")

if submitted:
    name_clean = (name or "").strip()
    if not name_clean:
        st.error("お客様名は必須です。")
        st.session_state["__create_idem__"] = None
        st.stop()
    
    idem = st.session_state.get("__create_idem__")
    if not idem:
        idem = secrets.token_hex(IDEMPOTENCY_KEY_LENGTH)
        st.session_state["__create_idem__"] = idem
    
    client_id = gen_id()
    
    payload = {
        "meta": {
            "client_id": client_id,
            "name": name_clean,
            "created_at_utc": utc_now_iso()
        }
    }
    
    ok = save_client(client_id, name_clean, payload)

    url = share_url_for(client_id)
    if ok:
        st.success("お客様用URLを発行しました。")
        st.code(url, language="text")
        st.link_button("➡️ このままお客様ページを開く（新規タブ）", url, type="primary")
    else:
        st.info("同じ操作がすでに登録済みです。")
        st.code(url, language="text")
        st.link_button("➡️ お客様ページを開く（新規タブ）", url, type="primary")

    if st.button("＋ もう一件登録する"):
        st.session_state["__create_idem__"] = None
        st.rerun()

st.divider()

# -------------------------------
# 一覧・検索・即アクセス・削除
# -------------------------------
st.header("お客様ページ 一覧")

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
def jst_sort_key(c):
    return c["created_jst"] or ""

if sort_key == "作成が新しい順":
    clients.sort(key=jst_sort_key, reverse=True)
elif sort_key == "作成が古い順":
    clients.sort(key=jst_sort_key)
elif sort_key == "名前（A→Z）":
    clients.sort(key=lambda x: (x["name"] or "").lower())
else:
    clients.sort(key=lambda x: (x["name"] or "").lower(), reverse=True)

# 行表示
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
            st.caption("作成日時（JST）")
            st.write(c["created_jst"])
        with cols[2]:
            st.caption("共有URL")
            if url:
                st.code(url, language="text")
            else:
                st.caption("URL生成エラー")
        with cols[3]:
            st.caption("操作")
            if url:
                st.link_button("開く（新規タブ）", url, type="primary")
            else:
                st.warning("無効なURLです")
        with cols[4]:
            delete_confirmed = st.session_state.get(f"confirm_delete_{c['id']}", False)
            if not delete_confirmed:
                if st.button("🗑️", key=f"del_prompt-{c['id']}"):
                    st.session_state[f"confirm_delete_{c['id']}"] = True
                    st.rerun()
            else:
                st.warning(f"本当に {c['name']} を削除しますか？")
                confirm_col1, confirm_col2 = st.columns(2)
                with confirm_col1:
                    if st.button("はい、削除する", key=f"del_yes-{c['id']}"):
                        if delete_client(c["id"]):
                            st.success("削除しました")
                            del st.session_state[f"confirm_delete_{c['id']}"]
                            st.rerun()
                        else:
                            st.error("削除に失敗しました")
                with confirm_col2:
                    if st.button("キャンセル", key=f"del_no-{c['id']}"):
                        del st.session_state[f"confirm_delete_{c['id']}"]
                        st.rerun()
        st.markdown("---")
