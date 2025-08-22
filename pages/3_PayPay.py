# pages/3_PayPay.py
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="PayPay銀行｜住宅ローン", page_icon="🏦", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 0.6rem;}
</style>
""", unsafe_allow_html=True)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "paypay"

PDF_DESC = ASSETS / "商品説明.pdf"

def load_bytes(p: Path) -> bytes:
    return p.read_bytes()

st.title("PayPay銀行｜住宅ローン")

st.subheader("商品説明（PDF）")
st.download_button("📥 PayPay銀行｜商品説明", data=load_bytes(PDF_DESC), file_name="PayPay_商品説明.pdf", mime="application/pdf")

st.subheader("事前審査フロー（要点）")
st.markdown("""
<table style="width:100%; border-collapse:collapse; background:#fff;">
  <thead>
    <tr style="background:#F2F6FA;">
      <th style="border:1px solid #aaa; padding:12px; width:140px;">STEP</th>
      <th style="border:1px solid #aaa; padding:12px;">内容</th>
      <th style="border:1px solid #aaa; padding:12px; width:140px;">目安</th>
      <th style="border:1px solid #aaa; padding:12px; width:260px;">提出物</th>
    </tr>
  </thead>
  <tbody>
    <tr><td style="border:1px solid #aaa; padding:12px;" align="center">1</td><td style="border:1px solid #aaa; padding:12px;">ヒアリング</td><td style="border:1px solid #aaa; padding:12px;" align="center">15–30分</td><td style="border:1px solid #aaa; padding:12px;">本人確認</td></tr>
    <tr><td style="border:1px solid #aaa; padding:12px;" align="center">2</td><td style="border:1px solid #aaa; padding:12px;">必要書類収集</td><td style="border:1px固" align="center">当日〜3日</td><td style="border:1px solid #aaa; padding:12px;">年収書類 等</td></tr>
    <tr><td style="border:1px solid #aaa; padding:12px;" align="center">3</td><td style="border:1px solid #aaa; padding:12px;">申込（オンライン/紙）</td><td style="border:1px solid #aaa; padding:12px;" align="center">15–20分</td><td style="border:1px solid #aaa; padding:12px;">申込フォーム</td></tr>
    <tr><td style="border:1px solid #aaa; padding:12px;" align="center">4</td><td style="border:1px solid #aaa; padding:12px;">審査</td><td style="border:1px solid #aaa; padding:12px;" align="center">1–3営業日</td><td style="border:1px solid #aaa; padding:12px;">随時対応</td></tr>
    <tr><td style="border:1px solid #aaa; padding:12px;" align="center">5</td><td style="border:1px solid #aaa; padding:12px;">結果共有</td><td style="border:1px solid #aaa; padding:12px;" align="center">即日</td><td style="border:1px solid #aaa; padding:12px;">—</td></tr>
  </tbody>
</table>
""", unsafe_allow_html=True)

st.caption("※本ページの数値・条件は社内目安。正式情報は銀行公表値をご確認ください。")