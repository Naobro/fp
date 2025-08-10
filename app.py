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
        ①不安の解消 ➡️ ②ライフプランニング ➡️ ③予算確定 ➡️ ④条件整理➡️ ⑤内見
    </div>
    """,
    unsafe_allow_html=True
)
st.header("一番重要な事は良い物件と出会った時に即決できる様に、条件整理・資金準備をしておく事")
st.divider()
st.subheader("不動産購入の流れ")
pdf_url = "https://naobro.github.io/fp/pages/flow_compressed.pdf"
st.markdown(f"[相談から引き渡しまで]({pdf_url})")
pdf_url = "https://naobro.github.io/fp/pages/tochi.pdf"
st.markdown(f"[注文住宅　土地]({pdf_url})")
st.divider()

# ============== phase① 不安の解消 ==============
st.subheader("phase①　不安の解消")


# 不安ランキング画像
huan_img = "https://github.com/Naobro/fp/blob/main/assets/huan.png"
st.image(gh_raw(huan_img), use_container_width=True)


st.markdown("## 🏠 不動産購入時の不安ランキング（調査対象：500人）")

# HTMLで横スクロール対応テーブル作成
table_html = """
<div style="overflow-x:auto;">
<table style="border-collapse: collapse; width: 100%; min-width: 600px; font-size:14px;">
<thead>
<tr style="background-color: #f2f2f2;">
    <th style="border: 1px solid #ddd; padding: 8px;">不安内容</th>
    <th style="border: 1px solid #ddd; padding: 8px;">なぜ不安になるか</th>
    <th style="border: 1px solid #ddd; padding: 8px;">解決策</th>
</tr>
</thead>
<tbody>
<tr>
    <td style="border: 1px solid #ddd; padding: 8px;">ローン返済・維持費の捻出ができるか（367人）</td>
    <td style="border: 1px solid #ddd; padding: 8px;">将来の収入・支出・金利・修繕費が不透明</td>
    <td style="border: 1px solid #ddd; padding: 8px;">✅ FPによるライフプラン・キャッシュフロー可視化<br>💡 金利上昇・修繕費増加のシナリオ分析</td>
</tr>
<tr>
    <td style="border: 1px solid #ddd; padding: 8px;">近所付き合いがうまくいくか（74人）</td>
    <td style="border: 1px solid #ddd; padding: 8px;">人間関係やトラブルの予測が困難</td>
    <td style="border: 1px solid #ddd; padding: 8px;">✅ トナリスク等の近隣調査で対応可<br>💡 購入前の現地見学・時間帯別の雰囲気確認</td>
</tr>
<tr>
    <td style="border: 1px solid #ddd; padding: 8px;">生活環境が良いか（38人）</td>
    <td style="border: 1px solid #ddd; padding: 8px;">治安・利便性・騒音などの情報不足</td>
    <td style="border: 1px solid #ddd; padding: 8px;">✅ 物件選定時に条件整理＆現地確認<br>💡 勤務先・ターミナル駅へのアクセス確認<br>💡 現地で線路や幹線道路の有無を確認</td>
</tr>
<tr>
    <td style="border: 1px solid #ddd; padding: 8px;">生活環境の変化に対応できるか（32人）</td>
    <td style="border: 1px solid #ddd; padding: 8px;">転勤・子育て・介護などの変化</td>
    <td style="border: 1px solid #ddd; padding: 8px;">✅ FP相談で将来の可変性を確認</td>
</tr>
<tr>
    <td style="border: 1px solid #ddd; padding: 8px;">満足いく家が購入できるか（27人）</td>
    <td style="border: 1px solid #ddd; padding: 8px;">完璧を求めて条件が絞れない</td>
    <td style="border: 1px solid #ddd; padding: 8px;">✅ 「70点」ルール（現状50点→70点以上でGO）<br>💡 予算を上げる・50年ローン検討<br>💡 内覧後の判断基準シート活用</td>
</tr>
<tr>
    <td style="border: 1px solid #ddd; padding: 8px;">災害が起こらないか（25人）</td>
    <td style="border: 1px solid #ddd; padding: 8px;">ハザードリスクへの不安</td>
    <td style="border: 1px solid #ddd; padding: 8px;">✅ ハザードマップで事前確認</td>
