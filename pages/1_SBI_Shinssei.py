# pages/1_SBI_Shinssei.py
import streamlit as st
from lib.bank_common import staff_header, flow_table_horizontal, pdf_viewer, note_box, tag_badge, bullets

st.set_page_config(page_title="SBI新生銀行｜住宅ローン", page_icon="🏦", layout="wide")

st.title("SBI新生銀行｜住宅ローン 商品説明 & 事前審査フロー")

# 金利・団信（8月時点の社内提示数値を画面メモとして掲示）
c1, c2, c3 = st.columns([1.2, 1.2, 2.0])
with c1:
    st.metric("変動金利（8月キャンペーン）", "0.59 %", help="社内提示用メモ。正式条件は毎月の金利公表に準拠。")
with c2:
    st.metric("がん団信 上乗せ", "+0.10 %", help="がん100%：0.59% + 0.10% = 0.69%（参考）")
with c3:
    st.info("最終適用金利は実行時点・商品条件により変動します。", icon="ℹ️")

st.subheader("強み")
bullets([
    "返済比率 一律40％（年収によらず）",
    "外国籍・転職者・旧耐震・住み替え（後売り）にも対応余地",
    "収入合算：合算者の最低年収を100万円へ引下げ（雇用形態不問で100％合算可）",
    "金消時金利（実行時適用）。金利上昇局面で有利",
    "審査金利3.0%で計算（35年返済なら年収約8.65倍目安）",
    "転職：勤続年数不問。オファーレター等の固定給・理論年収・目標設定ボーナスで審査可",
    "産育休：復職有無にかかわらず、休暇含まない年度の源泉票の額面100％で審査（長期は要相談）",
    "住み替え（後売り）：現住居ローンは実行後売却完済でも返比に算入せず審査（条件あり）",
    "団信：最高保険金額を3億円まで引上げ（高額案件も相談可）",
    "永住権無：単身 or 夫婦のどちらかが永住権あれば可、連帯保証人が日本国籍または永住権者必須、日本語または英語での対話ができること"
])

st.markdown("---")
st.subheader("特殊項目")
bullets([
    "諸費用ローン　⭕️",
    "リフォームローン　⭕️",
    "買い替えローン　⭕️：現自宅の売買契約書の売却金額または査定書記載の査定額が、現自宅の他行借入額の100%以上であれば、現自宅ローンを返済比率に含めず審査可能。売却期限設定なし、実行後の売却エビデンス提出不要。",
    "※1年間は元金据置・利息のみ返済、その後通常返済へ切替"
])

st.markdown("---")
st.subheader("事前審査用紙（ダウンロード/閲覧）")

# 新生銀行の事前審査用紙リンク
pdf_links = {
    "A3 印刷 PS住宅ローン審査申込書": "https://github.com/Naobro/fp/blob/main/pages/A3%20%E5%8D%B0%E5%88%B7.%20%20%20%20%20%20%20%20%20%20%20%20%20%20PS%E4%BD%8F%E5%AE%85%E3%83%AD%E3%83%BC%E3%83%B3%E5%AF%A9%E6%9F%BB%E7%94%B3%E8%BE%BC%E6%9B%B88090-1-20240122.pdf",
    "A4 印刷": "https://github.com/Naobro/fp/blob/main/pages/A4%20%E5%8D%B0%E5%88%B7.pdf",
    "ペアローン 同意書": "https://github.com/Naobro/fp/blob/main/pages/%E9%80%A3%E5%B8%AF%E4%BF%9D%E8%A8%BC%E4%BA%88%E5%AE%9A%E8%80%85%E3%81%AE%E5%90%8C%E6%84%8F%E6%9B%B8.pdf"
}

for name, url in pdf_links.items():
    st.link_button(f"📄 {name}", url)
    st.markdown("")
    pdf_viewer(url, height=600)
    st.markdown("---")

st.caption("※ページ上の金利/条件は社内用の目安表示です。正式情報は行の公表値をご確認ください。")