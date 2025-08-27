# pages/1_SBI_Shinssei.py
import streamlit as st
from pathlib import Path
from utils.rates import get_base_rates_for_current_month, month_label  # 共通レート

st.set_page_config(page_title="SBI新生銀行｜住宅ローン", page_icon="🏦", layout="wide")

# 余白・テーブル体裁
st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 0.6rem;}
.sbi-table th, .sbi-table td {
  line-height: 1.6;
  word-break: break-word;
  white-space: normal;
  vertical-align: top;
}
/* 今月の基準金利バナー（PayPayページ準拠） */
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

# ===== 今月の金利（最上段）=====
_base = get_base_rates_for_current_month()
sbi_rate = _base.get("SBI新生銀行", None)  # 当月の%（utils/rates.py由来）
if sbi_rate is not None:
    st.markdown(
        f"""
        <div class="rate-banner">
          <div class="label">🗓 {month_label()} の基準金利（SBI新生銀行）</div>
          <div class="value">{sbi_rate:.3f}%</div>
          <div class="note">今月はこれです</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ===== 事前審査用紙（今月の金利の直下へ移動）=====
st.subheader("事前審査用紙（ダウンロード）")
st.markdown("""
事前審査は **紙面での記入** になります。  
**下記よりダウンロード** をお願いします。  

- **単独**：A3 申込書のみ  
- **ペアローン**：A3 申込書 **＋** ペアローン申込書 の両方が必要

合わせて、**源泉徴収票・運転免許証（表裏）・健康保険証（表裏）** を **私に送ってください**。
""")

col1, col2 = st.columns(2)
with col1:
    st.download_button(
        "📥 A3 申込書",
        data=load_bytes(PDF_A3),
        file_name="SBI_A3_申込書.pdf",
        mime="application/pdf"
    )
with col2:
    st.download_button(
        "📥 ペアローン申込書",
        data=load_bytes(PDF_PAIR),
        file_name="SBI_ペアローン申込書.pdf",
        mime="application/pdf"
    )

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

# ===== デメリット（指定どおり）=====
st.subheader("デメリット")
st.markdown("""
- **125%・5年ルールなし**  
- **団信が弱い（一般・がん100%のみ）**
""")

# ─ 特殊項目（横長テーブル）
st.subheader("特殊項目")
st.markdown("""
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
      <td style="border:1px solid #aaa; padding:12px;" align="center">◯</td>
      <td style="border:1px solid #aaa; padding:12px;">相談</td>
    </tr>
    <tr>
      <td style="border:1px solid #aaa; padding:12px;">買い替え</td>
      <td style="border:1px solid #aaa; padding:12px;" align="center">◯</td>
      <td style="border:1px固 #aaa; padding:12px;">
        現自宅の売買契約書の売却金額又は査定書記載の査定額が、現自宅の他行借入額の100%以上であれば、
        現自宅の住宅ローンを返済比率に含めずに審査可能。売却期限の設定はなく、実行後の売却エビデンスの提出も不要。
        ※1年間のみ、元金据え置きにて利息のみ返済いただきます。1年経過後から通常の月々返済へ切り替わる。
      </td>
    </tr>
  </tbody>
</table>
""", unsafe_allow_html=True)

st.caption("※本ページの数値は社内目安。正式情報は銀行公表値をご確認ください。")