</tr>
<tr>
    <td style="border: 1px solid #ddd; padding: 8px;">ローンの審査に通るか（16人）</td>
    <td style="border: 1px solid #ddd; padding: 8px;">借入金額・個人情報などの不安</td>
    <td style="border: 1px solid #ddd; padding: 8px;">✅ 事前審査で解消<br>💡 個人情報が心配な方は信用情報機関で事前確認推奨</td>
</tr>
</tbody>
</table>
</div>
"""

st.markdown(table_html, unsafe_allow_html=True)






pdf_url = "https://naobro.github.io/fp/pages/tonari.pdf"
st.markdown(f"[📄 近隣調査　トナリスク]({pdf_url})")

st.info("“不安の解消は可視化して、専門家　データで解消　Next：**ライフプラン　予算** 。")
# ============== phase② ライフプラン　予算 ==============
st.subheader("phase②　ライフプラン　予算")

# FPイメージ（任意）：お金の不安→FPで可視化 への橋渡し
fp_img = "https://github.com/Naobro/fp/blob/main/assets/Fp.png"
st.image(gh_raw(fp_img), use_container_width=True, )


st.divider()
# =========================
# フェーズ② ライフプラン／予算（あなたの意図120%版）
# =========================
st.header("フェーズ② ライフプラン／予算")

# 画像（必要に応じて差し替え）
huan_img   = "https://naobro.github.io/fp/assets/huan.png"     # 不動産購入の不安：圧倒的1位はお金
danshin_img= "https://naobro.github.io/fp/assets/danshin.png"   # 団信イラスト
neage_img  = "https://naobro.github.io/fp/assets/neage.jpeg"    # 家賃値上げの現実（SNS引用イメージ等）
asia_img   = "https://naobro.github.io/fp/assets/sekai.jpg"     # アジア都市比較（任意）


st.markdown("## 💰 不動産購入時の不安ランキング　圧倒的　第1位🥇　【お金】")
# 1) もし、から入る（共感の起点）
st.markdown(
    """
    <div style="background:#fff3cd;border:1px solid #ffe49a;border-radius:10px;padding:14px 16px;">
      <b>もし、宝くじで10億円が当たったら——</b><br>
      きっと今の「お金の不安」は一気に小さくなりますよね。<br>
      つまり不安の正体は“<b>見えないお金</b>”。だったら、<u>見える化</u>すればいい。
    </div>
    """,
    unsafe_allow_html=True
)

# 2) 本質の問い：それって家賃なら払える？
st.markdown(
    """
    ### 住宅ローンが払えるか不安な人　それって、家賃なら払えるんですか？
    - 住宅ローンが不安 → でも<strong>同額の家賃</strong>なら「払える」と思っていませんか？  
    - しかも将来は<strong>インフレにより、お金の価値が下がるので、実質的な返済負担は軽くなる</strong>が、賃貸は<strong>逆に家賃アップの可能性大</strong>。
    """,
    unsafe_allow_html=True
)

# 強調見出し（単独表示）
st.markdown(
    """
    <div style="font-weight:900; color:#000000; font-size:22px; margin:12px 0 8px;">
      家賃は上がる。あなたの収入が下がっても家賃は下がらない。
    </div>
    """,
    unsafe_allow_html=True
)

# 値上げスクショ（2枚）を横並びで表示
neage_imgs = [
    "https://github.com/Naobro/fp/blob/main/assets/neage.jpg?raw=1",
    "https://github.com/Naobro/fp/blob/main/assets/neage1.jpg?raw=1",
]
cols = st.columns(len(neage_imgs))
for col, url in zip(cols, neage_imgs):
    col.image(url, use_container_width=True)

# 補足注釈（小さく・グレーで）
st.markdown(
    """
    <div style="color:#6b7280; font-size:12px; margin-top:4px;">
      ※ 実際に家賃の値上げ告知は各所で増えています。
    </div>
    """,
    unsafe_allow_html=True
)
# 3) 決定的な違い：団信（20万円ケースの具体比較）
st.markdown(
    """
    ### 団信がある“購入”と、団信がない“賃貸”の決定的な差
    <div style="display:flex; gap:12px; flex-wrap:wrap;">
      <div style="flex:1 1 320px; border:1px solid #e5e7eb; border-radius:12px; padding:14px;">
        <div style="font-weight:800; color:#0B4FA0; margin-bottom:6px;">住宅ローン 20万円／月（購入）</div>
        <ul style="margin:0 0 0 18px;">
          <li><b>団体信用生命保険（団信）</b>：万一のときは<strong>残債=0</strong>。</li>
          <li><b>がん団信</b>：診断・手術等で<strong>完済扱い</strong>となる商品も。</li>
          <li><b>就業不能・失業特約</b>：一定期間の返済免除で立て直し可。</li>
          <li>どうしても厳しい時は<strong>売却</strong>という選択肢（出口）も持てる。</li>
        </ul>
      </div>
      <div style="flex:1 1 320px; border:1px solid #e5e7eb; border-radius:12px; padding:14px;">
        <div style="font-weight:800; color:#7a1f1f; margin-bottom:6px;">家賃 20万円／月（賃貸）</div>
        <ul style="margin:0 0 0 18px;">
          <li>ご主人にもしもの事があっても、<b>家賃は0円にならない</b>。</li>
          <li>収入が落ちても、<b>家賃は待ってくれない</b>。</li>
          <li>結局、<b>払えないなら安い・狭い部屋へ住み替え</b></li>
          <li><b>資産は何も残らない</b>（ずっと掛け捨て）。</li>
        </ul>
      </div>
    </div>
    <div style="margin-top:6px; color:#6b7280; font-size:12px;">
      ※ 団信・特約の適用条件や保障範囲は商品・銀行により異なります。個別に最新の約款をご確認ください。
    </div>
    """,
    unsafe_allow_html=True
)
# 団信の強調テキスト
st.markdown(
    """
    <div style="font-weight:800; color:#111827; font-size:18px; margin:6px 0 2px;">
      団信＝“家族の暮らし”を守る仕組み。購入だから持てる安心。
    </div>
    """,
    unsafe_allow_html=True
)

# 団信の画像表示
danshin_img_url = "https://github.com/Naobro/fp/blob/main/assets/danshin.PNG?raw=1"
st.image(
    danshin_img_url,
    use_container_width=True
)

# 4) 100%確実な事実（強調帯）
st.markdown(
    """
    <div style="background:#E6F4EA;border:1px solid #34A853;border-radius:10px;padding:14px 16px; font-weight:700; text-align:center;">
      <span style="font-size:18px;">100% 確実な事実：</span>
      家賃を10年・20年払っても、<b>あなたの資産は増えません</b>。<br>
      増えるのは、<b>大家さんの資産だけ</b>です。社宅等の税務メリットがあっても、家賃そのものは<b>資産化しません</b>。
      <br>購入は、自分が借主の不動産投資と同じ
    </div>
    """,
    unsafe_allow_html=True
)
import streamlit as st

st.set_page_config(page_title="GitHub MP4 再生", layout="centered")
st.title("🎬 富裕層の考え方")

# GitHub blob URLをrawに変換
video_url = "https://raw.githubusercontent.com/Naobro/fp/main/assets/huyu.MP4"

# Streamlit標準プレーヤーで再生
st.video(video_url)
# 5) 数字で現実を見る（過去→現在の結果）
st.markdown(
    """
    中古マンション（70㎡目安）  
    ・東京都：2014年 約3,813万 → 2023年 約6,423万（<b>+約68.5%</b>）  
    ・23区　：2014年 約4,203万 → 2023年 約7,055万（<b>+約67.9%</b>）  
    新築→築10年（60㎡）指数：23区平均で <b>約1.5倍（146.8%）</b>  
    ・例：目黒区は <b>約2.21倍</b> と突出（渋谷・品川なども高伸長）  
    上昇額：東京都 <b>+約2,331万</b>／23区 <b>+約2,545万</b>（10年前比）  
    土地（坪単価）：東京都 <b>+約33.4%</b>（例：103万→137万/坪）  
    波及：都心5区だけでなく、<b>武蔵野・三鷹・調布</b>など周辺＆<b>埼玉・千葉・神奈川</b>人気エリアにも広がる
    """,
    unsafe_allow_html=True
)


# 6) 「待つ」シナリオの検証（オリ後／生産緑地）
st.markdown(
    """
    ### 「下がるまで待つ」は本当に正解？
    オリンピック前には、「オリンピック後に下がるから今は待ちます」というお客さんが多かったです。

    - 「オリンピック後は下がる」「生産緑地で暴落」——<b>結果、その予想は外れたケースが多い</b>。  
      制度設計・需給調整により、<b>暴落は回避</b>され、価格は<b>堅調〜上昇</b>が継続。  
      例：練馬区・大泉学園／世田谷区・千歳烏山などでは、2019〜2025年で<b>年数%上昇</b>の報告も。  
    - 海外目線では東京は<b>まだ安い</b>と映り、海外資金の需要も底堅い。
    """,
    unsafe_allow_html=True
)

# テキスト表示
st.markdown("アジア主要都市の都心マンション価格と比較しても、東京はまだ割安感があるという見方")

# 画像表示
try:
    st.image(asia_img, use_container_width=True)
except Exception:
    pass
# 7) 結論＆行動（FP→予算確定→事前審査）
st.markdown(
    """
    <div style="background:#EEF6FF;border:1px solid #BBD7FF;border-radius:10px;padding:12px 14px;">
      <b>結論：</b><br>
      未来は不確実。でも、<b>見える化</b>と<b>備え</b>で不安は小さくできる。<br><br>
      <b>次の一歩</b>：<br>
      1) お金のプロ（FP）とライフプランニング → <b>“無理なく返せる額”</b>を確定<br>
      2) <b>事前審査</b>で即動ける体制に（良い物件を<b>逃さない</b>）
    </div>
    """,
    unsafe_allow_html=True
)
import streamlit as st

# ✅ いちばん上で wide にする
st.set_page_config(page_title="理想の住まい探し", layout="wide", initial_sidebar_state="expanded")

# 万一どこかで幅を細くするCSSを入れていたら削除する（例）
# st.markdown("<style>.block-container{max-width:900px !important}</style>", unsafe_allow_html=True)
# ↑こういうCSSがあればコメントアウト/削除してください

st.divider()
# ============== phase① 条件整理 ==============
st.subheader("phase③ 条件整理")
st.divider()
st.subheader("5W2Hで理想の住まい探しを整理しよう")
st.markdown(
    """
