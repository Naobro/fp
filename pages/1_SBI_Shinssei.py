# pages/1_SBI_Shinssei.py
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="SBI新生銀行｜住宅ローン", page_icon="🏦", layout="wide")

# 余白（タイトルが切れない最小値）
st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 0.6rem;}
/* テーブルの長文がはみ出さないように調整 */
.sbi-table th, .sbi-table td {
  line-height: 1.6;
  word-break: break-word;
  white-space: normal;
  vertical-align: top;
}
</style>
""", unsafe_allow_html=True)

# プロジェクト直下を特定（/pages/ から一つ上のディレクトリ）
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "sbi"

# ローカルPDF
PDF_A3   = ASSETS / "A3_申込書.pdf"
PDF_PAIR = ASSETS / "ペアローン申込書.pdf"

def load_bytes(p: Path) -> bytes:
    try:
        return p.read_bytes()
    except Exception:
        st.warning(f"ファイルが見つかりません：{p}")
        return b""

st.title("SBI新生銀行｜住宅ローン 商品説明 & 事前審査")

# 金利メモ（固定表示のみ）
c1, c2, c3 = st.columns([1.2, 1.2, 2.0])
with c1:
    st.metric("変動金利（8月キャンペーン）", "0.59 %", help="社内メモ。正式条件は公表値に準拠。")
with c2:
    st.metric("がん団信 上乗せ", "+0.10 %", help="例：がん100%は 0.59% + 0.10% = 0.69%（参考）")
with c3:
    st.info("最終適用金利は実行時点・商品条件で変動します。", icon="ℹ️")

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
      <td style="border:1px solid #aaa; padding:12px;">
        現自宅の売買契約書の売却金額又は査定書記載の査定額が、現自宅の他行借入額の100%以上であれば、
        現自宅の住宅ローンを返済比率に含めずに審査可能。売却期限の設定はなく、実行後の売却エビデンスの提出も不要。
        ※1年間のみ、元金据え置きにて利息のみ返済いただきます。1年経過後から通常の月々返済へ切り替わる。
      </td>
    </tr>
  </tbody>
</table>
""", unsafe_allow_html=True)

st.subheader("事前審査用紙（クリックでダウンロード）")
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

st.caption("※本ページの数値は社内目安。正式情報は銀行公表値をご確認ください。")