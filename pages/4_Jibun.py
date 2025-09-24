# pages/4_Jibun.py
import streamlit as st
from pathlib import Path
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
    base_rate = float(jibun_rate)
    rate_gan100 = base_rate + 0.054
    rate_premium = base_rate + 0.154

    st.markdown(
        f"""
        <div class="rate-banner">
          <div class="label">🗓 {month_label()} の基準金利（じぶん銀行）</div>
          <div class="value">{base_rate:.3f}%</div>
          <div class="note">一般団信</div>
        </div>
        <div class="rate-banner">
          <div class="label">がん100% 団信</div>
          <div class="value">{rate_gan100:.3f}%</div>
          <div class="note">+0.054% 加算</div>
        </div>
        <div class="rate-banner">
          <div class="label">プレミアム団信</div>
          <div class="value">{rate_premium:.3f}%</div>
          <div class="note">+0.154% 加算</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ========== 特徴 ==========
st.subheader("特徴")
st.markdown("""
■金利優遇割は以下の4種類から組み合わせ自由です■  
(1) モバイル割 ▲0.07%  
(2) でんき割 ▲0.03%  
(3) ネット割 ▲0.03% ※戸建てのみ適用可  
(4) TV割 ▲0.02% ※戸建てのみ適用可  

👉 詳細は [auじぶん銀行公式サイト](https://www.jibunbank.co.jp/products/homeloan/customer/) をご確認ください。  

■大きな特徴3つ■  
① 諸費用も物件価格の10%まで可能！  
② 最大借入期間50年での申込が可能！  
※借入期間を35年超～50年とした場合は金利が0.1%上乗せとなります。  
③ 審査期間も借入期間に含まれるため借入上限金額が伸びます。  
""")

# ========== 入力方法リンク ==========
st.subheader("③ 事前審査｜入力方法")
st.markdown(
    """
    <div class="big-link">
      👉 <a href="https://pitch.com/v/web-xtdvtr" target="_blank">
      じぶん銀行 事前審査 入力方法はこちら
      </a>
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
          <li>団信プランが充実（がん100%, プレミアム団信）</li>
          <li>金利優遇割（最大 ▲0.15%）が使える</li>
          <li>最長50年借入可能</li>
          <li>諸費用も借入対象（物件価格の10%まで）</li>
        </ul>
      </td>
      <td style="border:1px solid #d1d5db; padding:12px; vertical-align: top;">
        <ul>
          <li>借入期間35年超は金利+0.1%</li>
          <li>優遇割の一部は戸建て限定（ネット割・TV割）</li>
          <li>個人事業主への対応は限定的</li>
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
      <td style="border:1px solid #aaa; padding:12px;">物件価格の10%まで借入可能</td>
    </tr>
    <tr>
      <td style="border:1px solid #aaa; padding:12px;">リフォーム</td>
      <td style="border:1px solid #aaa; padding:12px;" align="center">△</td>
      <td style="border:1px solid #aaa; padding:12px;">個別相談（別途条件あり）</td>
    </tr>
    <tr>
      <td style="border:1px solid #aaa; padding:12px;">買い替え</td>
      <td style="border:1px solid #aaa; padding:12px;" align="center">◯</td>
      <td style="border:1px solid #aaa; padding:12px;">現自宅ローンを含めた返済比率で審査</td>
    </tr>
  </tbody>
</table>
</div>
""", unsafe_allow_html=True)

st.caption("※本ページは案内用ダイジェスト。正式条件は銀行公表資料をご確認ください。")
