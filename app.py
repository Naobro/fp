import streamlit as st
from fpdf import FPDF
import tempfile
from datetime import datetime
import os

st.set_page_config(page_title="不動産エージェント NAOKI", layout="wide")

# ✅ fontsフォルダの中のフォントを使うように修正
FONT_PATH = os.path.join("fonts", "NotoSansJP-Regular.ttf")
if not os.path.exists(FONT_PATH):
    st.error(f"フォントファイル {FONT_PATH} が見つかりません。fonts フォルダを確認してください。")
    st.stop()

st.title("不動産エージェント NAOKI")
st.header("理想の住まい探し 成功ロードマップ")
st.markdown("### 家を買う前に絶対に考えるべき「たった3つのこと」")
st.markdown('<span style="color:blue; font-weight:bold; font-size:20px;">ライフプラン × 予算 × 条件整理</span>', unsafe_allow_html=True)
st.divider()

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

st.subheader("便利ツールへジャンプ")
tools = {
    "物件検索": "https://picks-agent.terass.com/search/mansion",
    "住宅ローン　チェッカー": "https://loan-checker.jp/loan",
    "住宅ローン　提案書": "https://mortgagenao.streamlit.app/",
    "賃貸 vs 購入 住居費・資産価値シミュレータ": "https://budget1.streamlit.app/",
    "諸費用計算シート": "https://howmuch1.streamlit.app/",
    "簡易ライフプランニング表": "https://lifeplan.streamlit.app/",
    "購入時期診断ツール": "https://when79.streamlit.app/",
}
for name, url in tools.items():
    st.markdown(f'<a href="{url}" target="_blank">{name}</a>', unsafe_allow_html=True)
st.divider()

### ヒアリングフォーム
st.subheader("ヒアリング内容")

if "hearing_data" not in st.session_state:
    st.session_state["hearing_data"] = {
        "name": "",
        "now_area": "",
        "now_years": 5,
        "is_owner": "賃貸",
        "now_rent": 10,
        "family": "",
        "commute_time": "",
        "husband_company": "",
        "husband_income": 0,
        "husband_service_years": 3,
        "wife_company": "",
        "wife_income": 0,
        "wife_service_years": 3,
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
        "ng": "",
        "other_agent": "",
        "why_terass": "",
    }

data = st.session_state["hearing_data"]

with st.form("hearing_form", clear_on_submit=False):
    data["name"] = st.text_input("お名前", value=data["name"])
    data["now_area"] = st.text_input("現在の居住エリア・駅", value=data["now_area"])
    data["now_years"] = st.number_input("居住年数", min_value=0, max_value=100, value=data["now_years"])
    data["is_owner"] = st.selectbox("持ち家・賃貸", ["持ち家", "賃貸"], index=1)
    data["now_rent"] = st.number_input("住居費（万円/月）", min_value=0, max_value=100, value=data["now_rent"])
    data["family"] = st.text_input("ご家族構成", value=data["family"])
    data["commute_time"] = st.text_input("通勤時間", value=data["commute_time"])
    data["husband_company"] = st.text_input("ご主人の勤務先", value=data["husband_company"])
    data["husband_income"] = st.number_input("ご主人の年収（万円）", min_value=0, max_value=10000, value=data["husband_income"])
    data["husband_service_years"] = st.number_input("ご主人の勤続年数", min_value=0, max_value=50, value=data["husband_service_years"])
    data["wife_company"] = st.text_input("奥様の勤務先", value=data["wife_company"])
    data["wife_income"] = st.number_input("奥様の年収（万円）", min_value=0, max_value=10000, value=data["wife_income"])
    data["wife_service_years"] = st.number_input("奥様の勤続年数", min_value=0, max_value=50, value=data["wife_service_years"])

    # 記述式の質問
    for field, label in [
        ("sat_point", "今の住まいで満足されている点・不満な点"),
        ("search_status", "物件探しの進捗"),
        ("why_buy", "なぜ不動産購入したいのか？"),
        ("task", "不満な点がこうなったらいい？"),
        ("anxiety", "将来に不安や心配はありますか？"),
        ("rent_vs_buy", "賃貸と購入、それぞれで迷われている点は？"),
        ("other_trouble", "他にもお住まい探しで困っていることはありますか？"),
        ("effect", "その課題や不安が今後も続いた場合、どのような影響があると思いますか？"),
        ("forecast", "今のままだと数年後どうなりそうですか？"),
        ("event_effect", "ライフイベントが控えている場合、それが現状の住まいにどんな影響を与えそうですか？"),
        ("missed_timing", "住み替えのタイミングを逃すことで、家賃の支払いがどれだけ増えるとお考えですか？"),
        ("ideal_life", "理想の暮らし、理想のお住まいはどんなイメージですか？"),
        ("solve_feeling", "もし今の課題が解決できるとしたら、どんな気持ちになりますか？"),
        ("goal", "お住まい購入によって「こうなりたい」という目標はありますか？"),
        ("important", "住まい選びで一番大切にしたいことは何ですか？"),
        ("must", "MAST条件3つのみ"),
        ("want", "WANT条件"),
        ("ng", "逆にNG条件"),
        ("other_agent", "他社ともやり取りしていますか？"),
        ("why_terass", "なぜTERASSに問い合わせをしてくれましたか？"),
    ]:
        data[field] = st.text_area(label, value=data[field])

    submitted = st.form_submit_button("送信")

if submitted:
    st.success("ご入力ありがとうございました！下記ボタンからPDFでダウンロードできます。")

    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("NotoSansJP", "", FONT_PATH, uni=True)
    pdf.add_font("NotoSansJP", "B", FONT_PATH, uni=True)

    pdf.set_font("NotoSansJP", "B", 16)
    pdf.cell(0, 10, "不動産ヒアリングシート", 0, 1, "C")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pdf.set_font("NotoSansJP", "", 10)
    pdf.cell(0, 8, f"作成日時：{now}", 0, 1, "R")
    pdf.ln(5)

    def pdf_write(label, value):
        pdf.set_font("NotoSansJP", "B", 12)
        pdf.multi_cell(0, 8, f"{label}")
        pdf.set_font("NotoSansJP", "", 12)
        pdf.multi_cell(0, 8, str(value) if value else "（未入力）")
        pdf.ln(2)

    pdf_write("お名前", data.get("name", ""))
    pdf_write("世帯年収（万円）", data.get("husband_income", 0) + data.get("wife_income", 0))

    for key, label in [
        ("now_area", "現在の居住エリア・駅"),
        ("now_years", "居住年数"),
        ("is_owner", "持ち家・賃貸"),
        ("now_rent", "住居費（月）"),
        ("family", "ご家族構成"),
        ("commute_time", "通勤時間"),
        ("husband_company", "ご主人の勤務先"),
        ("husband_income", "ご主人の年収（万円）"),
        ("husband_service_years", "ご主人の勤続年数"),
        ("wife_company", "奥様の勤務先"),
        ("wife_income", "奥様の年収（万円）"),
        ("wife_service_years", "奥様の勤続年数"),
        ("sat_point", "今の住まいで満足されている点・不満な点"),
        ("search_status", "物件探しの進捗"),
        ("why_buy", "なぜ不動産購入したいか"),
        ("task", "不満な点がこうなったらいい？"),
        ("anxiety", "将来に不安や心配"),
        ("rent_vs_buy", "賃貸と購入で迷っている点"),
        ("other_trouble", "他にもお住まい探しで困っていること"),
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
        ("other_agent", "他社とのやり取り状況"),
        ("why_terass", "TERASSに問い合わせた理由"),
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
            mime="application/pdf",
        )
