import streamlit as st
import json
import base64
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import numpy as np
import numpy_financial as npf
from fpdf import FPDF
import requests
import re
import matplotlib.pyplot as plt
import matplotlib as mpl

# Set Streamlit page config
st.set_page_config(page_title="お客様ページ", layout="wide")

# --- Database & Config ---
conn = st.connection("gsheets", type=GSheetsConnection)
SPREADSHEET_NAME = "client_data"
WORKSHEET_NAME = "Sheet1"

def load_client_from_db(client_id: str) -> dict | None:
    """指定されたクライアントIDのデータをデータベースから読み込む"""
    df = conn.read(spreadsheet=SPREADSHEET_NAME, worksheet=WORKSHEET_NAME, ttl=5)
    df.columns = ["client_id", "name", "property", "created_at_utc", "data"]
    
    row = df[df["client_id"] == client_id].iloc[0] if not df[df["client_id"] == client_id].empty else None
    
    if row is not None and row["data"]:
        return json.loads(row["data"])
    return None

def update_client_in_db(client_id: str, new_data: dict):
    """データベース内のクライアントデータを更新する"""
    df = conn.read(spreadsheet=SPREADSHEET_NAME, worksheet=WORKSHEET_NAME, ttl=5)
    df.columns = ["client_id", "name", "property", "created_at_utc", "data"]
    
    # 既存の行を見つける
    row_index = df[df["client_id"] == client_id].index
    
    if not row_index.empty:
        # 新しいデータをJSON文字列に変換
        df.loc[row_index, "data"] = json.dumps(new_data, ensure_ascii=False)
        df.loc[row_index, "property"] = new_data.get("property_info", {}).get("property_name")
        
        # シート全体を更新
        conn.clear(spreadsheet=SPREADSHEET_NAME, worksheet=WORKSHEET_NAME)
        conn.append(
            spreadsheet=SPREADSHEET_NAME,
            worksheet=WORKSHEET_NAME,
            data=df
        )
        return True
    return False

# --- Utility functions ---
def get_query_param(param_name):
    """URLクエリパラメータを取得する（新旧API両対応）"""
    return st.experimental_get_query_params().get(param_name, [None])[0]

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

def get_real_estate_data(property_url):
    # This is a placeholder for your web scraping logic
    st.info("物件情報の取得は現在開発中の機能です。")
    return None

def calculate_finance(loan_amount, interest_rate, years):
    try:
        rate = interest_rate / 12 / 100
        nper = years * 12
        pmt = npf.pmt(rate, nper, -loan_amount)
        return round(pmt)
    except Exception:
        return 0

def create_financial_plan(plan_data):
    # This is a placeholder for your PDF generation logic
    st.info("PDF作成機能は現在開発中です。")
    return None

def create_download_link(file_data, filename, file_type):
    b64 = base64.b64encode(file_data).decode()
    href = f'<a href="data:{file_type};base64,{b64}" download="{filename}">ダウンロード</a>'
    return href

def generate_pdf_financial_plan(plan_data):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.add_font("meiryo", "", "Meiryo.ttf", uni=True)
        pdf.set_font("meiryo", size=12)
        
        pdf.cell(200, 10, txt="住宅ローン返済計画書", ln=1, align="C")
        pdf.ln(10)
        
        pdf.cell(200, 10, txt=f"お客様名: {plan_data.get('client_info', {}).get('name', '未設定')}", ln=1)
        pdf.cell(200, 10, txt=f"物件名: {plan_data.get('property_info', {}).get('property_name', '未設定')}", ln=1)
        
        pdf_output = pdf.output(dest="S").encode("latin-1")
        return pdf_output
    except Exception as e:
        st.error(f"PDF生成エラー: {e}")
        return None

# --- Main app flow ---
client_id = get_query_param("client")

if not client_id:
    st.error("有効なクライアントIDがURLに指定されていません。")
    st.stop()

# --- データベースから顧客情報をロード ---
client_data_raw = load_client_from_db(client_id)

if client_data_raw is None:
    st.error(f"指定された顧客ID '{client_id}' は見つかりませんでした。URLを確認してください。")
    st.stop()

# --- データをセッションステートに初期化 ---
if "client_data" not in st.session_state or st.session_state["client_data"].get("meta", {}).get("client_id") != client_id:
    st.session_state["client_data"] = client_data_raw
    st.session_state["data_changed"] = False

