# pages/1_SBI_Shinssei.py
import streamlit as st
import urllib.request
import ssl

st.set_page_config(page_title="SBI新生銀行｜住宅ローン", page_icon="🏦", layout="wide")

# 余白最小化
st.markdown("""
<style>
.block-container {padding-top: 0.6rem; padding-bottom: 0.6rem;}
</style>
""", unsafe_allow_html=True)

# ---- PDF取得（標準ライブラリのみ） ----
@st.cache_data(show_spinner=False, ttl=3600)
def fetch_pdf_bytes(raw_url: str) -> bytes:
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(raw_url, context=ctx) as resp:
        return resp.read()

# ---- GitHub raw URL（お客様配布用・直接DLに利用）----
PDF_A3  = "https://raw.githubusercontent.com/Naobro/fp/main/pages/A3%20%E5%8D%B0%E5%88%B7.%20%20%20%20%20%20%20%20%20%20%20%20%20%20PS%E4%BD%8F%E5%AE%85%E3%83%AD%E3%83%BC%E3%83%B3%E5%AF%A9%E6%9F%BB%E7%94%B3%E8%BE%BC%E6%9B%B88090-1-20240122.pdf"
PDF_A4  = "https://raw.githubusercontent.com/Naobro/fp/main/pages/A4%20%E5%8D%B0%E5%88%B7.pdf"
PDF_PAIR = "https://raw.githubusercontent.com/Naobro/fp/main/pages/%E9%80%A3%E5%B8%AF%E4%BF%9D%E8%A8%BC%E4%BA%88%E5%AE%9A%E8%80%85%E3%81%AE%E5%90%8C%E6%84%8F%E6%9B%B8.pdf"

st.title("SBI新生銀行｜住宅ローン 商品説明 & 事前審査")

# 金利表示（固定文言：自動埋め込み/自動DLなし）
c1, c2, c3 = st.columns([1.2, 1.2, 2.0])
with c1:
    st.metric("変動金利（8月キャンペーン）", "0.59 %", help="社内メモ。正式条件は行公表に準拠。")
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
- 諸費用ローン　⭕️  
- リフォームローン　⭕️  
- 買い替えローン　⭕️：現自宅の売買契約書の売却金額または査定額が他行借入額の100%以上なら、現自宅ローンを返済比率に含めず審査可。売却期限なし・実行後の売却エビデンス提出不要。  
- ※1年間は元金据置・利息のみ返済、その後通常返済へ切替
""")

st.subheader("事前審査用紙（クリックでダウンロード）")
colA, colB, colC = st.columns(3)
with colA:
    try:
        data = fetch_pdf_bytes(PDF_A3)
        st.download_button("📥 A3 印刷 PS住宅ローン審査申込書", data=data, file_name="A3_PS_住宅ローン審査申込書.pdf", mime="application/pdf")
    except Exception:
        st.link_button("📄 A3 印刷（開く）", PDF_A3.replace("raw.githubusercontent.com", "github.com").replace("/main/", "/blob/"))
with colB:
    try:
        data = fetch_pdf_bytes(PDF_A4)
        st.download_button("📥 A4 印刷", data=data, file_name="A4_印刷.pdf", mime="application/pdf")
    except Exception:
        st.link_button("📄 A4 印刷（開く）", PDF_A4.replace("raw.githubusercontent.com", "github.com").replace("/main/", "/blob/"))
with colC:
    try:
        data = fetch_pdf_bytes(PDF_PAIR)
        st.download_button("📥 ペアローン 同意書", data=data, file_name="ペアローン同意書.pdf", mime="application/pdf")
    except Exception:
        st.link_button("📄 ペアローン 同意書（開く）", PDF_PAIR.replace("raw.githubusercontent.com", "github.com").replace("/main/", "/blob/"))

st.caption("※本ページの数値は社内目安。正式情報は銀行公表値をご確認ください。")