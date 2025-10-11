# pages/4_Jibun.py
import streamlit as st
from pathlib import Path
from utils.rates import month_label, get_base_rates_for_current_month
from pages.mortgageplan import load_manual_rates

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
      <td style="border:1px solid #aaa; padding:12px;" align="center">×</td>
      <td style="border:1px solid #aaa; padding:12px;">リフォーム費用NG</td>
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
# ===== 公式LINEバナー（×で閉じられる・PC/スマホ両対応）=====
import urllib.parse as _url

def render_line_banner():
    # 1) セッションフラグ初期化
    if "line_banner_closed" not in st.session_state:
        st.session_state.line_banner_closed = False

    # 2) ?close_banner=1 を検知して閉じる
    try:
        qp = st.query_params
        close_flag = str(qp.get("close_banner", "0")) == "1"
        qp_dict = dict(qp)  # 既存のクエリ保持用
    except Exception:
        qp = st.experimental_get_query_params()
        close_flag = (qp.get("close_banner", ["0"])[0] == "1")
        qp_dict = {k: (v[0] if isinstance(v, list) else v) for k, v in qp.items()}

    if close_flag:
        st.session_state.line_banner_closed = True

    if st.session_state.line_banner_closed:
        return  # 以降レンダしない

    # 3) × クリック時のURL（既存クエリを保持して close_banner=1 だけ付与）
    qp_dict = {k: (v if not isinstance(v, list) else v[0]) for k, v in qp_dict.items()}
    qp_dict["close_banner"] = "1"
    qs = _url.urlencode(qp_dict)
    close_url = "?" + qs if qs else "?close_banner=1"

    # 4) バナー描画（×はリンク。JS不要）
    st.markdown(f"""
    <style>
    .line-banner-wrap {{
      position: fixed;
      bottom: 100px; right: 18px; z-index: 9999;
    }}
    .line-banner {{
      background: #06C755; color: #fff;
      padding: 14px 18px 20px; border-radius: 12px;
      box-shadow: 0 4px 10px rgba(0,0,0,0.25);
      font-size: 15px; text-align: center; position: relative;
    }}
    .line-banner:hover {{ transform: scale(1.02); background:#05b34d; }}
    .line-banner .ttl {{ font-size: 17px; font-weight: 800; line-height: 1.4; }}
    .line-banner .id  {{ font-size: 20px; font-weight: 900; margin: 6px 0 6px; }}
    .line-banner img  {{
      width: 130px; display:block; margin: 8px auto 10px;
      border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.3);
      background:#fff;
    }}
    .line-banner .cta {{ display:inline-block; font-weight: 800; text-decoration: underline; color:#fff; }}
    .line-banner .close-btn {{
      position:absolute; top:6px; right:10px; width:24px; height:24px;
      border-radius:50%; background: rgba(0,0,0,0.25);
      color:#fff; text-align:center; line-height:24px;
      font-size:16px; font-weight:700; text-decoration:none;
    }}
    .line-banner .close-btn:hover {{ background: rgba(0,0,0,0.4); }}
    @media (max-width: 768px){{
      .line-banner-wrap {{ bottom: 100px; right: 14px; }}
      .line-banner {{ padding: 12px 14px 18px; }}
      .line-banner img {{ width: 110px; }}
      .line-banner .id {{ font-size: 18px; }}
    }}
    </style>

    <div class="line-banner-wrap" id="line-banner">
      <div class="line-banner" role="region" aria-label="LINE公式バナー">
        <a class="close-btn" href="{close_url}" aria-label="バナーを閉じる">×</a>
        <a href="https://lin.ee/m40HEqN" target="_blank" rel="noopener" style="text-decoration:none; color:#fff;">
          <div class="ttl">📲 シミュレーション利用は<br>LINEで簡単・不動産相談</div>
          <div class="id">LINE ID：@fudo3</div>
          <img src="https://qr-official.line.me/gs/M_277qthwd_GW.png?oat_content=qr" alt="LINE公式QRコード">
          <span class="cta">▶ 公式LINEで相談する</span>
        </a>
      </div>
    </div>
    """, unsafe_allow_html=True)

# どこかで呼び出す（各ページの末尾など）
render_line_banner()
