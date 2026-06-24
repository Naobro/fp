import streamlit as st
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

def img(name: str) -> str:
    return str(ASSETS / name)

st.set_page_config(page_title="賃貸の末路", page_icon="🏠", layout="wide")

st.markdown("""
<style>
.big-title{font-size:54px;font-weight:900;color:#1556c0;line-height:1.25;}
.accent{color:#ff5a3c;}
.lead{font-size:22px;line-height:1.9;color:#3a4356;font-weight:600;}
.section-label{display:inline-block;background:#ff5a3c;color:#fff;font-weight:800;
  font-size:16px;padding:5px 16px;border-radius:20px;margin-bottom:10px;}
.bias-title{font-size:30px;font-weight:900;color:#1556c0;}
.note{font-size:14px;color:#a99684;}
.story{font-size:18px;line-height:1.9;color:#26324a;}
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
# 11 必要資金（読み物）
# ============================================================
st.markdown('<div class="section-label">末路③ 数字で見る「老後の家賃」</div>', unsafe_allow_html=True)
st.header("老後2000万円問題は、「持ち家前提」で計算されている。")
st.write("総務省の家計調査では、高齢者の住居費はわずか月1.8万円。持ち家率94%を前提とした数字です。賃貸なら、ここに家賃がまるごと上乗せされます。")
st.image(img("rougosoumu.png"), use_container_width=True)
st.markdown("<hr>", unsafe_allow_html=True)

# ============================================================
# ★ 簡易ライフプランニング・シミュレーション
# ============================================================
st.markdown('<div class="section-label">あなたの数字で試算</div>', unsafe_allow_html=True)
st.header("🧮 簡易ライフプランニング")

# ---- ① 現状把握：家族構成 ----
st.subheader("① ご家族の構成")
fc1, fc2 = st.columns(2)
with fc1:
    age_husband = st.number_input("ご主人の年齢", min_value=18, max_value=90, value=35)
with fc2:
    age_wife = st.number_input("奥様の年齢", min_value=18, max_value=90, value=33)

num_children = st.number_input("お子様の人数", min_value=0, max_value=5, value=1)
children = []
for i in range(int(num_children)):
    cc1, cc2 = st.columns(2)
    with cc1:
        c_age = st.number_input(f"お子様{i+1} 年齢", min_value=0, max_value=40, value=0, key=f"child_age_{i}")
    with cc2:
        c_sex = st.selectbox(f"お子様{i+1} 性別", ["男の子", "女の子"], key=f"child_sex_{i}")
    children.append((c_age, c_sex))

# ご本人の年齢（積立計算の基準）はご主人の年齢を使用
age = age_husband

# ---- 収入・支出・金融商品・借入・家賃 ----
st.subheader("② いまの収入と支出")
ic1, ic2, ic3 = st.columns(3)
with ic1:
    income_husband = st.number_input("手取り収入：ご主人（万円/月）", min_value=0.0, value=30.0, step=1.0)
with ic2:
    income_wife = st.number_input("手取り収入：奥様（万円/月）", min_value=0.0, value=15.0, step=1.0)
with ic3:
    income_other = st.number_input("手取り収入：その他（万円/月）", min_value=0.0, value=0.0, step=1.0)

sc1, sc2 = st.columns(2)
with sc1:
    rent_now = st.number_input("現在の家賃（万円/月）", min_value=0.0, value=15.0, step=1.0)
with sc2:
    spend_self = st.number_input("毎月の生活費・自己申告（家賃を除く・万円）", min_value=0.0, value=20.0, step=1.0)

st.markdown("**毎月の金融商品・貯蓄（万円/月）**")
mc1, mc2, mc3, mc4 = st.columns(4)
with mc1: f_nisa = st.number_input("NISA積立", min_value=0.0, value=3.0, step=0.5)
with mc2: f_hoken = st.number_input("保険", min_value=0.0, value=2.0, step=0.5)
with mc3: f_chokin = st.number_input("貯金", min_value=0.0, value=3.0, step=0.5)
with mc4: f_other = st.number_input("その他", min_value=0.0, value=0.0, step=0.5)

bc1, bc2, bc3 = st.columns(3)
with bc1:
    loan_month = st.number_input("借入の月返済額（クレカ・奨学金・車など・万円）", min_value=0.0, value=0.0, step=0.5)
with bc2:
    bonus_year = st.number_input("ボーナス：年間（万円）", min_value=0.0, value=100.0, step=10.0)
with bc3:
    big_spend = st.selectbox("3年以内に200万円以上の出費予定", ["なし", "あり"])

# ---- 本当の生活費（家賃も差し引く）----
income_total = income_husband + income_wife + income_other
finance_total = f_nisa + f_hoken + f_chokin + f_other
real_spend = income_total - finance_total - loan_month - rent_now  # 収入−金融−借入−家賃
gap = real_spend - spend_self

st.subheader("③ 自己申告 vs 本当の生活費")
zc1, zc2, zc3 = st.columns(3)
zc1.metric("自己申告の生活費（家賃除く）", f"{spend_self:.1f}万円/月")
zc2.metric("収入−金融−借入−家賃＝本当の生活費", f"{real_spend:.1f}万円/月")
zc3.metric("ズレ（見えていない支出）", f"{gap:+.1f}万円/月")
if gap > 0:
    st.warning(f"自己申告より、実際は毎月 約{gap:.1f}万円 多く使っています。"
               f"年間にすると約{gap*12:.0f}万円。この「見えていない支出」を把握することが第一歩です。")
elif gap < 0:
    st.info("自己申告のほうが多めです。把握はできていますが、金融商品への配分を見直す余地があるかもしれません。")
else:
    st.info("自己申告と計算値が一致しています。")

st.markdown("---")

# ---- ④ 老後の必要資金 ----
st.subheader("④ 老後の必要資金")
st.caption("※ゆとりある老後：月36万円／最低限の生活：月25万円（生命保険文化センター）。"
           "最低でも25万円かかる理由は、退職後に自分で払う社会保険料と、リフォーム・車買い替えなど突発的出費の年割り分です。")

oc1, oc2, oc3 = st.columns(3)
with oc1:
    start_age = st.number_input("老後生活の開始年齢", min_value=55, max_value=75, value=65)
    end_age = st.number_input("何歳まで生きると想定するか", min_value=75, max_value=110, value=90)
with oc2:
    life_cost = st.number_input("老後の月の生活費（家賃除く・万円）", min_value=10.0, max_value=60.0, value=36.0, step=1.0)
    is_rent_old = st.checkbox("老後も賃貸で暮らす", value=False)
with oc3:
    pension = st.number_input("年金は月いくらもらえると思いますか（万円）", min_value=0.0, max_value=40.0, value=10.0, step=1.0)
    retire_money = st.number_input("退職金（夫婦合計・万円）", min_value=0.0, value=500.0, step=100.0)

old_rent = 0.0
if is_rent_old:
    st.caption("👉 今の都内ワンルームは平均11万円、20年前は平均6万円でした。老後、いくらの家賃に住みますか？")
    old_rent = st.number_input("老後の家賃（万円/月）", min_value=0.0, max_value=40.0, value=11.0, step=1.0)

inherit = st.number_input("相続で見込める額（不確実なら0・万円）", min_value=0.0, value=0.0, step=100.0)

# 老後計算
life_cost_final = life_cost + old_rent
retire_years = max(end_age - start_age, 0)
need_total = life_cost_final * 12 * retire_years
pension_total = pension * 12 * retire_years
self_need = max(need_total - pension_total - retire_money - inherit, 0)

st.markdown("#### 老後の総額シミュレーション")
st.table({
    "項目": [
        f"必要総額（月{life_cost_final:.0f}万円 × 12 × {retire_years}年）",
        f"－ 年金（月{pension:.0f}万円 × 12 × {retire_years}年）",
        "－ 退職金（夫婦合計）",
        "－ 相続",
        "＝ 自力で準備が必要な額",
    ],
    "金額": [
        f"{need_total:,.0f}万円",
        f"▲{pension_total:,.0f}万円",
        f"▲{retire_money:,.0f}万円",
        f"▲{inherit:,.0f}万円",
        f"{self_need:,.0f}万円",
    ],
})

st.markdown("---")

# ---- ⑤ 毎月いくら必要か（利回り別）----
st.subheader("⑤ 65歳までに、毎月いくら積み立てれば届く？")
years_to_65 = max(65 - age, 1)
st.write(f"ご主人 現在 {age}歳 → 65歳まで **残り{years_to_65}年**。目標額は **{self_need:,.0f}万円** です。")

rate = st.slider("利回り（%）を動かすと、毎月必要額が変わります", 0.0, 12.0, 5.0, step=0.5)

def monthly_needed(goal_manen, years, rate_percent):
    r = rate_percent / 100
    if r == 0:
        annual = goal_manen / years
    else:
        factor = ((1 + r) ** years - 1) / r
        annual = goal_manen / factor
    return annual / 12

mneed = monthly_needed(self_need, years_to_65, rate)
st.metric(f"利回り {rate:.1f}% の場合・毎月必要な積立額", f"約 {mneed:.1f}万円/月")

st.markdown("#### 利回り別の比較")
rates = [0, 3, 5, 7, 10]
st.table({
    "利回り": [f"{x}%（貯金のみ）" if x == 0 else f"{x}%" for x in rates],
    "毎月必要な積立額": [f"約 {monthly_needed(self_need, years_to_65, x):.1f}万円/月" for x in rates],
})
st.caption("※年1回複利の積立終価で試算。利回りは保証されるものではありません。"
           "一般に3〜5%は現実的に狙える範囲、7%超はリスクが高く確実ではなく、10%超を継続するのは非常に困難な水準です。")
st.markdown("<hr>", unsafe_allow_html=True)

# ============================================================
# ★ 万が一（病気・怪我・リストラ）
# ============================================================
st.markdown('<div class="section-label">万が一に備える</div>', unsafe_allow_html=True)
st.header("もし、病気・怪我・リストラで働けなくなったら？")
st.markdown("""
<p class="story">
問題は、病気や怪我で働けなくなった時です。<br>
働けなくなると、傷病手当金で手取りの半分ほどは出ますが、<b>1年半で止まります</b>。<br>
その後は収入が激減。一方で支出は下がらず、治療費でむしろ上がることも。<br>
例えば、手元資産500万円を月30万円で取り崩すと、<b>約16ヶ月で枯渇</b>します。<br>
足りない分を、貯金で備えるか、保険で備えるか——ここが分かれ道です。
</p>
""", unsafe_allow_html=True)

st.success("💡 住宅ローンなら、もしもの備えが組み込める\n\n"
           "・**がん団信**：がんと診断されたら、住宅ローンの残りが0円になる\n\n"
           "・**失業保障・全疾病保障・自然災害保障**：働けない・住めない事態をカバー\n\n"
           "足りない部分は、保険などで補う設計ができます。")

st.image(img("danshi.png"), use_container_width=True, caption="団信の保障（失業保障・全疾病保障・自然災害保障など）")

st.error("【賃貸の場合】がんになっても、リストラされても、家賃の支払い義務は残ります。"
         "払えなければ、より安い家賃へ引っ越すしかありません。"
         "しかし、その時にも退去費用＋引越し費用がかかります。"
         "——これが、自由なはずの賃貸のデメリットです。")
st.markdown("<hr>", unsafe_allow_html=True)

# ============================================================
# ★ 準備できなかった場合のストーリー
# ============================================================
st.markdown('<div class="section-label">準備できなかった、その先</div>', unsafe_allow_html=True)
st.header("もし、老後の準備ができなかったら——")
st.markdown("""
<p class="story">
<b>① 65歳で退職。</b>でも、多くの人がどうにか70歳まで働きます（シルバー人材、ガードマンなど）。<br><br>
<b>② 70歳以降は雇われにくくなり、</b>退職金を取り崩す生活へ。月の不足が15万円なら、退職金500万円は約3年で底をつきます。賃貸なら、さらに多くが必要です。<br><br>
<b>③ 73歳、資産ゼロ。</b>生活保護を申請しに、窓口へ向かいます。<br><br>
<b>④ 窓口で必ず聞かれます。「ご家族はいますか？」</b>「子供がいて、元気に働いています」——そう答えた瞬間、扶養が優先され、生活保護は受けにくくなります。<br><br>
<b>⑤ 結果、足りないお金を子供に頼る。あるいは同居させてもらう。</b>子供に、金銭的にも精神的にも負担をかけることになります。
</p>
""", unsafe_allow_html=True)

st.info("一方、自分の資産（持ち家）があれば——万が一の時、売却やリバースモーゲージで現金化できます。"
        "住まいが「最後の備え」になるのです。")

st.warning("だから、賃貸のままでは足りません。"
           "貯金するか、運用するか。そして何より、まずは「購入」を検討することが、"
           "あなたとご家族の未来を守る備えになります。")
st.markdown("<hr>", unsafe_allow_html=True)

# ============================================================
# 12 一生賃貸派の2つの道（読み物）
# ============================================================
st.markdown('<div class="section-label">突きつけられる現実</div>', unsafe_allow_html=True)
st.header("一生賃貸派が取れる道は、結局2つだけ。")
st.write("① 老後、生活費の安い地方へ移住する／② それまでに資産を作りきる。**どちらにせよ、「今からの準備」が運命を分けます。**")
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
