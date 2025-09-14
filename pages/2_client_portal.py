# fp/client_portal.py
# 顧客ポータル（表紙）：?client=<ID> を受けて各機能ページへ誘導するだけ

import json
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Client Portal", layout="centered")

# ========== パラメタ ==========
client_id = st.query_params.get("client", [""])[0] if hasattr(st, "query_params") else st.experimental_get_query_params().get("client", [""])[0]
if not client_id:
    st.error("client パラメータがありません。例： /client_portal?client=c-xxxxx")
    st.stop()

BASE = Path(__file__).resolve().parent
DATA_DIR = (BASE / "data" / "clients" / client_id).resolve()

meta_path = DATA_DIR / "meta.json"
display_name = ""
property_label = ""  # 物件名は“未決定”想定なので、表紙では使わない
spreadsheet_url = None
line_qr_url = None

# ========== meta 読み込み（なければ最低限の案内のみ） ==========
if meta_path.exists():
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        display_name = meta.get("display_name") or meta.get("customer_name") or ""
        spreadsheet_url = meta.get("spreadsheet_url") or None
        line_qr_url = meta.get("line_qr_url") or None
    except Exception:
        pass

# ========== ヘッダー（超シンプル） ==========
st.markdown("### お客様ポータル")
st.write(f"ID：`{client_id}`")
if display_name:
    st.write(f"お客様名：**{display_name}**")
st.write("このページから各コンテンツへ移動できます。")

st.divider()

# ========== 機能リンク ==========
def link(label: str, page_path: str):
    st.link_button(label, f"{page_path}?client={client_id}", use_container_width=True)

st.subheader("メニュー")
link("📄 住宅ローン提案（PDF）", "/pages/住宅ローン提案")
link("🧾 諸費用明細（PDF）", "/pages/諸費用明細")
link("✅ 必要書類チェックリスト（PDF）", "/pages/checklists")
link("📝 事前審査入力（ヒアリング）", "/pages/hearing")

st.divider()

# ========== 任意の外部リンク ==========
if spreadsheet_url:
    st.markdown("#### 共有スプレッドシート")
    st.link_button("📊 スプレッドシートを開く", spreadsheet_url, use_container_width=True)

if line_qr_url:
    st.markdown("#### 連絡（LINE）")
    st.image(line_qr_url, caption="LINE QR（既に交換済みなら表示不要）", use_column_width=True)

# 余白
st.write("")
