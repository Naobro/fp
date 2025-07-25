import streamlit as st

st.set_page_config(page_title="不動産エージェント NAOKI - ツール＆ヒアリング", layout="wide")

# --- タイトル・説明 ---
st.title("不動産エージェント NAOKI")
st.header("理想の住まい探し 成功ロードマップ")
st.markdown("### 家を買う前に絶対に考えるべき「たった3つのこと」")
st.markdown("""
**ライフプラン × 予算 × 条件整理**

この3つが、理想の住まいを叶えるための鍵です。
""")

st.divider()

# --- 便利ツール 動的リンク ---
st.subheader("便利ツールへジャンプ")
tools = {
    "賃貸 vs 購入 住居費・資産価値シミュレータ": "https://naobro-fp-streamlitapp-budget-py.streamlit.app/",
    "諸費用計算シート": "https://naobro-fp-streamlitapp-howmuch-py.streamlit.app/",
    "簡易ライフプランニング表": "https://naobro-fp-streamlitapp-lifeplan-py.streamlit.app/",
    "購入時期診断ツール": "https://naobro-fp-streamlitapp-when-py.streamlit.app/",
}
for name, url in tools.items():
    st.markdown(f"- [{name}]({url})")


for name, url in github_tools.items():
    st.markdown(f"- [{name}]({url})")

st.divider()

# --- ヒアリングフォーム ---
st.subheader("ヒアリングフォーム")

with st.form("hearing_form"):
    now_area = st.text_input("現在の居住エリア・駅")
    now_years = st.number_input("居住年数", min_value=0, max_value=100, value=5)
    is_owner = st.selectbox("持ち家・賃貸", ["持ち家", "賃貸"])
    now_rent = st.number_input("住居費（万円/月）", min_value=0, max_value=100, value=10)
    family = st.text_input("ご家族構成")
    commute_time = st.text_input("通勤時間")
    company = st.text_input("勤務先")
    service_years = st.number_input("勤続年数", min_value=0, max_value=50, value=3)
    income = st.number_input("年収（万円）", min_value=0, max_value=10000, value=700)
    sat_point = st.text_area("今の住まいで満足されている点・不満な点")
    search_status = st.text_area("物件探しの進捗")
    why_buy = st.text_area("なぜ不動産購入したいのか？")

    task = st.text_area("不満な点がこうなったらいい？")
    anxiety = st.text_area("将来に不安や心配はありますか？")
    rent_vs_buy = st.text_area("賃貸と購入、それぞれで迷われている点は？")
    other_trouble = st.text_area("他にもお住まい探しで困っていることはありますか？")

    effect = st.text_area("その課題や不安が今後も続いた場合、どのような影響があると思いますか？")
    forecast = st.text_area("今のままだと数年後どうなりそうですか？")
    event_effect = st.text_area("ライフイベントが控えている場合、それが現状の住まいにどんな影響を与えそうですか？")
    missed_timing = st.text_area("住み替えのタイミングを逃すことで、家賃の支払いがどれだけ増えるとお考えですか？")

    ideal_life = st.text_area("理想の暮らし、理想のお住まいはどんなイメージですか？")
    solve_feeling = st.text_area("もし今の課題が解決できるとしたら、どんな気持ちになりますか？")
    goal = st.text_area("お住まい購入によって「こうなりたい」という目標はありますか？")
    important = st.text_area("住まい選びで一番大切にしたいことは何ですか？")
    must = st.text_area("MAST条件3つのみ")
    want = st.text_area("WANT条件")
    ng = st.text_area("逆にNG条件")

    submitted = st.form_submit_button("送信")
    if submitted:
        st.success("ご入力ありがとうございました！（入力内容はセッションに一時保存されます）")
        st.session_state['hearing'] = {
            "area": now_area, "now_years": now_years, "is_owner": is_owner, "now_rent": now_rent,
            "family": family, "commute_time": commute_time, "company": company,
            "service_years": service_years, "income": income, "sat_point": sat_point, "search_status": search_status,
            "why_buy": why_buy, "task": task, "anxiety": anxiety, "rent_vs_buy": rent_vs_buy,
            "other_trouble": other_trouble, "effect": effect, "forecast": forecast,
            "event_effect": event_effect, "missed_timing": missed_timing, "ideal_life": ideal_life,
            "solve_feeling": solve_feeling, "goal": goal, "important": important,
            "must": must, "want": want, "ng": ng,
        }

# 入力確認用（開発時のみ）
if 'hearing' in st.session_state:
    st.write("=== ヒアリング内容（セッション一時保存） ===")
    st.json(st.session_state['hearing'])
