import streamlit as st
import json
import sqlite3
import os
from contextlib import contextmanager

st.set_page_config(page_title="専用ページ", layout="wide")

# ----- admin.py からコピーする共通コード -----
DB_PATH = "pages/clients.db"

@contextmanager
def get_db():
    """データベース接続のコンテキストマネージャー"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 辞書形式でアクセス可能
    try:
        yield conn
    finally:
        conn.close()

def _has_column(conn: sqlite3.Connection, table: str, col: str) -> bool:
    """指定されたテーブルに指定されたカラムが存在するかチェックする"""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"] == col for r in rows)

def ensure_schema():
    """テーブル作成＋不足カラムの追加（admin.py からコピー）"""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                client_id TEXT PRIMARY KEY,
                created_at TEXT,
                name TEXT,
                phone TEXT,
                email TEXT,
                memo TEXT,
                data TEXT NOT NULL
            )
        """)
        if not _has_column(conn, "clients", "idempotency_key"):
            try:
                conn.execute("ALTER TABLE clients ADD COLUMN idempotency_key TEXT")
            except sqlite3.OperationalError:
                pass
        if not _has_column(conn, "clients", "created_at_utc"):
            try:
                conn.execute("ALTER TABLE clients ADD COLUMN created_at_utc TEXT")
            except sqlite3.OperationalError:
                pass
        try:
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_clients_idem ON clients(idempotency_key)")
        except sqlite3.OperationalError:
            pass
        conn.commit()

# スキーマを保証することで、DBファイルが存在しない場合は作成される
ensure_schema()


def load_client_from_db(client_id: str) -> dict | None:
    """指定されたクライアントIDのデータをデータベースから読み込む"""
    with get_db() as conn:
        # この行は既に存在するため、try-exceptブロックで保護
        try:
            row = conn.execute("SELECT data FROM clients WHERE client_id = ?", (client_id,)).fetchone()
            return json.loads(row["data"]) if row and row["data"] else None
        except sqlite3.OperationalError:
            return None


# ----- クエリ取得（新旧API両対応） -----
def get_qp(name: str, default: str = "") -> str:
    try:
        val = st.query_params.get(name, "")
        if isinstance(val, list):
            return val[0] if val else default
        return val or default
    except Exception:
        val = st.experimental_get_query_params().get(name, [default])
        return val[0] if isinstance(val, list) else (val or default)

client_id = get_qp("client")

if not client_id:
    st.error("client パラメータがありません。例： /client_portal?client=c-xxxxx")
    st.stop()

# ----- データベースから顧客情報をロード -----
client_data_raw = load_client_from_db(client_id)

if client_data_raw is None:
    st.error(f"指定された顧客ID '{client_id}' は見つかりませんでした。")
    st.stop()

# 顧客名と物件名を取得
client_meta = client_data_raw.get("meta", {})
client_name = client_meta.get("name", "お客様")
property_name = client_data_raw.get("property", None)

# ----- ヘッダー -----
st.markdown(f"# {client_name} 様 専用ページ")
if property_name:
    st.markdown(f"<span style='font-size: small; color: grey;'>物件：{property_name}</span>", unsafe_allow_html=True)

# ----- 導線（5つのピル） -----
st.markdown("""
<style>
    .stButton > button {
        border-radius: 20px;
        padding: 5px 15px;
        width: 100%;
        margin-bottom: 5px;
    }
    .pill-container {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        justify-content: space-between;
    }
</style>
""", unsafe_allow_html=True)

col1, col2, col3, col4, col5 = st.columns(5, gap="small")

with col1:
    st.link_button("① ヒアリング", f"/hearing?client={client_id}", use_container_width=True)
with col2:
    st.link_button("② 住宅ローン", f"/pages/住宅ローン提案?client={client_id}", use_container_width=True)
with col3:
    st.link_button("③ スケジュール", "https://docs.google.com/spreadsheets/...", use_container_width=True)
with col4:
    st.link_button("④ 物件比較", f"/compare?client={client_id}", use_container_width=True)
with col5:
    st.link_button("⑤ 諸費用明細", f"/pages/諸費用明細?client={client_id}", use_container_width=True)

st.divider()

# ----- 小さめカード + QRコード -----
with st.container(border=True):
    col_text, col_qr = st.columns([0.7, 0.3])
    with col_text:
        st.markdown("このページはご案内の入口です。ご不明点はLINEでご連絡ください。", unsafe_allow_html=True)
    with col_qr:
        st.image("https://example.com/qr-code.png", width=100)

st.divider()

# ----- 各機能の1行説明 -----
st.markdown("""
- **ヒアリング**: ご希望条件や優先度の確認
- **住宅ローン**: 金利設定済みの提案書PDF
- **スケジュール**: 進行状況・ToDoはスプレッドシートで共有
- **物件比較**: 候補の比較・内見チェック
- **諸費用明細**: 概算→確定へ更新されるPDF
""")

# ----- フッター -----
st.markdown("---")
st.caption("このページのURLと顧客コードはお客様と担当者のみで共有しています。")
st.markdown("TERASS / Naoki Nishiyama", help="担当者名", unsafe_allow_html=True)
