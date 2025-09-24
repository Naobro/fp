# pages/5_SumishinSBI.py
import streamlit as st
from utils.rates import month_label, get_base_rates_for_current_month
from pages.住宅ローン提案 import load_manual_rates

st.set_page_config(page_title="住信SBIネット銀行｜住宅ローン", page_icon="🏦", layout="wide")

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
st.title("住信SBIネット銀行｜住宅ローン")

# ===== 今月の基準金利（最上段）=====
rates = load_manual_rates()
base = get_base_rates_for_current_month()

sbi_rate = rates.get("住信SBIネット銀行", base.get("住信SBIネット銀行"))

if sbi_rate is not None:
    base_rate = float(sbi_rate)
    rate_gan50 = base_rate + 0.10
    rate_gan100 = base_rate + 0.20

    st.markdown(
        f"""
        <div class="rate-banner">
          <div class="label">🗓 {month_label()} の基準金利（住信SBIネット銀行）</div>
          <div class="value">{base_rate:.3f}%</div>
          <div class="note">一般団信</div>
        </div>
        <div class="rate-banner">
          <div class="label">がん50% 団信</div>
          <div class="value">{rate_gan50:.3f}%</div>
          <div class="note">+0.10% 加算</div>
        </div>
        <div class="rate-banner">
          <div class="label">がん100% 団信</div>
          <div class="value">{rate_gan100:.3f}%</div>
          <div class="note">+0.20% 加算</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ========== 特徴 ==========
st.subheader("特徴")
st.markdown("""
- 事務手数料は借入額×2.2%  
- がん50%団信、がん100%団信を選択可能（それぞれ金利上乗せあり）  
- **全疾病保障＋三大疾病50%が標準付帯**  
- LTVに応じた金利帯（80％以下で優遇 等）  
- 125%ルールなし（繰上・借換の説明が楽）  
- 外国籍・転職後1年未満でも審査事例あり  
- 審査スピードが比較的早い  
""")

# ========== 入力方法リンク ==========
st.subheader("③ 事前審査｜入力方法")
st.markdown(
    """
    <div class="big-link">
      👉 <a href="https://www.netbk.co.jp/contents/lp/homeloan/" target="_blank">
      住信SBIネット銀行 住宅ローン 公式サイト（事前審査）
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
          <li>金利が業界最低水準</li>
          <li>ネット完結型でスピーディ</li>
          <li>全疾病保障＋三大疾病50%が標準付帯</li>
          <li>LTVに応じた金利優遇で提案しやすい</li>
        </ul>
      </td>
      <td style="border:1px solid #d1d5db; padding:12px; vertical-align: top;">
        <ul>
          <li>事務手数料が高額（借入額×2.2%）</li>
          <li>がん団信は金利上乗せ（50%:+0.10%, 100%:+0.20%）</li>
          <li>特殊案件（自主管理, 借地権等）はNG</li>
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
      <td style="border:1px solid #aaa; padding:12px;" align="center">×</td>
      <td style="border:1px solid #aaa; padding:12px;">諸費用借入は不可</td>
    </tr>
    <tr>
      <td style="border:1px solid #aaa; padding:12px;">リフォーム</td>
      <td style="border:1px solid #aaa; padding:12px;" align="center">×</td>
      <td style="border:1px solid #aaa; padding:12px;">リフォーム費用融資不可</td>
    </tr>
    <tr>
      <td style="border:1px solid #aaa; padding:12px;">買い替え</td>
      <td style="border:1px solid #aaa; padding:12px;" align="center">△</td>
      <td style="border:1px solid #aaa; padding:12px;">売却前提で審査可能だが制約あり</td>
    </tr>
  </tbody>
</table>
</div>
""", unsafe_allow_html=True)

st.caption("※本ページは案内用ダイジェスト。正式条件は銀行公表資料をご確認ください。")
