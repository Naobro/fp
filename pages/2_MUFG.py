# pages/2_MUFG.py
import streamlit as st
from pathlib import Path
from utils.rates import month_label, get_base_rates_for_current_month

st.set_page_config(page_title="三菱UFJ銀行｜住宅ローン", page_icon="🏦", layout="wide")

# 余白・バナーCSS（SBIページと同じ見た目）
st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 0.6rem;}
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

# ローカルPDFパス
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "mufg"
PDF_DESC   = ASSETS / "商品説明.pdf"
PDF_NOTICE = ASSETS / "入力時の注意点.pdf"

def load_bytes(p: Path) -> bytes:
    try:
        return p.read_bytes()
    except Exception:
        st.warning(f"ファイルが見つかりません：{p}")
        return b""

st.title("三菱UFJ銀行｜住宅ローン")

# ===== 今月の基準金利（最上段）=====
from pages.mortgageplan import load_manual_rates  # 共通の金利読込を利用

rates = load_manual_rates()
base = get_base_rates_for_current_month()

mufg_rate = rates.get("三菱UFJ銀行", base.get("三菱UFJ銀行"))

if mufg_rate is not None:
    st.markdown(
        f"""
        <div class="rate-banner">
          <div class="label">🗓 {month_label()} の基準金利（三菱UFJ銀行）</div>
          <div class="value">{float(mufg_rate):.3f}%</div>
          <div class="note">三大疾病団信など条件で加算</div>
        </div>
        """,
        unsafe_allow_html=True
    )
# ─ 商品説明（PDF 配布）
st.subheader("商品説明（PDF）")
st.download_button(
    "📥 三菱UFJ｜商品説明",
    data=load_bytes(PDF_DESC),
    file_name="三菱UFJ_商品説明.pdf",
    mime="application/pdf"
)

# ─ 事前審査（オンライン）
st.subheader("事前審査（オンライン）")
st.markdown("アクセスコードを **コピペ** して、下のボタン先で入力してください。")
st.code("w-mufg-hgshw001", language="text")
st.link_button(
    "🔗 事前審査ログイン（仲介向け）",
    "https://web.smart-entry-tab.jp/setWeb/estate/login/?realtor_cd=HGSHW-04384"
)

# ─ 入力時の注意点（テキストの追記＋PDF 配布）
st.subheader("入力時の注意点")
st.markdown(
    "担当者名：**西山 直樹**  /  メール：**naoki.nishiyama@terass.com**",
    unsafe_allow_html=True,
)
st.download_button(
    "📥 入力時の注意点（PDF）",
    data=load_bytes(PDF_NOTICE),
    file_name="三菱UFJ_入力時の注意点.pdf",
    mime="application/pdf"
)

# ─ 特殊項目（横長テーブル）
st.subheader("特殊項目")
st.markdown("""
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
      <td style="border:1px solid #aaa; padding:12px;">物件価格の <b>110%</b> まで</td>
    </tr>
    <tr>
      <td style="border:1px solid #aaa; padding:12px;">リフォーム</td>
      <td style="border:1px solid #aaa; padding:12px;" align="center">◯</td>
      <td style="border:1px solid #aaa; padding:12px;">2本扱い／本体と同金利</td>
    </tr>
    <tr>
      <td style="border:1px solid #aaa; padding:12px;">買い替え</td>
      <td style="border:1px solid #aaa; padding:12px;" align="center">◯</td>
      <td style="border:1px solid #aaa; padding:12px;">可能だが、<b>原則 返済比率に含めて計算</b></td>
    </tr>
  </tbody>
</table>
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
