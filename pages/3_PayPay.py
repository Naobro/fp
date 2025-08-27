# pages/3_PayPay.py
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="PayPay銀行｜住宅ローン", page_icon="🏦", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 0.6rem;}
.big-link {
    font-size: 1.4rem;
    font-weight: bold;
    margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "paypay"

PDF_DESC = ASSETS / "商品説明.pdf"

def load_bytes(p: Path) -> bytes:
    try:
        return p.read_bytes()
    except Exception:
        st.error(f"ファイルが見つかりません: {p}")
        return b""

st.title("PayPay銀行｜住宅ローン")

# ─ 商品説明
st.subheader("商品説明（PDF）")
st.download_button(
    "📥 PayPay銀行｜商品説明",
    data=load_bytes(PDF_DESC),
    file_name="PayPay_商品説明.pdf",
    mime="application/pdf"
)

# ─ 事前審査
st.subheader("事前審査　入力方法")
st.markdown(
    """
    <div class="big-link">
        👉 <a href="https://www.paypay-bank.co.jp/ad/mortgage/agency4.html" target="_blank">
        事前審査はこちら（PayPay銀行公式ページ）
        </a>
    </div>
    """,
    unsafe_allow_html=True
)

# ─ 特殊項目（横長テーブル）
st.subheader("特殊項目")
st.markdown("""
<table class="sbi-table" style="width:100%; border-collapse:collapse; background:#fff;">
  <thead>
    <tr style="background:#FCF9F0;">
      <th style="border:1px solid #aaa; padding:12px; width:22%;">項目</th>
      <th style="border:1px solid #aaa; padding:12px; width:10%;">取扱</th>
      <th style="border:1px solid #aaa; padding:12px;">備考</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="border:1px solid #aaa; padding:12px;">諸費用</td>
      <td style="border:1px solid #aaa; padding:12px;" align="center">◯</td>
      <td style="border:1px solid #aaa; padding:12px;">相談</td>
    </tr>
    <tr>
      <td style="border:1px solid #aaa; padding:12px;">リフォーム</td>
      <td style="border:1px solid #aaa; padding:12px;" align="center">❎</td>
      <td style="border:1px solid #aaa; padding:12px;">相談</td>
    </tr>
    <tr>
      <td style="border:1px solid #aaa; padding:12px;">買い替え</td>
      <td style="border:1px solid #aaa; padding:12px;" align="center">◯</td>
      <td style="border:1px solid #aaa; padding:12px;">
        ダブルローン不可、融資実行後（決済後）1か月以内に完済
      </td>
    </tr>
  </tbody>
</table>
""", unsafe_allow_html=True)