# pages/3_PayPay.py
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="PayPay銀行｜住宅ローン", page_icon="🏦", layout="wide")

# ========== Styles ==========
st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 0.6rem;}
.big-link { font-size: 1.4rem; font-weight: bold; margin: 1rem 0; }
.table-wrap { overflow-x: auto; }
th, td { font-size: .98rem; }
</style>
""", unsafe_allow_html=True)

# ========== Paths ==========
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "paypay"

PDF_PREEXAM = ASSETS / "paypay事前審査.pdf"
PDF_DESC    = ASSETS / "商品説明.pdf"

def load_bytes(p: Path) -> bytes:
    try:
        return p.read_bytes()
    except Exception:
        st.error(f"ファイルが見つかりません: {p}")
        return b""

# ========== Title ==========
st.title("PayPay銀行｜住宅ローン")

# ① 提携住宅ローン｜事前審査
st.subheader("① 提携住宅ローン｜事前審査")
st.markdown(
    """
    <div class="big-link">
      👉 <a href="https://www.paypay-bank.co.jp/ad/mortgage/agency4.html" target="_blank">
      提携経由の事前審査はこちら（PayPay銀行 公式・提携ページ）
      </a>
    </div>
    <div>※ 弊社提携枠では、個人申込と <b>金利・頭金等の条件が異なる場合</b>があります。</div>
    """,
    unsafe_allow_html=True
)

# ② 個人で事前審査する場合（公式）
st.subheader("② 個人で事前審査する場合（公式）")
st.markdown(
    """
    <div class="big-link">
      👉 <a href="https://www.paypay-bank.co.jp/mortgage/index.html?utm_source=chatgpt.com" target="_blank">
      個人申込はこちら（PayPay銀行 住宅ローン 公式サイト）
      </a>
    </div>
    <div>※ 個人申込は提携条件の対象外です。条件・審査基準が異なる点にご注意ください。</div>
    """,
    unsafe_allow_html=True
)

# ③ 事前審査｜入力方法（PDF）＋ 基本必要書類
st.subheader("③ 事前審査｜入力方法（PDF）")
st.download_button(
    "📥 事前審査の入力方法（PDF）",
    data=load_bytes(PDF_PREEXAM),
    file_name="PayPay_事前審査_入力方法.pdf",
    mime="application/pdf"
)
st.markdown(
    """
    #### 基本必要書類（私に送ってください）
    - 源泉徴収票
    - 健康保険証（表・裏）
    """,
    unsafe_allow_html=True
)

# ④ 商品説明（PDF）
st.subheader("④ 商品説明（PDF）")
st.download_button(
    "📥 PayPay銀行｜商品説明（PDF）",
    data=load_bytes(PDF_DESC),
    file_name="PayPay_商品説明.pdf",
    mime="application/pdf"
)

# 強み／デメリット
st.subheader("強み／デメリット（横並び）")
st.markdown("""
<div class="table-wrap">
<table style="width:100%; border-collapse:collapse; background:#fff;">
  <thead>
    <tr style="background:#F3F4F6;">
      <th style="border:1px solid #d1d5db; padding:12px; width:50%;">強み</th>
      <th style="border:1px solid #d1d5db; padding:12px; width:50%;">デメリット</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="border:1px solid #d1d5db; padding:12px;">
        <ul>
          <li><b>業界初の連生団信</b>（じぶん銀行・みずほ・りそな・三井住友 なども対応）</li>
          <li>団信スペック充実（がん50%・がん100%・全疾病保証）</li>
          <li>失業保証・自然災害保証あり（+0.05%）</li>
          <li><b>審査金利・返済比率が緩く</b>借入額をストレッチ可能</li>
          <li><b>最長 50年</b> 借入可能（+0.1%）</li>
          <li>ソフトバンクユーザー金利割引</li>
          <li>転職後 <b>勤続半年</b>でも審査可（承認実例あり）</li>
        </ul>
      </td>
      <td style="border:1px solid #d1d5db; padding:12px;">
        <ul>
          <li>個人事業主には弱い</li>
          <li><b>125%・5年ルールなし</b></li>
          <li>リフォーム費用 融資不可</li>
          <li>物件担保評価が厳しい（借地権・既存不適格・自主管理はNG）</li>
        </ul>
      </td>
    </tr>
  </tbody>
</table>
</div>
""", unsafe_allow_html=True)

# 特殊項目
st.subheader("特殊項目")
st.markdown("""
<div class="table-wrap">
<table style="width:100%; border-collapse:collapse; background:#fff;">
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
</div>
""", unsafe_allow_html=True)