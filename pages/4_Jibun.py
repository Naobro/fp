import streamlit as st
from pathlib import Path
from utils.rates import month_label
from pages.住宅ローン提案 import load_manual_rates, get_base_rates_for_current_month

st.set_page_config(page_title="じぶん銀行｜住宅ローン", page_icon="🏦", layout="wide")

# ========== Styles ==========
st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 0.6rem;}
.big-link { font-size: 1.4rem; font-weight: bold; margin: 1rem 0; }
.table-wrap { overflow-x: auto; }
th, td { font-size: .98rem; }

/* 今月の基準金利バナー */
.rate-banner {
  display: flex; flex-direction: column; gap: 6px;
  border: 1px solid #e5e7eb; border-radius: 12px;
  background: #fff; padding: 14px 16px; margin: 4px 0 14px 0;
}
.rate-banner .label { font-size: 1.0rem; color: #374151; }
.rate-banner .value { font-size: 2.2rem; font-weight: 800; color: #1b232a; line-height: 1.1; }
.rate-banner .note  { font-size: 0.95rem; color: #4b5563; }
</style>
""", unsafe_allow_html=True)

# ========== Paths ==========
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "jibun"

PDF_DESC = ASSETS / "商品説明.pdf"

def load_bytes(p: Path) -> bytes:
    try:
        return p.read_bytes()
    except Exception:
        st.error(f"ファイルが見つかりません: {p}")
        return b""

# ========== Title ==========
st.title("じぶん銀行｜住宅ローン")

# ===== 今月の基準金利（最上段）=====
rates = load_manual_rates()
base = get_base_rates_for_current_month()

jibun_rate = rates.get("じぶん銀行", base.get("じぶん銀行"))

if jibun_rate is not None:
    st.markdown(
        f"""
        <div class="rate-banner">
          <div class="label">🗓 {month_label()} の基準金利（じぶん銀行）</div>
          <div class="value">{float(jibun_rate):.3f}%</div>
          <div class="note">がん団信・7大疾病団信など条件で加算</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ① 事前審査｜入力方法（外部リンク）
st.subheader("① 事前審査｜入力方法")
st.markdown(
    """
    <div class="big-link">
      👉 <a href="https://pitch.com/v/web-xtdvtr" target="_blank">
      Pitch｜入力方法ページ
      </a>
    </div>
    """,
    unsafe_allow_html=True
)

# ② 商品説明（PDF）
st.subheader("② 商品説明（PDF）")
st.download_button(
    "📥 じぶん銀行｜商品説明（PDF）",
    data=load_bytes(PDF_DESC),
    file_name="じぶん銀行_商品説明.pdf",
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
          <li>KDDI・三菱UFJが出資するネット銀行</li>
          <li>団信ラインナップ充実（がん100・7大疾病・全疾病）</li>
          <li>ペアローン・収入合算対応可</li>
          <li>審査が比較的柔軟</li>
          <li><b>最長50年借入</b>（36年以上は+0.1%）</li>
        </ul>
      </td>
      <td style="border:1px solid #d1d5db; padding:12px; vertical-align: top;">
        <ul>
          <li><b>125%・5年ルールなし</b></li>
          <li>諸費用借入は限定的</li>
          <li>リフォーム費用は融資対象外</li>
          <li>担保評価に厳しい物件は不可</li>
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
      <td style="border:1px solid #aaa; padding:12px;" align="center">△</td>
      <td style="border:1px solid #aaa; padding:12px;">一部のみ対象</td>
    </tr>
    <tr>
      <td style="border:1px solid #aaa; padding:12px;">リフォーム</td>
      <td style="border:1px solid #aaa; padding:12px;" align="center">❎</td>
      <td style="border:1px solid #aaa; padding:12px;">対象外</td>
    </tr>
    <tr>
      <td style="border:1px solid #aaa; padding:12px;">買い替え</td>
      <td style="border:1px solid #aaa; padding:12px;" align="center">◯</td>
      <td style="border:1px solid #aaa; padding:12px;">審査次第でダブルローン可</td>
    </tr>
  </tbody>
</table>
</div>
""", unsafe_allow_html=True)
