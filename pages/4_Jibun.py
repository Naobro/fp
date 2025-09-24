# pages/4_Jibun.py
import streamlit as st
from pathlib import Path

# 金利関連の関数を正しくインポート
from utils.rates import month_label, get_base_rates_for_current_month
from pages.住宅ローン提案 import load_manual_rates

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
          <div class="note">団信オプションなど条件で加算</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ========== 事前審査リンク ==========
st.subheader("提携住宅ローン｜事前審査")
st.markdown(
    """
    <div class="big-link">
      👉 <a href="https://pitch.com/v/web-xtdvtr" target="_blank">
      事前審査の入力方法はこちら（Pitch資料）
      </a>
    </div>
    <div>
      <b>諸費用まで借入可能・金利優遇あり</b> など、公式サイトからの個人申込よりも有利な条件でご利用いただけます。
    </div>
    """,
    unsafe_allow_html=True
)

# ========== 強み／デメリット ==========
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
          <li><b>KDDI・三菱UFJの共同出資</b>で安心感</li>
          <li>がん50％・がん100％・7大疾病など団信オプション充実</li>
          <li><b>最長50年</b> の超長期ローンが可能（+0.1%）</li>
          <li>ネット銀行ならではの低金利水準</li>
          <li>一部繰上返済手数料無料</li>
        </ul>
      </td>
      <td style="border:1px solid #d1d5db; padding:12px; vertical-align: top;">
        <ul>
          <li>リフォーム費用の融資は原則不可</li>
          <li><b>125%・5年ルールなし</b></li>
          <li>物件評価が厳しめ（担保余力を重視）</li>
          <li>個人事業主にはやや厳しい傾向</li>
        </ul>
      </td>
    </tr>
  </tbody>
</table>
</div>
""", unsafe_allow_html=True)

# ========== 特殊項目 ==========
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
      <td style="border:1px solid #aaa; padding:12px;">原則不可</td>
    </tr>
    <tr>
      <td style="border:1px solid #aaa; padding:12px;">買い替え</td>
      <td style="border:1px solid #aaa; padding:12px;" align="center">◯</td>
      <td style="border:1px solid #aaa; padding:12px;">ダブルローンは原則不可。売却完了を前提とする。</td>
    </tr>
  </tbody>
</table>
</div>
""", unsafe_allow_html=True)

st.caption("※本ページの数値は案内用です。正式条件は銀行公表資料をご確認ください。")
