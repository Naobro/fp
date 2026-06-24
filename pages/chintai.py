import streamlit as st
from pathlib import Path

# ---- 画像フォルダのパスを自動で組み立てる ----
# このファイル(chintai.py)は pages/ の中にあるので、1つ上がリポジトリのルート
ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

def img(name: str) -> str:
    return str(ASSETS / name)

# ---- ページ設定 ----
st.set_page_config(page_title="賃貸の末路", page_icon="🏠", layout="wide")

# ---- 簡単なスタイル（POPな色味） ----
st.markdown("""
<style>
.big-title{font-size:54px;font-weight:900;color:#1556c0;line-height:1.25;}
.accent{color:#ff5a3c;}
.lead{font-size:22px;line-height:1.9;color:#3a4356;font-weight:600;}
.section-label{display:inline-block;background:#ff5a3c;color:#fff;font-weight:800;
  font-size:16px;padding:5px 16px;border-radius:20px;margin-bottom:10px;}
.bias-title{font-size:30px;font-weight:900;color:#1556c0;}
.note{font-size:14px;color:#a99684;}
hr{border:none;border-top:2px dotted #ffe0cf;margin:34px 0;}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 表紙
# ============================================================
st.markdown('<div class="big-title">賃貸の<span class="accent">末路</span></div>', unsafe_allow_html=True)
st.markdown("""
<p class="lead">
今はとりあえず賃貸でいい——<br>
その先送りが、35年後のあなたを追い詰める。<br>
家賃も、金利・不動産価格と連動します。<br>
高齢者は<span class="accent">部屋を借りられない</span>時代へ。
</p>
""", unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ============================================================
# 01 問題提起
# ============================================================
st.markdown('<div class="section-label">問いかけ</div>', unsafe_allow_html=True)
st.header("「今はとりあえず賃貸でいい」——本当に、それでいいのでしょうか？")
c1, c2 = st.columns(2)
with c1:
    st.subheader("あなたは将来を見据えていますか？")
    st.write("5年後・10年後の「なんとなく」ではなく、65歳から先の住まいの計画はできていますか？")
with c2:
    st.subheader("先送りしていませんか？")
    st.write("家を買うか借りるかは「好み」の問題ではありません。数千万円単位の意思決定を、先送りしているだけかもしれません。")
st.info("なぜ多くの人が「先送り」してしまうのか？ その正体は、4つの「心理のワナ」にあります。")

st.markdown("<hr>", unsafe_allow_html=True)

# ============================================================
# 02-05 4つのバイアス
# ============================================================
st.markdown('<div class="section-label">行動心理学の4つのワナ</div>', unsafe_allow_html=True)

st.markdown('<div class="bias-title">① 現状維持バイアス 〜「今のままでいいかも」が損を生む〜</div>', unsafe_allow_html=True)
st.write("**【定義】** 変化より「今のまま」を無意識に選んでしまう心の働き。変化＝不安（軽い）、現状＝安心（重い）と脳が錯覚する。")
st.write("**あるある：** 引越しが面倒で家賃が高い今の家に住み続ける／相場より高い物件で妥協／検討しても白紙に戻す。")
st.success("💡 「今の家に住み続けるコスト」を数字で計算\n\n"
           "今の家賃15万円 × 6年 ＝ **1,080万円**　／　今の家賃15万円 × 35年 ＝ **6,300万円**\n\n"
           "家賃は、何も残りません。")

st.markdown('<div class="bias-title">② 損失回避バイアス 〜「損したくない」が一番の損〜</div>', unsafe_allow_html=True)
st.write("**【定義】** 同じ金額でも「得」より「損」を強く嫌がる心理。損する痛みは、得する喜びの“2倍”重い。")
st.write("**あるある：** 値下がりが怖くて買い時を逃す／「もう少し下がるかも」と待ち続け好物件を逃す／契約直前に白紙撤回。")
st.success("💡 「買わないことの損失」も同じ重さで計算する。まずは相談から、現状把握と将来の見通しを整理する。")

st.markdown('<div class="bias-title">③ 選択のパラドックス 〜選択肢が多いほど決められない〜</div>', unsafe_allow_html=True)
st.write("**【定義】** 選択肢が増えるほど、迷い・後悔が増える心理現象。たくさん見るほど満足度は下がる。")
st.write("**あるある：** 100件以上見て疲れて止まる／「もっと良い物件があるはず」と感じる／決めた後も後悔。")
st.success("💡 100%の物件はない。最初に「譲れない条件3つ」を決める。\n\n"
           "予算 × エリア × スペック（広さ・築年数）のうち2つが確定すると、答えは出る。\n\n"
           "安くて人気エリアで駅近・築浅、はない。")

st.markdown('<div class="bias-title">④ 確証バイアス 〜見たいものだけを見てしまう〜</div>', unsafe_allow_html=True)
st.write("**【定義】** 自分の考えに合う情報だけを集め、反する情報を無視する傾向。「いいな」と思った瞬間、欠点が見えなくなる。")
st.write("**あるある：** 良い口コミだけ信じる／不利な条件を軽く見積もる／営業の「お得です」を鵜呑みに。")
st.success("💡 あえて「この物件のデメリットは？」と、信頼できる第三者（エージェント）に聞く。")

st.markdown("<hr>", unsafe_allow_html=True)

# ============================================================
# 06 現実① 家賃高騰
# ============================================================
st.markdown('<div class="section-label">現実を見よ ①</div>', unsafe_allow_html=True)
st.header("家賃は「上がり続けて」いる。")
st.write("2026年、ついに都内ワンルームの平均家賃が11万円を突破。東京23区シングル向けは21ヶ月連続で最高値を更新しています。")
c1, c2 = st.columns(2)
with c1:
    st.image(img("chintokyo.png"), use_container_width=True)
with c2:
    st.metric("東京23区 シングル向け 平均家賃", "11万円超", "+12.0%（前年同月比）")
    st.write("21ヶ月連続 最高値更新。賃貸は「変動費」。一生、値上げのリスクを抱え続けることになります。")
st.markdown('<p class="note">出典：at home / 日本経済新聞 2026年</p>', unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ============================================================
# 07 現実② 20年後試算
# ============================================================
st.markdown('<div class="section-label">現実を見よ ②</div>', unsafe_allow_html=True)
st.header("20年前・現在・20年後、あなたの住居費はどうなる？")
st.write("日銀の物価安定目標は年2%。20年後、都内ワンルームは16万円に。年金生活で家賃を払い続けられますか？")
st.image(img("20.png"), use_container_width=True)
st.markdown('<p class="note">※日本銀行 物価安定目標 年2%で試算</p>', unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ============================================================
# 08 先送り1年のコスト
# ============================================================
st.markdown('<div class="section-label">先送りのコスト</div>', unsafe_allow_html=True)
st.header("その「1年待とう」が、約312万円を捨てている。")
st.write("1年待つと、家賃は掛け捨て（戻ってこない）。さらに、住宅ローンなら積み上がっていたはずの「元金（資産）」も得られません。この2つは別物なので、合算した損失になります。")
st.image(img("saki.png"), use_container_width=True)
st.markdown('<p class="note">※金利0.9%・35年（元利均等）での概算。不動産価格・金利は2026年時点で上昇局面（今後の継続を保証するものではありません）</p>', unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ============================================================
# 09 老後賃貸の3つの末路
# ============================================================
st.markdown('<div class="section-label">老後 賃貸の「3つの末路」</div>', unsafe_allow_html=True)
st.header("歳をとってからの賃貸には、逃れられない3つのリスクがある。")
c1, c2 = st.columns([1.3, 1])
with c1:
    st.markdown("**① 年齢を理由に「契約できない」**")
    st.write("高齢者の約3人に1人が、年齢を理由に入居を断られた経験あり（R65不動産 2025年調査）。")
    st.markdown("**② 退去トラブル・高額な請求**")
    st.write("借地借家法で借主は守られるが、現実には高額な原状回復費の請求や、強引な立ち退き（地上げ・放火事件まで）も発生。")
    st.markdown("**③ 「終の住処」の安心がない**")
    st.write("築浅を借りても、80歳で建物取り壊しになれば次は借りにくい。一生、家賃と更新の不安がつきまとう。")
with c2:
    st.image(img("rougo.jpg"), use_container_width=True)
    st.image(img("jiage.jpg"), use_container_width=True)
st.markdown('<p class="note">出典：テレ朝news / R65不動産調査 2025</p>', unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ============================================================
# 10 退去トラブル実例
# ============================================================
st.markdown('<div class="section-label">末路② リアルな「退去トラブル」</div>', unsafe_allow_html=True)
st.header("「綺麗に使っていたのに」——退去費用100万円超の現実。")
st.write("退去時の原状回復費は、借主にとって“言い値”になりやすい。SNSには、解体処分費・クロス全面張替で100万円超を請求された声が溢れています。")
c1, c2 = st.columns(2)
with c1:
    st.image(img("100.jpg"), use_container_width=True)
    st.caption("マンション退去：請求額 ¥1,038,156")
with c2:
    st.image(img("taikyo.jpg"), use_container_width=True)
    st.caption("戸建て6年半：精算額 ¥307,900")
st.warning("賃貸は「住み終わり」にも、まとまったお金が出ていく。")

st.markdown("<hr>", unsafe_allow_html=True)

# ============================================================
# 11 必要資金 ＋ シミュレーション
# ============================================================
st.markdown('<div class="section-label">末路③ 数字で見る「老後の家賃」</div>', unsafe_allow_html=True)
st.header("老後2000万円問題は、「持ち家前提」で計算されている。")
st.write("総務省の家計調査では、高齢者の住居費はわずか月1.8万円。持ち家率94%を前提とした数字です。賃貸なら、ここに家賃がまるごと上乗せされます。")
st.image(img("rougosoumu.png"), use_container_width=True)

st.subheader("🧮 老後の必要資金シミュレーション")
st.write("あなたの想定家賃と、老後に賃貸で暮らす年数を入れてみてください。")
sc1, sc2 = st.columns(2)
with sc1:
    rent = st.slider("老後の想定家賃（万円/月）", 5, 25, 16)
with sc2:
    years = st.slider("老後に賃貸で暮らす年数", 10, 35, 20)

assumed_housing = 1.8  # 持ち家前提の住居費（万円/月）
monthly_gap = rent - assumed_housing
yearly_gap = monthly_gap * 12
total_gap = yearly_gap * years
total_need = 2000 + total_gap  # 老後2000万円 + 家賃分

m1, m2, m3 = st.columns(3)
m1.metric("毎月の差額", f"▲{monthly_gap:.1f}万円")
m2.metric(f"{years}年間の家賃分の不足", f"▲{total_gap:,.0f}万円")
m3.metric("老後に必要な総額の目安", f"約{total_need:,.0f}万円")
st.caption("※持ち家前提の住居費 月1.8万円との差額で試算。老後2,000万円問題に上乗せした概算です。")

st.markdown("<hr>", unsafe_allow_html=True)

# ============================================================
# 12 5000万円試算
# ============================================================
st.markdown('<div class="section-label">突きつけられる現実</div>', unsafe_allow_html=True)
st.header("30歳の人が、65歳までに5,000万円を貯めるには？")
st.write("「一生賃貸でいい」を選ぶなら、これだけの準備を“今から”始める必要があります。")
st.table({
    "方法": ["💰 貯金だけで貯める", "📈 積立投資（利回り5%想定）", "35年間 続けると"],
    "毎月の額／結果": ["月 12万円ずつ", "月 4.5万円ずつ", "≒ 5,000万円"],
})
st.write("一生賃貸派が取れる道は、結局この2つだけ——① 老後、生活費の安い地方へ移住する／② それまでに資産を作りきる。"
         "**どちらにせよ、「今からの準備」が運命を分けます。**")
st.markdown('<p class="note">※利回り5%は複利運用の試算。元本保証ではありません</p>', unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ============================================================
# 13 地方移住
# ============================================================
st.markdown('<div class="section-label">道① 地方移住という選択</div>', unsafe_allow_html=True)
st.header("家賃を抑えたいなら、住む「場所」を変える手もある。")
st.write("東京23区のワンルームが11万円超に対し、地方なら同等の部屋が大幅に安く借りられます。ただし、仕事・医療・人間関係まで含めた生活設計が前提です。")
st.image(img("chin.png"), use_container_width=True)
st.markdown('<p class="note">出典：at home 全国家賃相場</p>', unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ============================================================
# 14 買い替え実例
# ============================================================
st.markdown('<div class="section-label">道② 資産を作る「買い替え」実例</div>', unsafe_allow_html=True)
st.header("買うと、住みながら資産が育つ。")
st.write("買うことは「消費」ではなく「資産形成」。下は、私が担当したお客様の例です。")
st.table({
    "タイミング": ["2019年 購入（タワマン60㎡）", "2025年 売却（築6年・ペアローン3,000万円利用）", "売却益（譲渡所得税 0円）"],
    "金額": ["約 6,000万円", "1億1,800万円", "＋5,800万円"],
})
c1, c2 = st.columns(2)
with c1:
    st.markdown("**次の住まいへ（70㎡・築2年へ買い替え）**")
    st.write("物件価格7,000万円。住宅ローン約19万円/月 ＋ 管理費等3万円/月 ＝ 住居費 約22万円/月。")
with c2:
    st.markdown("**手元の5,800万円を運用すると**")
    st.write("利回り5%で年約290万円（≒月24万円）の収入。住居費をまかなえる計算に。元本5,800万円は残り、ローン返済後は物件も手元に残る。")
st.markdown('<p class="note">※特定事例の概算。価格・税・利回りは物件と市況により異なります</p>', unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ============================================================
# 15 アフォーダブル住宅の誤解
# ============================================================
st.markdown('<div class="section-label">よくある誤解</div>', unsafe_allow_html=True)
st.header("「アフォーダブル住宅があるから大丈夫」——その安心は、12年で終わる。")
st.write("対象は子育て・新婚世帯に限られ、減額は最大12年で終了。老後はそもそも対象外です。")
c1, c2 = st.columns(2)
with c1:
    st.image(img("afo.jpg"), use_container_width=True)
with c2:
    st.markdown("**この制度の「落とし穴」**")
    st.write("・対象は子育て・新婚世帯のみ\n\n・減額は最大12年で終了\n\n・老後は対象外、使えない")
    st.write("**だから——制度に頼れない老後に備え、現役のうちに「終の住処」を確保しておく必要があるのです。**")
st.markdown('<p class="note">出典：東京都 / JKK東京 2026年</p>', unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ============================================================
# 16 CTA
# ============================================================
st.markdown('<div class="section-label">結論</div>', unsafe_allow_html=True)
c1, c2 = st.columns([1, 1.4])
with c1:
    st.image(img("pro.JPG"), use_container_width=True)
    st.markdown("### 不動産エージェント 西山")
with c2:
    st.header("まずは、相談から始めましょう。")
    st.write("大事なのは、今の現状を正しく把握すること。そこからどう進めるかは、私が一緒に整理します。")
    st.markdown("**1. 現状を把握する**／今の生活コストを見直す")
    st.markdown("**2. 将来の見通しを確認**／年金はいくら？ 今のままで大丈夫？")
    st.markdown("**3. 今、何をすべきかを整理**／必要なら次の一手をディレクション")
    st.success("「この物件のデメリットは？」その問いに、正直に答えるのが私の仕事です。先送りを、今日で終わらせましょう。")
    st.caption("※ライフプランニングはお金のプロ（FP）と連携。私は不動産の視点から最適な進め方をご案内します。")

