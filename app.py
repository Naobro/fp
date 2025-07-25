import streamlit as st
from fpdf import FPDF
import tempfile

# ページ設定
st.set_page_config(page_title="不動産エージェント NAOKI", layout="wide")

# タイトル・キャッチコピー
st.title("不動産エージェント NAOKI")
st.header("理想の住まい探し 成功ロードマップ")
st.markdown("### 家を買う前に絶対に考えるべき「たった3つのこと」")
st.markdown("""
**ライフプラン × 予算 × 条件整理**

この3つが、理想の住まいを叶えるための鍵です。
""")
st.divider()

# 5W2H
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
st.divider()

# 便利ツールへのリンク
st.subheader("便利ツールへジャンプ")
tools = {
    "賃貸 vs 購入 住居費・資産価値シミュレータ": "https://budget1.streamlit.app/",
    "諸費用計算シート": "https://howmuch1.streamlit.app/",
    "簡易ライフプランニング表": "https://lifeplan.streamlit.app/",
    "購入時期診断ツール": "https://when79.streamlit.app/",
}
for name, url in tools.items():
    st.markdown(f"- [{name}]({url})")
st.divider()

# --- ヒアリングフォーム ---
st.subheader("ヒアリングフォーム")

# セッションステート初期化（フォーム項目の保存用）
if 'hearing_data' not in st.session_state:
    st.session_state['hearing_data'] = {
        "now_area": "",
        "now_years": 5,
        "is_owner": "持ち家",
        "now_rent": 10,
        "family": "",
        "commute_time": "",
        "company": "",
        "service_years": 3,
        "income": 700,
        "sat_point": "",
        "search_status": "",
        "why_buy": "",
        "task": "",
        "anxiety": "",
        "rent_vs_buy": "",
        "other_trouble": "",
        "effect": "",
        "forecast": "",
        "event_effect": "",
        "missed_timing": "",
        "ideal_life": "",
        "solve_feeling": "",
        "goal": "",
        "important": "",
        "must": "",
        "want": "",
        "ng": ""
    }

data = st.session_state['hearing_data']

with st.form("hearing_form", clear_on_submit=False):
    data["now_area"] = st.text_input("現在の居住エリア・駅", value=data["now_area"])
    data["now_years"] = st.number_input("居住年数", min_value=0, max_value=100, value=data["now_years"])
    data["is_owner"] = st.selectbox("持ち家・賃貸", ["持ち家", "賃貸"], index=0 if data["is_owner"]=="持ち家" else 1)
    data["now_rent"] = st.number_input("住居費（万円/月）", min_value=0, max_value=100, value=data["now_rent"])
    data["family"] = st.text_input("ご家族構成", value=data["family"])
    data["commute_time"] = st.text_input("通勤時間", value=data["commute_time"])
    data["company"] = st.text_input("勤務先", value=data["company"])
    data["service_years"] = st.number_input("勤続年数", min_value=0, max_value=50, value=data["service_years"])
    data["income"] = st.number_input("年収（万円）", min_value=0, max_value=10000, value=data["income"])
    data["sat_point"] = st.text_area("今の住まいで満足されている点・不満な点", value=data["sat_point"])
    data["search_status"] = st.text_area("物件探しの進捗", value=data["search_status"])
    data["why_buy"] = st.text_area("なぜ不動産購入したいのか？", value=data["why_buy"])

    data["task"] = st.text_area("不満な点がこうなったらいい？", value=data["task"])
    data["anxiety"] = st.text_area("将来に不安や心配はありますか？", value=data["anxiety"])
    data["rent_vs_buy"] = st.text_area("賃貸と購入、それぞれで迷われている点は？", value=data["rent_vs_buy"])
    data["other_trouble"] = st.text_area("他にもお住まい探しで困っていることはありますか？", value=data["other_trouble"])

    data["effect"] = st.text_area("その課題や不安が今後も続いた場合、どのような影響があると思いますか？", value=data["effect"])
    data["forecast"] = st.text_area("今のままだと数年後どうなりそうですか？", value=data["forecast"])
    data["event_effect"] = st.text_area("ライフイベントが控えている場合、それが現状の住まいにどんな影響を与えそうですか？", value=data["event_effect"])
    data["missed_timing"] = st.text_area("住み替えのタイミングを逃すことで、家賃の支払いがどれだけ増えるとお考えですか？", value=data["missed_timing"])

    data["ideal_life"] = st.text_area("理想の暮らし、理想のお住まいはどんなイメージですか？", value=data["ideal_life"])
    data["solve_feeling"] = st.text_area("もし今の課題が解決できるとしたら、どんな気持ちになりますか？", value=data["solve_feeling"])
    data["goal"] = st.text_area("お住まい購入によって「こうなりたい」という目標はありますか？", value=data["goal"])
    data["important"] = st.text_area("住まい選びで一番大切にしたいことは何ですか？", value=data["important"])
    data["must"] = st.text_area("MAST条件3つのみ", value=data["must"])
    data["want"] = st.text_area("WANT条件", value=data["want"])
    data["ng"] = st.text_area("逆にNG条件", value=data["ng"])

    submitted = st.form_submit_button("送信")

if submitted:
    st.success("ご入力ありがとうございました！下記ボタンからPDFでダウンロードできます。")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(0, 10, "不動産ヒアリングシート", 0, 1, "C")
    pdf.ln(5)

    def pdf_write(label, value):
        pdf.set_font("Arial", "B", 12)
        pdf.cell(50, 8, f"{label}:", 0, 0)
        pdf.set_font("Arial", "", 12)
        pdf.multi_cell(0, 8, str(value) if value else "（未入力）")

    for key, label in [
        ("now_area", "現在の居住エリア・駅"),
        ("now_years", "居住年数"),
        ("is_owner", "持ち家・賃貸"),
        ("now_rent", "住居費（月）"),
        ("family", "ご家族構成"),
        ("commute_time", "通勤時間"),
        ("company", "勤務先"),
        ("service_years", "勤続年数"),
        ("income", "年収"),
        ("sat_point", "今の住まいの満足点・不満点"),
        ("search_status", "物件探しの進捗"),
        ("why_buy", "なぜ不動産購入したいか"),
        ("task", "不満な点がこうなったらいい？"),
        ("anxiety", "将来に不安や心配"),
        ("rent_vs_buy", "賃貸と購入で迷っている点"),
        ("other_trouble", "その他困っていること"),
        ("effect", "課題や不安の影響"),
        ("forecast", "数年後の予想"),
        ("event_effect", "ライフイベントの影響"),
        ("missed_timing", "住み替えタイミングを逃す影響"),
        ("ideal_life", "理想の暮らし・住まい"),
        ("solve_feeling", "課題解決時の気持ち"),
        ("goal", "購入による目標"),
        ("important", "住まい選びで大切なこと"),
        ("must", "MAST条件3つ"),
        ("want", "WANT条件"),
        ("ng", "逆にNG条件"),
    ]:
        pdf_write(label, data.get(key, ""))

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        pdf.output(tmp_file.name)
        pdf_path = tmp_file.name

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
        st.download_button(
            label="ヒアリング内容をPDFでダウンロード",
            data=pdf_bytes,
            file_name="hearing_sheet.pdf",
            mime="application/pdf"
        )