client_data = st.session_state["client_data"]
meta = client_data.get("meta", {})
plan_data = client_data.get("plan_data", {})
client_info = plan_data.get("client_info", {})
property_info = plan_data.get("property_info", {})
loan_info = plan_data.get("loan_info", {})

st.title(f"{meta.get('name', 'お客様')}様")
st.subheader("住宅購入シミュレーション・資金計画書")

# --- Tab UI ---
tab1, tab2, tab3 = st.tabs(["資金計画", "シミュレーション", "共有・ダウンロード"])

with tab1:
    st.header("資金計画書")
    
    with st.expander("お客様情報", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("お客様名", value=client_info.get("name", ""), key="input_name")
        with col2:
            email = st.text_input("メールアドレス", value=client_info.get("email", ""), key="input_email")
        
        if st.button("お客様情報を更新", key="update_client_info"):
            client_data["plan_data"]["client_info"]["name"] = name
            client_data["plan_data"]["client_info"]["email"] = email
            st.session_state["data_changed"] = True
            st.rerun()

    with st.expander("物件情報", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            property_name = st.text_input("物件名", value=property_info.get("property_name", ""), key="input_prop_name")
        with col2:
            property_price = st.number_input("物件価格（万円）", value=property_info.get("property_price", 0), min_value=0, step=10, key="input_prop_price")

        st.markdown("---")
        property_url = st.text_input("物件URLから自動入力", value=st.session_state.get("property_url_input", ""), key="input_prop_url")
        if st.button("物件情報を取得", key="fetch_prop_info"):
            st.session_state["property_url_input"] = property_url
            if property_url:
                with st.spinner("物件情報を取得中..."):
                    fetched_data = get_real_estate_data(property_url)
                    if fetched_data:
                        client_data["plan_data"]["property_info"].update(fetched_data)
                        st.session_state["data_changed"] = True
                        st.rerun()
            else:
                st.warning("物件URLを入力してください。")
        
        if st.button("物件情報を更新", key="update_prop_info"):
            client_data["plan_data"]["property_info"]["property_name"] = property_name
            client_data["plan_data"]["property_info"]["property_price"] = property_price
            st.session_state["data_changed"] = True
            st.rerun()

with tab2:
    st.header("住宅ローンシミュレーション")

    with st.expander("ローン条件", expanded=True):
        loan_amount = st.number_input("借入希望額（万円）", value=loan_info.get("loan_amount", 3000), min_value=10, step=10, key="input_loan_amount")
        interest_rate = st.number_input("金利（年利％）", value=loan_info.get("interest_rate", 1.0), min_value=0.01, max_value=10.0, step=0.01, key="input_interest_rate")
        loan_years = st.number_input("返済期間（年）", value=loan_info.get("loan_years", 35), min_value=1, max_value=50, step=1, key="input_loan_years")
        
        if st.button("シミュレーションを実行", key="run_simulation"):
            client_data["plan_data"]["loan_info"]["loan_amount"] = loan_amount
            client_data["plan_data"]["loan_info"]["interest_rate"] = interest_rate
            client_data["plan_data"]["loan_info"]["loan_years"] = loan_years
            st.session_state["data_changed"] = True
            st.rerun()

    st.subheader("結果")
    monthly_payment = calculate_finance(loan_amount * 10000, interest_rate, loan_years)
    st.metric("毎月の返済額", f"¥{monthly_payment:,}", "円")

with tab3:
    st.header("共有とダウンロード")
    
    st.info("このページは、お客様がいつでもアクセスできる専用のURLです。")
    
    st.subheader("資金計画書のPDF")
    
    if st.button("PDFを作成"):
        with st.spinner("PDFを作成中..."):
            pdf_data = generate_pdf_financial_plan(plan_data)
            if pdf_data:
                b64_pdf = base64.b64encode(pdf_data).decode('utf-8')
                st.markdown(
                    f"""
                    <a href="data:application/pdf;base64,{b64_pdf}" download="資金計画書_{meta['name']}.pdf">
                        <button style="background-color:#4CAF50;color:white;padding:10px 20px;border-radius:5px;border:none;">
                            ダウンロード
                        </button>
                    </a>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.error("PDFの作成に失敗しました。")

# --- セッションステートの更新とデータベースへの保存 ---
if st.session_state.get("data_changed", False):
    with st.spinner("変更内容を保存中..."):
        update_client_in_db(client_id, st.session_state["client_data"])
        st.session_state["data_changed"] = False
        st.success("変更が保存されました！")
