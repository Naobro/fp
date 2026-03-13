import streamlit as st
from pathlib import Path
from utils.rates import get_base_rates_for_current_month, month_label

# =============================
# ページ設定（必ず一番最初）
# =============================
st.set_page_config(page_title="SBI新生銀行｜住宅ローン", page_icon="🏦", layout="wide")

st.markdown("<style>section[data-testid='stSidebar']{display:none;}</style>", unsafe_allow_html=True)

# 余白・テーブル体裁
st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 0.6rem;}
.table-wrap { overflow-x: auto; }
.sbi-table { 
  width: 100%; border-collapse: collapse; background: #fff;
  table-layout: fixed; min-width: 1100px;
}
.sbi-table th, .sbi-table td {
  line-height: 1.6;
  word-break: break-word;
  white-space: normal;
  vertical-align: top;
}
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

# パス
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "sbi"

# ローカルPDF
PDF_A3   = ASSETS / "A3_申込書.pdf"
PDF_PAIR = ASSETS / "ペアローン申込書.pdf"

def load_bytes(p: Path) -> bytes:
    try:
        return p.read_bytes()
    except Exception:
        st.warning(f"ファイルが見つかりません：{p}")
        return b""

# タイトル
st.title("SBI新生銀行｜住宅ローン 商品説明 & 事前審査")

# ===== 今月の基準金利（最上段）=====
from pages.mortgageplan import load_manual_rates

base_rates = get_base_rates_for_current_month()
manual = load_manual_rates()

sbi_rate = manual.get("SBI新生銀行", base_rates.get("SBI新生銀行"))
if sbi_rate is not None:
    st.markdown(
        f"""
        <div class="rate-banner">
          <div class="label">🗓 {month_label()} の基準金利（SBI新生銀行）</div>
          <div class="value">{float(sbi_rate):.3f}%</div>
          <div class="note">ガン団信　+0.1%</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ===== 住宅ローン WEB事前審査 =====
st.subheader("🌐 住宅ローン WEB事前審査")

# Web申込URL
WEB_APPLY_URL = "https://webform.sbishinseibank.co.jp/n/form/c/v1/bxfb/forms/-PbXSXrwkQPu-aRXpfz2W"

# GitHub画像URL
WEB_GUIDE_IMAGE_URL = "https://raw.githubusercontent.com/Naobro/fp/main/assets/sbi/sbiweb.jpg"

st.markdown("""
SBI新生銀行の事前審査は、**Web申込** に変更になりました。

**手順：**
1. 下のボタンから **Web事前審査フォーム** を開く  
2. 画面の案内に沿って必要事項を入力  
3. 申込完了後、必要書類を **私（西山）宛** に送付してください  
""")

# Web申込ボタン
st.markdown(
    f"""
    <div style="text-align:center; margin: 20px 0;">
      <a href="{WEB_APPLY_URL}" target="_blank" rel="noopener noreferrer"
         style="
           display:inline-block;
           background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
           color: white; padding: 16px 40px; border-radius: 25px;
           text-decoration: none; font-weight: 800; font-size: 1.1rem;
           box-shadow: 0 4px 12px rgba(30, 64, 175, 0.35);
         ">
        📝 SBI新生銀行 Web事前審査フォームを開く
      </a>
      <div style="margin-top: 8px; font-size: 0.9rem; color: #666;">
        ※新しいタブでSBI新生銀行の公式申込フォームが開きます
      </div>
    </div>
    """,
    unsafe_allow_html=True
)

# GitHub画像を表示
st.markdown("**📋 申込手順の詳細案内**")
try:
    st.image(WEB_GUIDE_IMAGE_URL, use_container_width=True, 
             caption="住宅ローンWEB事前審査のご案内")
except Exception:
    st.info("💡 申込案内画像は読み込み中です。上のボタンから直接お申込みください。")

# 必要書類（送り先を「私」に変更）
st.markdown("""
### 📎 Web申込完了後の必要書類

Webフォームでの入力が終わったら、以下の書類を **私（西山）宛** にお送りください：

- **本人確認書類**：運転免許証（表・裏）、マイナンバーカード等  
- **収入証明書類**：源泉徴収票、確定申告書 等  
- **健康保険証**：表・裏の両面  

**📲 送付方法（どちらでもOK）：**
- **LINE**：いつものLINEに画像で送付  
- **メール**：`naoki.nishiyama@terass.com` に添付して送付  

※ **物件資料は私が銀行に送りますので、お客様でのご用意・送付は不要です。**
""")

# ===== 強み =====
st.subheader("強み")
st.markdown("""
- 返済比率 一律40％（年収によらず）  
- 外国籍・転職者・旧耐震・住み替え（後売り）にも対応余地  
- 収入合算：合算者の最低年収を100万円へ引下げ（雇用形態不問で100％合算可）  
- 金消時金利（実行時適用）。金利上昇局面で有利  
- 審査金利3.0%で計算（35年返済なら年収約8.65倍目安）  
- 転職：勤続年数不問。オファーレター等の固定給・理論年収・目標設定ボーナスで審査可  
- 産育休：復職有無を問わず、休暇含まない年度の源泉票の額面100％で審査（長期は要相談）  
- 住み替え（後売り）：現自宅ローンは実行後売却完済でも返比に算入せず審査（条件あり）  
- 団信：最高保険金額を3億円まで引上げ（高額案件も相談可）  
- 永住権無：単身 or 夫婦のどちらかが永住権あれば可、連保は日本国籍/永住権者、日/英で対話可能であること
""")

# ===== デメリット =====
st.subheader("デメリット")
st.markdown("""
- **125%・5年ルールなし**  
- **団信が弱い（一般・がん100%のみ）**
""")

# ===== 特殊項目テーブル =====
st.subheader("特殊項目")
st.markdown("""
<div class="table-wrap">
<table class="sbi-table">
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
      <td style="border:1px solid #aaa; padding:12px;" align="center">◯</td>
      <td style="border:1px solid #aaa; padding:12px;">相談</td>
    </tr>
    <tr>
      <td style="border:1px solid #aaa; padding:12px;">買い替え</td>
      <td style="border:1px solid #aaa; padding:12px;" align="center">◯</td>
      <td style="border:1px solid #aaa; padding:12px;">
        現自宅の売買契約書の売却金額又は査定書記載の査定額が、現自宅の他行借入額の100%以上であれば、
        現自宅の住宅ローンを返済比率に含めずに審査可能。売却期限の設定はなく、実行後の売却エビデンスの提出も不要。
        ※1年間のみ、元金据え置きにて利息のみ返済いただきます。1年経過後から通常の月々返済へ切り替わる。
      </td>
    </tr>
  </tbody>
</table>
</div>
""", unsafe_allow_html=True)

st.caption("※本ページの数値は社内目安。正式情報は銀行公表値をご確認ください。")
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
