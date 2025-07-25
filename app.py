import streamlit as st

# タイトル・キャッチコピー
st.title("不動産エージェント NAOKI")
st.header("理想の住まい探し　成功ロードマップ")
st.markdown("### 家を買う前に絶対に考えるべき「たった3つのこと」")
st.markdown("""
**ライフプラン × 予算 × 条件整理**

この3つが、理想の住まいを叶えるための鍵です。
""")

st.divider()

# 5W2H セクション
st.subheader("5W2Hで理想の住まい探しを整理しよう")
st.markdown("""
- **Why（なぜ）:** なぜ購入を検討していますか？（例：賃貸脱却、子育て環境、資産形成）
- **When（いつ）:** いつまでに購入したいですか？
- **Where（どこで）:** どのエリアでお探しですか？
- **Who（誰が）:** ご家族構成や購入する方は？
- **What（何を）:** どんな物件を希望していますか？
- **How（どのように）:** どんな購入方法をお考えですか？（ローンの利用/頭金の有無/リノベ希望など）
- **How much（いくらで）:** ご予算や資金計画は？
""")

st.info("これらの項目を一緒に整理して、理想の住まい探しをサポートします！")

# 必要に応じて入力フォーム追加もOK
# with st.form("5W2H_form"):
#     why = st.text_input("Why（なぜ購入を検討していますか？）")
#     when = st.text_input("When（いつまでに購入したいですか？）")
#     where = st.text_input("Where（どのエリアでお探しですか？）")
#     who = st.text_input("Who（ご家族構成や購入する方は？）")
#     what = st.text_input("What（どんな物件を希望していますか？）")
#     how = st.text_input("How（どんな購入方法をお考えですか？）")
#     how_much = st.text_input("How much（ご予算や資金計画は？）")
#     submitted = st.form_submit_button("送信")

#     if submitted:
#         st.success("ご入力ありがとうございました！")

