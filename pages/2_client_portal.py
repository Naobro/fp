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

def load_client_from_db(client_id: str) -> dict | None:
    """指定されたクライアントIDのデータをデータベースから読み込む"""
    with get_db() as conn:
        row = conn.execute("SELECT data FROM clients WHERE client_id = ?", (client_id,)).fetchone()
        return json.loads(row["data"]) if row and row["data"] else None

# ----- クエリ取得（新旧API両対応） -----
def get_qp(name: str, default: str = "") -> str:
    try:
        # 新API
        val = st.query_params.get(name, "")
        if isinstance(val, list):
            return val[0] if val else default
        return val or default
    except Exception:
        # 旧API
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
# NOTE: admin.pyのコードには物件情報の保存部分が見当たらないため、
# もし物件情報を表示したい場合は、admin側で物件名を保存するロジックを
# 追加する必要があります。

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
        margin-bottom: 5px; /* スマホでの縦並び用 */
    }
    .pill-container {
        display: flex;
        flex-wrap: wrap; /* スマホで折り返す */
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
        # 実際はここでQRコード画像を生成・表示
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
