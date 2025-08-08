import streamlit as st
import json
import os

# 条件のスコア
SCORES = {"MUST": 5, "WANT": 3, "NO": -5, "その他": 1}

# JSON読み込み
with open("data/conditions.json", "r", encoding="utf-8") as f:
    CONDITIONS = json.load(f)

st.set_page_config(page_title="不動産物件比較ツール", layout="wide")

st.title("🏠 不動産物件比較ツール")

# 物件種別選択
property_type = st.radio("物件種別を選択", ["マンション", "戸建", "土地"], horizontal=True)

# 条件リスト取得
condition_groups = CONDITIONS[property_type]

st.subheader("① 現状の条件入力（⭕️: あり / ❌: なし / 🔺: わからない）")
current_conditions = {}
for group, items in condition_groups.items():
    st.markdown(f"### {group}")
    cols = st.columns(len(items))
    for i, item in enumerate(items):
        with cols[i]:
            current_conditions[item] = st.radio(
                item, ["⭕️", "❌", "🔺"], horizontal=True, key=f"current_{item}"
            )

st.subheader("② 希望条件の入力（MUST:5個 / WANT:10個 / NO:10個）")

must_selected, want_selected, no_selected = [], [], []
max_must, max_want, max_no = 5, 10, 10

for group, items in condition_groups.items():
    st.markdown(f"### {group}")
    for item in items:
        choice = st.selectbox(
            f"{item} の優先度",
            ["どちらでも", "MUST", "WANT", "NO"],
            key=f"wish_{item}"
        )
        if choice == "MUST" and len(must_selected) < max_must:
            must_selected.append(item)
        elif choice == "WANT" and len(want_selected) < max_want:
            want_selected.append(item)
        elif choice == "NO" and len(no_selected) < max_no:
            no_selected.append(item)

st.subheader("③ スコア計算")

if st.button("現状のスコアを計算"):
    total_score = 0
    details = []
    for item, value in current_conditions.items():
        score = 0
        if item in must_selected and value == "⭕️":
            score = SCORES["MUST"]
        elif item in want_selected and value == "⭕️":
            score = SCORES["WANT"]
        elif item in no_selected and value == "⭕️":
            score = SCORES["NO"]
        elif value == "⭕️":
            score = SCORES["その他"]

        total_score += score
        details.append((item, value, score))

    st.success(f"✅ 現状の合計スコア: **{total_score}点**")
    st.dataframe(details, use_container_width=True)

st.subheader("④ 物件ごとのスコア比較")

uploaded = st.file_uploader("CSVで物件条件をアップロード（項目は現状と同じ名前）", type="csv")

if uploaded:
    import pandas as pd
    df = pd.read_csv(uploaded)

    def calc_score(row):
        score = 0
        for item in df.columns:
            if row[item] == 1 and item in must_selected:
                score += SCORES["MUST"]
            elif row[item] == 1 and item in want_selected:
                score += SCORES["WANT"]
            elif row[item] == 1 and item in no_selected:
                score += SCORES["NO"]
            elif row[item] == 1:
                score += SCORES["その他"]
        return score

    df["スコア"] = df.apply(calc_score, axis=1)
    df_sorted = df.sort_values("スコア", ascending=False)

    st.dataframe(df_sorted, use_container_width=True)
