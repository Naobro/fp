import streamlit as st
from fpdf import FPDF
import tempfile
from datetime import datetime
import os

st.set_page_config(page_title="不動産エージェント NAOKI", layout="wide")

# ✅ fontsフォルダの中のフォントを使う
FONT_PATH = os.path.join("fonts", "NotoSansJP-Regular.ttf")
if not os.path.exists(FONT_PATH):
    st.error(f"フォントファイル {FONT_PATH} が見つかりません。fonts フォルダを確認してください。")
    st.stop()

# --- GitHubの blob URL → raw URL 変換ヘルパー ---
def gh_raw(url: str) -> str:
    # 例: https://github.com/Naobro/fp/blob/main/assets/top.png
    # →  https://raw.githubusercontent.com/Naobro/fp/main/assets/top.png
    return url.replace("https://github.com/", "https://raw.githubusercontent.com/").replace("/blob/", "/")

# ============== ヒーロー ==============
# ▼ 指定：タイトルとサブタイトルの“間”にトップ画像
top_img = "https://github.com/Naobro/fp/blob/main/assets/top.png"
st.image(gh_raw(top_img), use_container_width=True)


st.title("不動産エージェント NAOKI")


st.markdown("### 家を買う前に絶対に考えるべき「たった3つのこと」")
st.markdown(
    '<span style="color:blue; font-weight:bold; font-size:20px;">不安の解消 × ライフプラン予算 × 条件整理</span>',
    unsafe_allow_html=True,
)
st.header("理想の住まい探し 成功ロードマップ")
st.markdown(
    """
    <div style="
        background-color:#f0f8ff;
        color:#000080;
        font-size:20px;
        font-weight:bold;
        padding:12px;
        border-radius:8px;
        border: 2px solid #000080;
        text-align:center;
        ">
        ①不安の解消 ➡️ ②ライフプランニング ➡️ ③予算確定 ➡️ ④条件整理
    </div>
    """,
    unsafe_allow_html=True
)

st.divider()

# ============== phase① 不安の解消 ==============
st.subheader("phase①　不安の解消")

# ランキング説明（軽く整形）
st.markdown("🏠 **不動産購入時の不安ランキング（調査対象：500人）**")
st.markdown("""
**主要な不安（上位）**
1. **ローン返済・維持費の捻出ができるか（367人）**  
　長期返済や将来のメンテ費への不安が最多。
2. **近所付き合いがうまくいくか（74人）**  
　新しいコミュニティへの適応不安。
3. **生活環境が良いか（38人）**  
　治安・利便性・騒音など住環境の懸念。
4. **生活環境の変化に対応できるか（32人）**  
　転勤や家族構成など将来変化への備え。
5. **満足いく家が購入できるか（27人）**
6. **災害が起こらないか（25人）**
7. **ローンの審査に通るか（16人）**
""")

# 不安ランキング画像
huan_img = "https://github.com/Naobro/fp/blob/main/assets/huan.png"
st.image(gh_raw(huan_img), use_container_width=True)


# 不安→安心の心構え
st.markdown("""
### 不動産購入の不安を解消するための心構え
- **なぜ不安なのか？** → それは「わからない・見えない」から。
1. **知識を身につけることで、不安の正体を可視化**  
   不動産購入の流れ・ローンの仕組み・インスペクション・災害リスクなど“要点だけ”理解すると、不安は一気に軽くなります。
2. **「待つ」より“価値が落ちにくい家”を選ぶ**  
   いつか安くなる　理想の白馬の王子様を待つだけでは、機会を逃して不安が増すばかり条件整理して　売りやすい/貸しやすい資産性の高い物件選定で自由度UP。
3. **専門家を頼る**  
   不動産×FP×建築士（インスペクション）×近隣調査（トナリスク）複数の専門家を頼ることが安心への近道です。
4. **不安を言語化**  
   不明瞭な不安ほど行動を妨げます。不安を具体的に言葉にする　例：「ローン返済に耐えられるか？」→ ライフプラン＆キャッシュフローで可視化。
5. **“迷う時間”は機会損失**  
   迷っている間に良い物件が他の人に買われてしまうこともしばしばです。70点を超える（つまり十分に満足できそうな）物件に出会ったら、「考えすぎず、行動する」
""")

pdf_url = "https://naobro.github.io/fp/pages/tonari.pdf"
st.markdown(f"[📄 PDFはこちら]({pdf_url})")

st.info("“不安の解消”は ** で可視化→言語化。Next：**ライフプラン　予算** 不安の可視化。")
# ============== phase② ライフプラン　予算 ==============
st.subheader("phase②　ライフプラン　予算")

# FPイメージ（任意）：お金の不安→FPで可視化 への橋渡し
fp_img = "https://github.com/Naobro/fp/blob/main/assets/Fp.png"
st.image(gh_raw(fp_img), use_container_width=True, )


st.divider()

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

# ▼▼▼ ここにお問い合わせフォームリンクを追加 ▼▼▼
st.markdown(
    """
    <div style='margin-top:20px;'>
        <a href="https://docs.google.com/forms/d/e/1FAIpQLSdbG6xqziJWaKf9fBK8uvsrHBMKibCaRadE7qShR3Nl6Cv8Kg/viewform?usp=pp_url"
           target="_blank"
           style="display:inline-block; background:#226BB3; color:white; padding:12px 24px; font-size:18px; font-weight:bold; border-radius:8px; text-decoration:none; margin-bottom:10px;">
           📩 お問い合わせはこちら
        </a>
    </div>
    """,
    unsafe_allow_html=True,
)
# ▲▲▲ お問い合わせフォームここまで ▲▲▲

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
