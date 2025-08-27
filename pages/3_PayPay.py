# pages/3_PayPay.py
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="PayPay銀行｜住宅ローン", page_icon="🏦", layout="wide")

# ========== Styles ==========
st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 0.6rem;}
.big-link {
    font-size: 1.4rem;
    font-weight: bold;
    margin: 1rem 0;
}
.section-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 16px 18px;
    margin-bottom: 14px;
}
h2, h3 { margin-top: .4rem; }
ul { margin: 0.4rem 0 0.2rem 1.2rem; }
li { line-height: 1.6; }
.table-wrap { overflow-x: auto; }
th, td { font-size: .98rem; }
</style>
""", unsafe_allow_html=True)

# ========== Paths ==========
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "paypay"

# ③で配布するPDF（事前審査の入力方法）
PDF_PREEXAM = ASSETS / "paypay事前審査.pdf"     # 例: assets/paypay/paypay事前審査.pdf を配置
# ④で配布するPDF（商品説明）
PDF_DESC    = ASSETS / "商品説明.pdf"           # 例: assets/paypay/商品説明.pdf を配置

def load_bytes(p: Path) -> bytes:
    try:
        return p.read_bytes()
    except Exception:
        st.error(f"ファイルが見つかりません: {p}")
        return b""

# ========== Page Title ==========
st.title("PayPay銀行｜住宅ローン")

# ========== ① 提携住宅ローン｜事前審査 ==========
with st.container():
    st.subheader("① 提携住宅ローン｜事前審査")
    st.markdown(
        """
        <div class="section-card">
          <div class="big-link">
            👉 <a href="https://www.paypay-bank.co.jp/ad/mortgage/agency4.html" target="_blank">
            提携経由の事前審査はこちら（PayPay銀行 公式・提携ページ）
            </a>
          </div>
          <div>※ 弊社提携枠では、個人申込と <b>金利・頭金等の条件が異なる場合</b>があります。</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ========== ② 個人で事前審査する場合（公式） ==========
with st.container():
    st.subheader("② 個人で事前審査する場合（公式）")
    st.markdown(
        """
        <div class="section-card">
          <div class="big-link">
            👉 <a href="https://www.paypay-bank.co.jp/mortgage/index.html?utm_source=chatgpt.com" target="_blank">
            個人申込はこちら（PayPay銀行 住宅ローン 公式サイト）
            </a>
          </div>
          <div>※ 個人申込は提携条件の対象外です。条件・審査基準が異なる点にご注意ください。</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ========== ③ 事前審査 入力方法（PDF配布） ==========
with st.container():
    st.subheader("③ 事前審査｜入力方法（PDF）")
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.download_button(
        "📥 事前審査の入力方法（PDF）",
        data=load_bytes(PDF_PREEXAM),
        file_name="PayPay_事前審査_入力方法.pdf",
        mime="application/pdf"
    )
    st.markdown('</div>', unsafe_allow_html=True)

# ========== ④ 商品説明（PDF配布） ==========
with st.container():
    st.subheader("④ 商品説明（PDF）")
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.download_button(
        "📥 PayPay銀行｜商品説明（PDF）",
        data=load_bytes(PDF_DESC),
        file_name="PayPay_商品説明.pdf",
        mime="application/pdf"
    )
    st.markdown('</div>', unsafe_allow_html=True)

# ========== 強み・デメリット（横長テーブル） ==========
st.subheader("強み／デメリット（要点まとめ｜横並び）")
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
          <li><b>業界初の連生団信</b>（他行：じぶん銀行・みずほ・りそな・三井住友 など）</li>
          <li>団信スペック充実（がん50%・がん100%・全疾病保証）</li>
          <li>失業保証・自然災害保証など <b>保証も充実（+0.05%）</b></li>
          <li><b>審査金利・返済比率が他行より緩め</b>で、借入額をストレッチしやすい</li>
          <li><b>最長 50年</b> まで借入可能（+0.1%）</li>
          <li>ソフトバンクユーザー <b>金利割引</b>あり</li>
          <li>転職後 <b>勤続半年</b>でも審査可（承認・実行の実例あり）</li>
        </ul>
      </td>
      <td style="border:1px solid #d1d5db; padding:12px;">
        <ul>
          <li><b>個人事業主</b>には相対的に弱い傾向</li>
          <li><b>125%・5年ルールなし</b></li>
          <li><b>リフォーム費用 融資不可</b></li>
          <li>物件担保評価が厳しめ（<b>借地権・既存不適格・自主管理</b>などはNG）</li>
        </ul>
      </td>
    </tr>
  </tbody>
</table>
</div>
<small>※ 上記は社内取扱いの要点整理です。詳細条件・最新仕様は必ず公式資料をご確認ください。</small>
""", unsafe_allow_html=True)

# ========== 既存の「特殊項目」テーブル ==========
st.subheader("特殊項目")
st.markdown("""
<div class="table-wrap">
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
        ダブルローン不可、融資実行後（決済後）1か月以内に完済（返済比率内なら可能）
      </td>
    </tr>
  </tbody>
</table>
</div>
""", unsafe_allow_html=True)