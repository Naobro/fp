# pages/2_MUFG.py
import streamlit as st
from lib.bank_common import staff_header, flow_table_horizontal, pdf_viewer, note_box, tag_badge, bullets

st.set_page_config(page_title="三菱UFJ銀行｜住宅ローン", page_icon="🏦", layout="wide")

st.title("三菱UFJ銀行｜住宅ローン 商品説明 & 事前審査フロー")

# 担当者情報（編集可）
staff_header(editable=True)

st.subheader("商品説明（社内共有用）")
bullets([
    "変動・固定のラインナップ。ワイド団信（+0.3%）など特約あり。",
    "三大疾病50% などの保障バリエーション。",
    "取り扱い・詳細条件は行公表値を都度参照。",
])

st.markdown("---")
st.subheader("事前審査フロー（横長）")
flow_table_horizontal([
    {"step":"STEP1", "内容":"ヒアリング（属性・希望条件・資金計画）", "目安":"15–30分", "提出物":"本人確認（免許/在留/保険証）"},
    {"step":"STEP2", "内容":"必要書類の収集（源泉徴収票・給与明細 等）", "目安":"当日〜3日", "提出物":"年収書類・在職/勤続確認"},
    {"step":"STEP3", "内容":"事前審査申込（オンライン）", "目安":"15–20分", "提出物":"申込フォーム・同意書"},
    {"step":"STEP4", "内容":"審査（属性・与信・物件）", "目安":"1–3営業日", "提出物":"追加質問の随時対応"},
    {"step":"STEP5", "内容":"結果共有・資金計画の確定", "目安":"即日", "提出物":"—"},
])

st.markdown("---")
st.subheader("商品説明（PDF）")
ufj_pdf = "https://github.com/Naobro/fp/blob/main/pages/ufj.pdf"
st.link_button("📄 三菱UFJ銀行｜商品説明（PDFを開く）", ufj_pdf)
pdf_viewer(ufj_pdf, height=820)

st.markdown("---")
st.subheader("三菱UFJ 事前審査（オンライン）")
st.link_button("🔗 事前審査ログイン（仲介向け）", "https://web.smart-entry-tab.jp/setWeb/estate/login/?realtor_cd=HGSHW-04384")

with st.expander("ログイン情報（社内メモ）", expanded=False):
    st.code("受付コード： w-mufg-hgshw001", language="text")
    st.info("担当者名・メールは本ページ上部の編集欄で修正・維持できます。", icon="📝")

st.markdown("---")
st.subheader("営業トークの要点（タグ）")
tag_badge("ワイド団信+0.3%")
tag_badge("三大疾病50%")
tag_badge("オンライン申込可")
tag_badge("PDFで即説明")