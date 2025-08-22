# pages/1_SBI_Shinssei.py
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="SBI新生銀行｜住宅ローン", page_icon="🏦", layout="wide")

# 余白（タイトルが切れない最小値）
st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 0.6rem;}
</style>
""", unsafe_allow_html=True)

# プロジェクト直下を特定（/pages/ から一つ上のディレクトリ）
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "sbi"

# ローカルPDF（必ず存在する前提のパス）
PDF_A3   = ASSETS / "A3_申込書.pdf"
PDF_A4   = ASSETS / "A4_申込書.pdf"
PDF_PAIR = ASSETS / "ペアローン同意書.pdf"

def load_bytes(p: Path) -> bytes:
    return p.read_bytes()

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

st.subheader("特殊項目")
st.markdown("""
- 諸費用　◯（物件価格の <b>110%</b> まで）  
- リフォーム　◯（<b>2本扱い／本体と同金利</b>）  
- 買い替え　◯（可能だが、<b>原則 返済比率に含めて計算</b>）
""", unsafe_allow_html=True)

st.subheader("事前審査用紙（クリックでダウンロード）")
col1, col2, col3 = st.columns(3)
with col1:
    st.download_button("📥 A3 申込書", data=load_bytes(PDF_A3), file_name="SBI_A3_申込書.pdf", mime="application/pdf")
with col2:
    st.download_button("📥 A4 申込書", data=load_bytes(PDF_A4), file_name="SBI_A4_申込書.pdf", mime="application/pdf")
with col3:
    st.download_button("📥 ペアローン同意書", data=load_bytes(PDF_PAIR), file_name="SBI_ペアローン同意書.pdf", mime="application/pdf")

st.caption("※本ページの数値は社内目安。正式情報は銀行公表値をご確認ください。")