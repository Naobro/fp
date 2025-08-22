# lib/bank_common.py
import streamlit as st
from urllib.parse import urlparse
import re

# ========== 担当者情報（初期値）==========
# 初回だけここを書き換えて保存してください。以降はUIから編集→セッション保存されます。
DEFAULT_STAFF_NAME = "西山 直樹"
DEFAULT_STAFF_EMAIL = "sample@example.com"  # ← あなたのメールに置換推奨

def ensure_staff_state():
    if "staff_name" not in st.session_state:
        st.session_state.staff_name = DEFAULT_STAFF_NAME
    if "staff_email" not in st.session_state:
        st.session_state.staff_email = DEFAULT_STAFF_EMAIL

def staff_header(editable: bool = True):
    """
    ページ上部に担当者情報を横並びで表示（編集可）
    """
    ensure_staff_state()
    c1, c2, c3 = st.columns([1.6, 1.6, 2.8])
    with c1:
        if editable:
            st.session_state.staff_name = st.text_input("担当者名", value=st.session_state.staff_name)
        else:
            st.markdown(f"**担当者名**：{st.session_state.staff_name}")
    with c2:
        if editable:
            st.session_state.staff_email = st.text_input("メールアドレス", value=st.session_state.staff_email)
        else:
            st.markdown(f"**メール**：{st.session_state.staff_email}")
    with c3:
        st.info("修正内容はセッション内で保持されます。", icon="📝")

def github_to_raw(url: str) -> str:
    """
    GitHubの通常URL → rawコンテンツURLに変換
    例:
      https://github.com/user/repo/blob/main/path/file.pdf
      → https://raw.githubusercontent.com/user/repo/main/path/file.pdf
    """
    if "github.com" in url:
        url = url.replace("https://github.com/", "https://raw.githubusercontent.com/")
        url = url.replace("/blob/", "/")
    return url

def pdf_viewer(url: str, height: int = 800):
    """
    PDFを埋め込み表示（横長領域）。GitHubのURLにも対応。
    """
    raw = github_to_raw(url)
    st.markdown(
        f"""
        <iframe src="{raw}" width="100%" height="{height}" style="border:1px solid #ddd; border-radius:8px;"></iframe>
        """,
        unsafe_allow_html=True
    )

def flow_table_horizontal(steps):
    """
    事前審査フローを横長テーブルで表示。
    steps: list[dict] 例：
      [{"step":"STEP1","内容":"ヒアリング","目安":"15分","提出物":"本人確認"} ...]
    """
    # HTMLで横長・大きめ
    html = """
    <style>
      .flowtbl, .flowtbl th, .flowtbl td { border:1.2px solid #aaa; border-collapse:collapse; }
      .flowtbl th, .flowtbl td { padding:14px; font-size:18px; }
      .flowtbl { width:100%; table-layout:fixed; background:#fff; margin-bottom:18px; }
      .flowtbl th { background:#F2F6FA; }
      .flowtbl td small { color:#666; }
      .flowtbl .step { font-weight:700; color:#226BB3; }
    </style>
    <table class="flowtbl">
      <thead>
        <tr>
          <th style="width:140px;">STEP</th>
          <th>内容</th>
          <th style="width:140px;">目安</th>
          <th style="width:260px;">提出物</th>
        </tr>
      </thead>
      <tbody>
    """
    for s in steps:
        html += f"""
        <tr>
          <td class="step" align="center">{s.get('step','')}</td>
          <td>{s.get('内容','')}</td>
          <td align="center">{s.get('目安','')}</td>
          <td>{s.get('提出物','')}</td>
        </tr>
        """
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)

def note_box(title: str, body: str):
    st.markdown(f"### {title}")
    st.markdown(body)

def tag_badge(text: str):
    st.markdown(
        f"""
        <span style="
            display:inline-block;
            padding:6px 10px;
            margin:0 8px 8px 0;
            border:1px solid #ddd;
            border-radius:999px;
            font-size:14px;
            background:#FCF9F0;">{text}</span>
        """,
        unsafe_allow_html=True
    )

def bullets(items):
    st.markdown("\n".join([f"- {x}" for x in items]))