import streamlit as st
import pandas as pd

# ✅ サイドバー完全非表示＋全幅化（共通CSS）
st.set_page_config(page_title="家賃補助シミュレーション", layout="wide")
st.markdown("""
<style>
section[data-testid='stSidebar'] {display: none !important;}
button[kind="header"] {display: none !important;}
[data-testid="stHeader"] {visibility: hidden !important;}
[data-testid="stToolbar"] {display: none !important;}
div.block-container {padding-top: 1rem !important; max-width: 100% !important;}
</style>
""", unsafe_allow_html=True)

st.title("🏠 家賃補助シミュレーション")

# -------------------------
# 入力欄
# -------------------------
age_start = st.number_input("現在の年齢", 20, 80, 35)
age_end = 90
support_end_age = st.number_input("家賃補助が終了する年齢", 40, 70, 65)

# 入力検証
if support_end_age <= age_start:
    st.error("⚠️ 家賃補助終了年齢は現在の年齢より大きい値を入力してください。")
    st.stop()

st.markdown("### 家賃設定（最大6区分）")
rent_settings = []
for i in range(6):
    c1, c2, c3 = st.columns(3)
    with c1:
        start = st.number_input(f"区分{i+1} 開始年齢", 20, 100, 30 + i * 10, key=f"start_{i}")
    with c2:
        end = st.number_input(f"区分{i+1} 終了年齢", 20, 100, 39 + i * 10, key=f"end_{i}")
    with c3:
        rent = st.number_input(f"区分{i+1} 家賃 (万円)", 0, 100, 10 + i * 2, key=f"rent_{i}")
    if start <= end:
        rent_settings.append((start, end, rent))

if not rent_settings:
    st.warning("⚠️ 家賃区分が未設定のため、全期間家賃0万円として計算します。")

st.markdown("### 家賃補助のポートフォリオ（毎月・万円）")
c1, c2, c3 = st.columns(3)
with c1:
    waste = st.number_input("浪費 (万円)", 0, 50, 2)
with c2:
    save = st.number_input("貯蓄 (万円)", 0, 50, 2)
with c3:
    invest = st.number_input("運用 (万円)", 0, 50, 6)

rate = st.number_input("運用利回り（年%）", 0.0, 10.0, 5.0) / 100
rate = max(rate, 0)

# -------------------------
# 東京エリア別家賃相場表
# -------------------------
st.markdown("### 📊 東京エリア別 家賃相場（参考）")
rent_data = [
    ["都心5区", "千代田区・中央区・港区・新宿区・渋谷区", "約18～25万円", "約28～35万円", "約50万円前後"],
    ["城南地区", "品川区・目黒区・世田谷区・大田区・渋谷区", "約16〜20万円", "約22〜26万円", "約25〜32万円"],
    ["城北地区", "文京区・北区・荒川区・板橋区・足立区・葛飾区", "約9〜13万円", "約11〜15万円", "約16〜20万円"],
    ["城西地区", "杉並区・中野区・練馬区・武蔵野市・西東京市", "約12〜16万円", "約14〜18万円", "約17〜22万円"],
    ["城東地区", "江東区・墨田区・江戸川区・台東区・荒川区", "約13〜16万円", "約15〜20万円", "約20〜24万円"]
]
df_rent = pd.DataFrame(rent_data, columns=["地域", "対象区", "1LDK", "2LDK", "3LDK以上"])
st.dataframe(df_rent.style.set_properties(**{"font-size": "12px"}), hide_index=True)

# -------------------------
# 資産シミュレーション計算
# -------------------------
years = age_end - age_start
rows = []
saving = 0
investing = 0

for i in range(years + 1):
    age = age_start + i
    rent_now = 0
    for s, e, r in rent_settings:
        if s <= age <= e:
            rent_now = r
            break

    if age < support_end_age:
        saving += save * 12
        investing = investing * (1 + rate) + invest * 12
    else:
        total_expense = rent_now * 12
        if total_expense <= saving:
            saving -= total_expense
        else:
            shortfall = total_expense - saving
            saving = 0
            investing = max(0, investing - shortfall)

    total_asset = saving + investing
    rows.append([age, rent_now, round(saving), round(investing), round(total_asset)])

if rows:
    asset_65 = next((row[4] for row in rows if row[0] == 65), 0)
else:
    asset_65 = 0

st.markdown(f"### 💰 65歳時点の資産額（貯蓄＋運用分） ⇒ **{asset_65:,} 万円**")

df_assets = pd.DataFrame(
    rows,
    columns=["年齢", "家賃 (万円)", "貯蓄 (万円)", "運用 (万円)", "総資産 (万円)"]
) if rows else pd.DataFrame(columns=["年齢", "家賃 (万円)", "貯蓄 (万円)", "運用 (万円)", "総資産 (万円)"])

