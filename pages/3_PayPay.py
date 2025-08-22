# pages/3_PayPay.py
import streamlit as st
from lib.bank_common import staff_header, flow_table_horizontal, pdf_viewer, tag_badge, bullets

st.set_page_config(page_title="PayPay銀行｜住宅ローン", page_icon="🏦", layout="wide")

st.title("PayPay銀行｜住宅ローン 商品説明 & 事前審査フロー")

# 担当者情報（編集可）
staff_header(editable=True)

st.subheader("商品説明（社内共有用）")
bullets([
    "がん50 / がん100 の上乗せ設定あり（参考：+0.05% / +0.15% 等、案件・時期により変動）",
    "がん50以上で全疾病・失業補償と連動（社内トーク用）",
    "ソフトバンク系割引（例：最大 -0.13%）の訴求余地",
    "125%ルールなし での借換/繰上視点の説明がしやすい",
])

st.markdown("---")
st.subheader("商品説明（PDF）")
pp_pdf = "https://github.com/Naobro/fp/blob/main/pages/paypay.pdf"
st.link_button("📄 PayPay銀行｜商品説明（PDFを開く）", pp_pdf)
pdf_viewer(pp_pdf, height=820)

st.markdown("---")
st.subheader("事前審査フロー（横長）")
flow_table_horizontal([
    {"step":"STEP1", "内容":"ヒアリング（属性・希望条件・資金計画）", "目安":"15–30分", "提出物":"本人確認（免許/在留/保険証）"},
    {"step":"STEP2", "内容":"必要書類の収集（源泉徴収票・給与明細 等）", "目安":"当日〜3日", "提出物":"年収書類・在職/勤続確認"},
    {"step":"STEP3", "内容":"事前審査申込（オンライン/紙）", "目安":"15–20分", "提出物":"申込フォーム・同意書"},
    {"step":"STEP4", "内容":"審査（属性・与信・物件）", "目安":"1–3営業日", "提出物":"追加質問の随時対応"},
    {"step":"STEP5", "内容":"結果共有・資金計画の確定", "目安":"即日", "提出物":"—"},
])

st.markdown("---")
st.subheader("営業トークの要点（タグ）")
tag_badge("がん50/100")
tag_badge("全疾病・失業補償")
tag_badge("ソフトバンク割 最大-0.13%")
tag_badge("125%ルールなし")