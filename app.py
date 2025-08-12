import os
from datetime import datetime
import tempfile
from pathlib import Path

import streamlit as st
from fpdf import FPDF

# ============================================
# 0) URLにclientがあれば直接お客様ページへ（PINは見ない）
# ============================================
q = st.query_params
if q.get("client"):
    st.switch_page("pages/2_client_portal.py")  # ← 実ファイル名に合わせる（今はこれでOK）

# ============================================
# 1) ページ設定（このページで1回だけ）
# ============================================
st.set_page_config(
    page_title="不動産エージェント NAOKI",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================
# 2) 共通ユーティリティ／前提チェック
# ============================================
# フォント（日本語TTF）の存在確認
FONT_PATH = os.path.join("fonts", "NotoSansJP-Regular.ttf")
if not os.path.exists(FONT_PATH):
    st.error(f"フォント {FONT_PATH} が見つかりません。'fonts' フォルダに NotoSansJP-Regular.ttf を配置してください。")
    st.stop()

def gh_raw(url: str) -> str:
    """GitHubの blob URL → raw URL 変換"""
    return url.replace("https://github.com/", "https://raw.githubusercontent.com/").replace("/blob/", "/")

# ============================================
# 3) ヒーロー
# ============================================
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
        ①不安の解消 ➡️ ②ライフプランニング ➡️ ③予算確定 ➡️ ④条件整理 ➡️ ⑤内見
    </div>
    """,
    unsafe_allow_html=True
)
st.header("一番重要な事は良い物件と出会った時に即決できる様に、条件整理・資金準備をしておく事")

st.divider()
st.subheader("不動産購入の流れ")
st.markdown("[相談から引き渡しまで](https://naobro.github.io/fp/pages/flow_compressed.pdf)")
st.markdown("[注文住宅　土地](https://naobro.github.io/fp/pages/tochi.pdf)")
st.subheader("不動産売却の流れ")
st.markdown("[不動産売却資料](https://naobro.github.io/fp/pages/sale.pdf)")
st.divider()

# ============================================
# 4) phase① 不安の解消
# ============================================
st.subheader("phase①　不安の解消")

huan_img = "https://github.com/Naobro/fp/blob/main/assets/huan.png"
st.image(gh_raw(huan_img), use_container_width=True)

st.markdown("## 🏠 不動産購入時の不安ランキング（調査対象：500人）")

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

st.markdown("[📄 近隣調査　トナリスク](https://naobro.github.io/fp/pages/tonari.pdf)")

st.info("“不安の解消は可視化して、専門家　データで解消　Next：**ライフプラン　予算** 。")

# ============================================
# 5) phase② ライフプラン／予算
# ============================================
st.subheader("phase②　ライフプラン　予算")

fp_img = "https://github.com/Naobro/fp/blob/main/assets/Fp.png"
st.image(gh_raw(fp_img), use_container_width=True)

st.divider()
st.header("フェーズ② ライフプラン／予算")

huan_img   = "https://naobro.github.io/fp/assets/huan.png"
danshin_img= "https://naobro.github.io/fp/assets/danshin.png"
neage_img  = "https://naobro.github.io/fp/assets/neage.jpeg"
asia_img   = "https://naobro.github.io/fp/assets/sekai.jpg"

st.markdown("## 💰 不動産購入時の不安ランキング　圧倒的　第1位🥇　【お金】")
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

st.markdown(
    """
    ### 住宅ローンが払えるか不安な人　それって、家賃なら払えるんですか？
    - 住宅ローンが不安 → でも<strong>同額の家賃</strong>なら「払える」と思っていませんか？  
    - しかも将来は<strong>インフレにより、お金の価値が下がるので、実質的な返済負担は軽くなる</strong>が、賃貸は<strong>逆に家賃アップの可能性大</strong>。
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div style="font-weight:900; color:#000000; font-size:22px; margin:12px 0 8px;">
      家賃は上がる。あなたの収入が下がっても家賃は下がらない。
    </div>
    """,
    unsafe_allow_html=True
)

neage_imgs = [
    "https://github.com/Naobro/fp/blob/main/assets/neage.jpg?raw=1",
    "https://github.com/Naobro/fp/blob/main/assets/neage1.jpg?raw=1",
]
cols = st.columns(len(neage_imgs))
for col, url in zip(cols, neage_imgs):
    col.image(url, use_container_width=True)

st.markdown(
    """
    <div style="color:#6b7280; font-size:12px; margin-top:4px;">
      ※ 実際に家賃の値上げ告知は各所で増えています。
    </div>
    """,
    unsafe_allow_html=True
)

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

st.markdown(
    """
    <div style="font-weight:800; color:#111827; font-size:18px; margin:6px 0 2px;">
      団信＝“家族の暮らし”を守る仕組み。購入だから持てる安心。
    </div>
    """,
    unsafe_allow_html=True
)

st.image("https://github.com/Naobro/fp/blob/main/assets/danshin.PNG?raw=1", use_container_width=True)

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

# （※ set_page_config の重複はここ以外に置かない）
st.title("🎬 富裕層の考え方")
st.video("https://raw.githubusercontent.com/Naobro/fp/main/assets/huyu.MP4")

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

st.markdown("アジア主要都市の都心マンション価格と比較しても、東京はまだ割安感があるという見方")
try:
    st.image(asia_img, use_container_width=True)
except Exception:
    pass

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

st.divider()
# ============================================
# 6) phase③ 条件整理
# ============================================
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

st.divider()
st.subheader("📩 お問い合わせ")
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
cols = st.columns(2)
for i, (label, url) in enumerate(tools.items()):
    with cols[i % 2]:
        st.link_button(label, url)
for name, url in tools.items():
    st.markdown(f'<a href="{url}" target="_blank">{name}</a>', unsafe_allow_html=True)

st.divider()

# ============================================
# 7) ヒアリングフォーム ＋ PDF出力
# ============================================
st.subheader("ヒアリング内容")

TO_EMAIL_DEFAULT = "naoki.nishiyama@terass.com"
base_defaults = {
    "name": "", "now_area": "", "now_years": 5, "is_owner": "賃貸",
    "now_rent": 10, "family": "",
    "husband_company": "", "husband_income": 0, "husband_service_years": 3,
    "wife_company": "", "wife_income": 0, "wife_service_years": 3,
    "sat_point": "", "search_status": "", "why_buy": "", "task": "",
    "anxiety": "", "rent_vs_buy": "", "other_trouble": "", "effect": "",
    "forecast": "", "event_effect": "", "missed_timing": "", "ideal_life": "",
    "solve_feeling": "", "goal": "", "important": "",
    "must": "", "want": "", "ng": "", "other_agent": "", "why_terass": "",
    "housing_cost": 10,
    "husband_commute": "", "wife_commute": "",
    "sat_price": 3, "sat_location": 3, "sat_size": 3, "sat_age": 3, "sat_spec": 3,
    "dissat_free": "",
    "self_fund": "", "other_debt": "", "gift_support": "",
    "w_why": "", "w_when": "", "w_where": "", "w_who": "", "w_what": "", "w_how": "", "w_howmuch": "", "w_free": "",
    "prio_price": 3, "prio_location": 3, "prio_size": 3, "prio_age": 3, "prio_spec": 3,
    "spec_parking": False, "spec_bicycle": False, "spec_ev": False, "spec_pet": False,
    "spec_barrierfree": False, "spec_security": False, "spec_disaster": False,
    "spec_mgmt_good": False, "spec_fee_ok": False, "spec_free": "",
    "contact_pref": "", "share_method": "", "pdf_recipient": TO_EMAIL_DEFAULT,
}

if "hearing_data" not in st.session_state:
    st.session_state["hearing_data"] = base_defaults.copy()
else:
    for k, v in base_defaults.items():
        st.session_state["hearing_data"].setdefault(k, v)
    if not st.session_state["hearing_data"].get("housing_cost"):
        st.session_state["hearing_data"]["housing_cost"] = st.session_state["hearing_data"].get("now_rent", 0)

data = st.session_state["hearing_data"]

with st.form("hearing_form", clear_on_submit=False):
    st.markdown("#### 1) 現状把握（基礎）")
    c1, c2, c3 = st.columns(3)
    with c1:
        data["name"]      = st.text_input("お名前", value=data["name"])
        data["now_area"]  = st.text_input("現在の居住エリア・駅", value=data["now_area"])
    with c2:
        data["now_years"] = st.number_input("居住年数（年）", min_value=0, max_value=100, value=int(data["now_years"]))
        data["is_owner"]  = st.selectbox("持ち家・賃貸", ["賃貸", "持ち家"], index=0 if data["is_owner"]=="賃貸" else 1)
    with c3:
        data["housing_cost"] = st.number_input("住居費（万円/月）", min_value=0, max_value=200, value=int(data["housing_cost"]))
    data["family"] = st.text_input("ご家族構成（人数・年齢・将来予定）", value=data["family"])

    st.divider()

    st.markdown("#### 2) 現在の住まい（満足・不満）")
    data["sat_point"] = st.text_area("現在の住宅の満足点（自由入力）", value=data["sat_point"])
    sc1, sc2, sc3, sc4, sc5 = st.columns(5)
    with sc1:
        data["sat_price"] = st.slider("満足度：価格（1=不満／5=満足）", 1, 5, int(data["sat_price"]))
    with sc2:
        data["sat_location"] = st.slider("満足度：立地（1=不満／5=満足）", 1, 5, int(data["sat_location"]))
    with sc3:
        data["sat_size"] = st.slider("満足度：広さ（1=不満／5=満足）", 1, 5, int(data["sat_size"]))
    with sc4:
        data["sat_age"] = st.slider("満足度：築年数（1=不満／5=満足）", 1, 5, int(data["sat_age"]))
    with sc5:
        data["sat_spec"] = st.slider("満足度：スペック（1=不満／5=満足）", 1, 5, int(data["sat_spec"]))
    sat_total = int(data["sat_price"]) + int(data["sat_location"]) + int(data["sat_size"]) + int(data["sat_age"]) + int(data["sat_spec"])
    st.caption(f"満足度スコア合計：**{sat_total} / 25**（低いほど不満が大きい）")
    data["dissat_free"] = st.text_area("不満な点（自由入力）", value=data["dissat_free"])

    st.divider()

    st.markdown("#### 3) 収入・勤務（夫婦2名）")
    st.markdown("**ご主人**")
    hc1, hc2, hc3 = st.columns(3)
    with hc1:
        data["husband_company"] = st.text_input("勤務先・勤務地（ご主人）", value=data["husband_company"])
    with hc2:
        data["husband_income"]  = st.number_input("年収（ご主人・万円）", min_value=0, max_value=10000, value=int(data["husband_income"]))
    with hc3:
        data["husband_service_years"] = st.number_input("勤続年数（ご主人・年）", min_value=0, max_value=50, value=int(data["husband_service_years"]))
    data["husband_commute"] = st.text_input("通勤状況（在宅頻度／出社曜日・時間）〈ご主人〉", value=data["husband_commute"])

    st.markdown("**奥様**")
    wc1, wc2, wc3 = st.columns(3)
    with wc1:
        data["wife_company"] = st.text_input("勤務先・勤務地（奥様）", value=data["wife_company"])
    with wc2:
        data["wife_income"]  = st.number_input("年収（奥様・万円）", min_value=0, max_value=10000, value=int(data["wife_income"]))
    with wc3:
        data["wife_service_years"] = st.number_input("勤続年数（奥様・年）", min_value=0, max_value=50, value=int(data["wife_service_years"]))
    data["wife_commute"] = st.text_input("通勤状況（在宅頻度／出社曜日・時間）〈奥様〉", value=data["wife_commute"])

    st.divider()

    st.markdown("#### 4) 資金計画")
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        data["self_fund"] = st.text_input("自己資金（頭金＋諸費用の目安）", value=data["self_fund"])
    with fc2:
        data["other_debt"] = st.text_input("借入（自動車ローン等）", value=data["other_debt"])
    with fc3:
        data["gift_support"] = st.text_input("相続・贈与・援助（予定額／有無／時期）", value=data["gift_support"])

    st.divider()

    st.markdown("#### 5) ライフイベント・家族計画")
    data["event_effect"] = st.text_area("出産・進学・転勤・同居 等の予定／学区・保育・医療の希望", value=data["event_effect"])

    st.divider()

    st.markdown("#### 6) 5W2H（購入計画）")
    data["w_why"]     = st.text_input("Why（なぜ）：購入理由", value=data["w_why"])
    data["w_when"]    = st.text_input("When（いつ）：購入／入居タイミング", value=data["w_when"])
    data["w_where"]   = st.text_input("Where（どこで）：希望エリア・沿線", value=data["w_where"])
    data["w_who"]     = st.text_input("Who（誰が）：居住メンバー", value=data["w_who"])
    data["w_what"]    = st.text_input("What（何を）：種別・広さ・築年数・階数・設備", value=data["w_what"])
    data["w_how"]     = st.text_input("How（どう買う）：ローン方針・頭金の考え方", value=data["w_how"])
    data["w_howmuch"] = st.text_input("How much（いくら）：総予算／月返済の上限", value=data["w_howmuch"])
    data["w_free"]    = st.text_area("補足（自由入力）", value=data["w_free"])

    st.divider()

    st.markdown("#### 7) 希望条件の優先度")
    data["must"] = st.text_input("MUST条件（3つまで）", value=data["must"])
    data["want"] = st.text_area("WANT条件", value=data["want"])
    data["ng"]   = st.text_area("NG条件", value=data["ng"])

    st.markdown("**重要度のトレードオフ（1=最優先〜5）**")
    p1, p2, p3, p4, p5 = st.columns(5)
    with p1:
        data["prio_price"] = st.selectbox("価格", [1,2,3,4,5], index=[1,2,3,4,5].index(int(data["prio_price"])) if str(data["prio_price"]).isdigit() else 2)
    with p2:
        data["prio_location"] = st.selectbox("立地（資産性）", [1,2,3,4,5], index=[1,2,3,4,5].index(int(data["prio_location"])) if str(data["prio_location"]).isdigit() else 2)
    with p3:
        data["prio_size"] = st.selectbox("広さ", [1,2,3,4,5], index=[1,2,3,4,5].index(int(data["prio_size"])) if str(data["prio_size"]).isdigit() else 2)
    with p4:
        data["prio_age"] = st.selectbox("築年数", [1,2,3,4,5], index=[1,2,3,4,5].index(int(data["prio_age"])) if str(data["prio_age"]).isdigit() else 2)
    with p5:
        data["prio_spec"] = st.selectbox("スペック", [1,2,3,4,5], index=[1,2,3,4,5].index(int(data["prio_spec"])) if str(data["prio_spec"]).isdigit() else 2)

    st.markdown("#### 8) 物件スペック・住環境（チェック＋自由入力）")
    csp1, csp2, csp3, csp4, csp5 = st.columns(5)
    with csp1:
        data["spec_parking"] = st.checkbox("駐車場", value=bool(data["spec_parking"]))
        data["spec_bicycle"] = st.checkbox("駐輪", value=bool(data["spec_bicycle"]))
    with csp2:
        data["spec_ev"] = st.checkbox("エレベーター", value=bool(data["spec_ev"]))
        data["spec_pet"] = st.checkbox("ペット可", value=bool(data["spec_pet"]))
    with csp3:
        data["spec_barrierfree"] = st.checkbox("バリアフリー", value=bool(data["spec_barrierfree"]))
        data["spec_security"] = st.checkbox("防犯性（オートロック等）", value=bool(data["spec_security"]))
    with csp4:
        data["spec_disaster"] = st.checkbox("災害リスク許容", value=bool(data["spec_disaster"]))
        data["spec_mgmt_good"] = st.checkbox("管理状態が良好", value=bool(data["spec_mgmt_good"]))
    with csp5:
        data["spec_fee_ok"] = st.checkbox("管理費/修繕積立金 許容範囲内", value=bool(data["spec_fee_ok"]))
    data["spec_free"] = st.text_area("スペック補足（自由入力）", value=data["spec_free"])

    st.divider()

    st.markdown("#### 9) 他社相談状況")
    data["other_agent"] = st.text_input("他社への相談状況（有無・内容）", value=data["other_agent"])

    st.divider()

    st.markdown("#### 10) 連絡・共有")
    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        data["contact_pref"] = st.text_input("希望連絡手段・時間帯", value=data["contact_pref"])
    with cc2:
        data["share_method"] = st.text_input("資料共有（LINE／メール 等）", value=data["share_method"])
    with cc3:
        data["pdf_recipient"] = st.text_input("PDF送付先メール", value=data.get("pdf_recipient", TO_EMAIL_DEFAULT))

    submitted = st.form_submit_button("送信")

# ============================================
# 8) PDF生成（送信後）
# ============================================
if submitted:
    st.success("ご入力ありがとうございました！PDFを生成します。")

    import urllib.request

    REG_NAME = "NotoSansJP-Regular.ttf"
    BLD_NAME = "NotoSansJP-Bold.ttf"
    RAW_REG = "https://raw.githubusercontent.com/Naobro/fp/main/fonts/NotoSansJP-Regular.ttf"
    RAW_BLD = "https://raw.githubusercontent.com/Naobro/fp/main/fonts/NotoSansJP-Bold.ttf"

    def ensure_fonts_dir() -> Path:
        candidates = [
            Path(__file__).resolve().parent / "fonts",
            Path.cwd() / "fonts",
            Path("/mount/src/fp/fonts"),
            Path("/app/fonts"),
        ]
        for d in candidates:
            if (d / REG_NAME).exists() and (d / BLD_NAME).exists():
                return d.resolve()
        for d in candidates:
            if (d / REG_NAME).exists():
                try:
                    (d / BLD_NAME).write_bytes((d / REG_NAME).read_bytes())
                except Exception:
                    pass
                return d.resolve()
        tmp = Path(tempfile.mkdtemp(prefix="fonts_"))
        urllib.request.urlretrieve(RAW_REG, str(tmp / REG_NAME))
        try:
            urllib.request.urlretrieve(RAW_BLD, str(tmp / BLD_NAME))
        except Exception:
            (tmp / BLD_NAME).write_bytes((tmp / REG_NAME).read_bytes())
        return tmp.resolve()

    font_dir = ensure_fonts_dir()
    reg_path = font_dir / REG_NAME
    bld_path = font_dir / BLD_NAME
    if not reg_path.exists():
        st.error(f"日本語フォントが見つかりません: {reg_path}")
        st.stop()
    if not bld_path.exists():
        bld_path.write_bytes(reg_path.read_bytes())

    st.caption(f"Font dir: {font_dir}")
    st.caption(f"Use TTF: {reg_path.name} / {bld_path.name}")

    save_cwd = os.getcwd()
    os.chdir(str(font_dir))
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.add_font("NotoSansJP", "", reg_path.name, uni=True)
        pdf.add_font("NotoSansJP", "B", bld_path.name, uni=True)

        def title(t):
            pdf.set_font("NotoSansJP", "B", 14); pdf.cell(0, 10, t, 0, 1)
        def pair(label, val):
            pdf.set_font("NotoSansJP","B",11); pdf.multi_cell(0, 7, label)
            pdf.set_font("NotoSansJP","",11); pdf.multi_cell(0, 7, str(val) if val not in [None, ""] else "（未入力）")
            pdf.ln(1)

        pdf.set_font("NotoSansJP", "B", 16)
        pdf.cell(0, 10, "不動産ヒアリングシート", 0, 1, "C")
        pdf.set_font("NotoSansJP", "", 10)
        pdf.cell(0, 8, f"作成日時：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, "R")
        pdf.ln(2)

        title("1) 現状把握（基礎）")
        pair("お名前", data["name"])
        pair("現在の居住エリア・駅", data["now_area"])
        pair("居住年数（年）", data["now_years"])
        pair("種別（賃貸/持ち家）", data["is_owner"])
        pair("住居費（万円/月）", data["housing_cost"])
        pair("ご家族構成", data["family"])

        title("2) 現在の住まい（満足・不満）")
        pair("満足点", data["sat_point"])
        sat_total = int(data["sat_price"]) + int(data["sat_location"]) + int(data["sat_size"]) + int(data["sat_age"]) + int(data["sat_spec"])
        pair("満足度（価格/立地/広さ/築年数/スペック）合計", f"{data['sat_price']}/{data['sat_location']}/{data['sat_size']}/{data['sat_age']}/{data['sat_spec']}（計 {sat_total} / 25）")
        pair("不満な点", data["dissat_free"])

        title("3) 収入・勤務（夫婦2名）")
        pair("ご主人：勤務先・勤務地", data["husband_company"])
        pair("ご主人：年収（万円）／勤続（年）", f"{data['husband_income']}／{data['husband_service_years']}")
        pair("ご主人：通勤状況", data["husband_commute"])
        pair("奥様：勤務先・勤務地", data["wife_company"])
        pair("奥様：年収（万円）／勤続（年）", f"{data['wife_income']}／{data['wife_service_years']}")
        pair("奥様：通勤状況", data["wife_commute"])
        pair("世帯年収（万円）", (data.get("husband_income",0) or 0) + (data.get("wife_income",0) or 0))

        title("4) 資金計画")
        pair("自己資金（頭金＋諸費用）", data["self_fund"])
        pair("借入（自動車ローン等）", data["other_debt"])
        pair("相続・贈与・援助（予定額／有無／時期）", data["gift_support"])

        title("5) ライフイベント・家族計画")
        pair("予定／学区・保育・医療の希望", data["event_effect"])

        title("6) 5W2H（購入計画）")
        pair("Why", data["w_why"]); pair("When", data["w_when"]); pair("Where", data["w_where"])
        pair("Who", data["w_who"]); pair("What", data["w_what"]); pair("How", data["w_how"]); pair("How much", data["w_howmuch"])
        pair("補足", data["w_free"])

        title("7) 希望条件の優先度／物件スペック")
        pair("MUST", data["must"]); pair("WANT", data["want"]); pair("NG", data["ng"])
        pair("重要度（価格/立地/広さ/築年数/スペック）", f"{data['prio_price']}/{data['prio_location']}/{data['prio_size']}/{data['prio_age']}/{data['prio_spec']}")
        spec_list = []
        for k, label in [
            ("spec_parking","駐車場"), ("spec_bicycle","駐輪"), ("spec_ev","エレベーター"),
            ("spec_pet","ペット可"), ("spec_barrierfree","バリアフリー"), ("spec_security","防犯性"),
            ("spec_disaster","災害リスク許容"), ("spec_mgmt_good","管理良好"), ("spec_fee_ok","管理費/修繕積立金 許容")
        ]:
            if data.get(k):
                spec_list.append(label)
        pair("チェック項目", "・".join(spec_list) if spec_list else "（なし）")
        pair("スペック補足", data["spec_free"])

        title("8) 他社相談状況")
        pair("他社相談", data["other_agent"])

        title("9) 連絡・共有")
        pair("希望連絡手段・時間帯", data["contact_pref"])
        pair("資料共有", data["share_method"])
        pair("PDF送付先", data.get("pdf_recipient", TO_EMAIL_DEFAULT))

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            pdf.output(tmp_file.name)
            pdf_path = tmp_file.name
    except Exception as e:
        st.error("PDFの作成でエラーが発生しました（フォント取得/配置を確認してください）。")
        st.exception(e)
        os.chdir(save_cwd)
        st.stop()
    finally:
        os.chdir(save_cwd)

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    st.download_button("📄 PDFをダウンロード", data=pdf_bytes, file_name="hearing_sheet.pdf", mime="application/pdf")