st.dataframe(
    df_assets.style.format({
        "家賃 (万円)": "{:,.0f}",
        "貯蓄 (万円)": "{:,.0f}",
        "運用 (万円)": "{:,.0f}",
        "総資産 (万円)": "{:,.0f}"
    }).set_properties(subset=["年齢"], **{"text-align": "center"}).set_properties(
        subset=["家賃 (万円)", "貯蓄 (万円)", "運用 (万円)", "総資産 (万円)"], **{"text-align": "right"}
    ),
    height=400
)

# -------------------------
# 老後生活費の目安
# -------------------------
st.markdown("### 📌 老後生活費の目安（生命保険文化センター 2024年）")
df_living = pd.DataFrame([
    ["食費", 7.5, ""],
    ["住居費", 2.0, "持ち家想定（賃貸は＋3〜7万）"],
    ["光熱・水道", 2.0, ""],
    ["保健・医療", 1.7, ""],
    ["交通・通信", 2.6, ""],
    ["趣味・娯楽", 2.5, ""],
    ["交際費", 2.7, ""],
    ["その他", 2.5, "雑費・予備費"],
    ["合計（最低限）", 23.5, ""],
    ["合計（ゆとり）", 35.7, "旅行・趣味など含む"]
], columns=["項目", "月額（万円）", "備考"])

st.table(
    df_living.style.format({"月額（万円）": "{:,.1f}万円"})
    .set_properties(subset=["月額（万円）"], **{"text-align": "right"})
)
# ===== 公式LINEバナー（×で閉じられる・PC/スマホ両対応）=====
import urllib.parse as _url

def render_line_banner():
    # 1) セッションフラグ初期化
    if "line_banner_closed" not in st.session_state:
        st.session_state.line_banner_closed = False

    # 2) ?close_banner=1 を検知して閉じる
    try:
        qp = st.query_params
        close_flag = str(qp.get("close_banner", "0")) == "1"
        qp_dict = dict(qp)  # 既存のクエリ保持用
    except Exception:
        qp = st.experimental_get_query_params()
        close_flag = (qp.get("close_banner", ["0"])[0] == "1")
        qp_dict = {k: (v[0] if isinstance(v, list) else v) for k, v in qp.items()}

    if close_flag:
        st.session_state.line_banner_closed = True

    if st.session_state.line_banner_closed:
        return  # 以降レンダしない

    # 3) × クリック時のURL（既存クエリを保持して close_banner=1 だけ付与）
    qp_dict = {k: (v if not isinstance(v, list) else v[0]) for k, v in qp_dict.items()}
    qp_dict["close_banner"] = "1"
    qs = _url.urlencode(qp_dict)
    close_url = "?" + qs if qs else "?close_banner=1"

    # 4) バナー描画（×はリンク。JS不要）
    st.markdown(f"""
    <style>
    .line-banner-wrap {{
      position: fixed;
      bottom: 100px; right: 18px; z-index: 9999;
    }}
    .line-banner {{
      background: #06C755; color: #fff;
      padding: 14px 18px 20px; border-radius: 12px;
      box-shadow: 0 4px 10px rgba(0,0,0,0.25);
      font-size: 15px; text-align: center; position: relative;
    }}
    .line-banner:hover {{ transform: scale(1.02); background:#05b34d; }}
    .line-banner .ttl {{ font-size: 17px; font-weight: 800; line-height: 1.4; }}
    .line-banner .id  {{ font-size: 20px; font-weight: 900; margin: 6px 0 6px; }}
    .line-banner img  {{
      width: 130px; display:block; margin: 8px auto 10px;
      border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.3);
      background:#fff;
    }}
    .line-banner .cta {{ display:inline-block; font-weight: 800; text-decoration: underline; color:#fff; }}
    .line-banner .close-btn {{
      position:absolute; top:6px; right:10px; width:24px; height:24px;
      border-radius:50%; background: rgba(0,0,0,0.25);
      color:#fff; text-align:center; line-height:24px;
      font-size:16px; font-weight:700; text-decoration:none;
    }}
    .line-banner .close-btn:hover {{ background: rgba(0,0,0,0.4); }}
    @media (max-width: 768px){{
      .line-banner-wrap {{ bottom: 100px; right: 14px; }}
      .line-banner {{ padding: 12px 14px 18px; }}
      .line-banner img {{ width: 110px; }}
      .line-banner .id {{ font-size: 18px; }}
    }}
    </style>

    <div class="line-banner-wrap" id="line-banner">
      <div class="line-banner" role="region" aria-label="LINE公式バナー">
        <a class="close-btn" href="{close_url}" aria-label="バナーを閉じる">×</a>
        <a href="https://lin.ee/m40HEqN" target="_blank" rel="noopener" style="text-decoration:none; color:#fff;">
          <div class="ttl">📲 シミュレーション利用は<br>LINEで簡単・不動産相談</div>
          <div class="id">LINE ID：@fudo3</div>
          <img src="https://qr-official.line.me/gs/M_277qthwd_GW.png?oat_content=qr" alt="LINE公式QRコード">
          <span class="cta">▶ 公式LINEで相談する</span>
        </a>
      </div>
    </div>
    """, unsafe_allow_html=True)

# どこかで呼び出す（各ページの末尾など）
render_line_banner()
