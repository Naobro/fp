import streamlit as st
import json
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="専用ページ", layout="wide")

# データベース設定
conn = st.connection("gsheets", type=GSheetsConnection)
SPREADSHEET_NAME = "client_data" # スプレッドシート名
WORKSHEET_NAME = "Sheet1" # シート名

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
def load_client_from_gsheets(client_id):
    try:
        df = conn.read(
            spreadsheet=SPREADSHEET_NAME,
            worksheet=WORKSHEET_NAME,
            usecols=list(range(5)),
            ttl=5 # 5秒間キャッシュ
        )
        df.columns = ["client_id", "name", "property", "created_at_utc", "data"]
        row = df[df["client_id"] == client_id].iloc[0]
        return row
    except (pd.errors.EmptyDataError, IndexError):
        return None

client_data_row = load_client_from_gsheets(client_id)

if client_data_row is None:
    st.error(f"指定された顧客ID '{client_id}' は見つかりませんでした。")
    st.stop()

# 顧客名と物件名を取得
client_name = client_data_row.get("name", "お客様")
property_name = client_data_row.get("property", None)

# ----- ヘッダー -----
st.markdown(f"# {client_name} 様 専用ページ")
if property_name and property_name != "null":
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