- **Why（なぜ）:** なぜ購入を検討していますか？（例：賃貸脱却、子育て環境、資産形成）
- **When（いつ）:** いつまでに購入したいですか？
- **Where（どこで）:** どのエリアでお探しですか？
- **Who（誰が）:** ご家族構成や購入する方は？
- **What（何を）:** どんな物件を希望していますか？
- **How（どのように）:** どんな購入方法をお考えですか？（ローンの利用/頭金の有無/リノベ希望など）
- **How much（いくらで）:** ご予算や資金計画は？
"""
)
st.info("これらの項目を一緒に整理して、理想の住まい探しをサポートします！")

# ▼▼▼ お問い合わせリンク（純正UIを使用：スマホでも安定） ▼▼▼
st.divider()
st.subheader("📩 お問い合わせ")
# Streamlit 1.31+ 推奨：st.link_button（target=_blankとして扱われる）
st.link_button(
    "お問い合わせはこちら",
    "https://docs.google.com/forms/d/e/1FAIpQLSdbG6xqziJWaKf9fBK8uvsrHBMKibCaRadE7qShR3Nl6Cv8Kg/viewform?usp=pp_url",
    type="primary",
)

st.divider()
st.subheader("便利ツールへジャンプ")
tools = {
    "物件検索": "https://picks-agent.terass.com/search/mansion",
    "住宅ローン チェッカー": "https://loan-checker.jp/loan",
}
# 2列でボタン表示（スマホは1列にフォールバック）
cols = st.columns(2)
i = 0
for label, url in tools.items():
    with cols[i % 2]:
        st.link_button(label, url)
    i += 1
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
