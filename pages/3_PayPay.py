# pages/3_PayPay.py
import streamlit as st
from pathlib import Path
from utils.rates import get_base_rates_for_current_month, month_label  # ← 追加

st.set_page_config(page_title="PayPay銀行｜住宅ローン", page_icon="🏦", layout="wide")

# ========== Styles ==========
st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 0.6rem;}
.big-link { font-size: 1.4rem; font-weight: bold; margin: 1rem 0; }
.table-wrap { overflow-x: auto; }
th, td { font-size: .98rem; }

/* 追加：今月の基準金利バナー */
.rate-banner {
  display: flex; flex-direction: column; gap: 6px;
  border: 1px solid #e5e7eb; border-radius: 12px;
  background: #fff; padding: 14px 16px; margin: 4px 0 14px 0;
}
.rate-banner .label { font-size: 1.0rem; color: #374151; }
.rate-banner .value { font-size: 2.2rem; font-weight: 800; color: #1b232a; line-height: 1.1; }
.rate-banner .note { font-size: 0.95rem; color: #4b5563; }
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

# ========== 追加：ページ最上段に今月の基準金利（PayPay銀行） ==========
_base = get_base_rates_for_current_month()              # 今月の%を取得（utils/rates.py）
paypay_rate = _base.get("PayPay銀行", None)             # PayPay銀行の当月レート（%）
if paypay_rate is not None:
    st.markdown(
        f"""
        <div class="rate-banner">
          <div class="label">🗓 {month_label()} の基準金利（PayPay銀行）</div>
          <div class="value">{paypay_rate:.3f}%</div>
          <div class="note">がん団信など金利上乗せ</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# 提携住宅ローン｜事前審査
st.subheader("提携住宅ローン｜事前審査")
st.markdown(
    """
    <div class="big-link">
      👉 <a href="https://www.paypay-bank.co.jp/ad/mortgage/agency4.html" target="_blank">
      提携の事前審査はこちら（西山 経由）
      </a>
    </div>
    <div>
      <b>諸費用まで借入可能・金利優遇あり</b> など、公式サイトからの個人申込よりも有利な条件でご利用いただけます。
    </div>
    """,
    unsafe_allow_html=True
)

# 個人で事前審査する場合（公式）
st.subheader("個人で事前審査する場合（公式）")
st.markdown(
    """
    <div style="margin-top:1rem; font-weight:bold;">
      【参考】個人で直接申込する場合の条件
    </div>
    <div class="big-link">
      👉 <a href="https://www.paypay-bank.co.jp/mortgage/index.html?utm_source=chatgpt.com" target="_blank">
      PayPay銀行 住宅ローン公式サイト
      </a>
    </div>
    <div>
      ※ こちらからの申込は <b>弊社提携の優遇条件（諸費用借入・金利引下げ等）が一切適用されません</b>。<br>
      条件面では弊社経由でのお申込が有利です。
    </div>
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
      <td style="border:1px solid #d1d5db; padding:12px; vertical-align: top;">
        <ul>
          <li>個人事業主には弱い（弁護士・医師などOK）</li>
          <li><b>125%・5年ルールなし</b></li>
          <li>リフォーム費用 融資不可</li>
          <li>物件担保評価が厳しい（借地権・既存不適格・自主管理などはNG）</li>
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