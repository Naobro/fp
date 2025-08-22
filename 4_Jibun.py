# pages/4_Jibun.py
import streamlit as st
from lib.bank_common import staff_header, flow_table_horizontal, tag_badge, bullets

st.set_page_config(page_title="じぶん銀行｜住宅ローン", page_icon="🏦", layout="wide")

st.title("じぶん銀行｜住宅ローン 商品説明 & 事前審査フロー")

# 担当者情報（編集可）
staff_header(editable=True)

st.subheader("商品説明（社内共有用）")
bullets([
    "がん100（+0.054% 参考）や 7大疾病（+0.10% 参考）等の特約ラインナップ（時期により変動）",
    "ネット完結系の強み・スピードとコスト訴求",
    "ワイド団信（+0.3%）の説明余地",
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
st.subheader("営業トークの要点（タグ）")
tag_badge("がん100 +0.054%")
tag_badge("7大疾病 +0.10%")
tag_badge("ワイド団信 +0.3%")
tag_badge("ネット完結/スピード")