# -*- coding: utf-8 -*-
import os, json, tempfile
from datetime import datetime
from pathlib import Path

import streamlit as st
from fpdf import FPDF

st.set_page_config(page_title="お客様ポータル（ヒアリング）", layout="wide")

# =========================
# データ入出力
# =========================
DATA_DIR = Path("data/clients")
DATA_DIR.mkdir(parents=True, exist_ok=True)

def load_client(cid: str):
    f = DATA_DIR / f"{cid}.json"
    if not f.exists():
        return None
    return json.loads(f.read_text(encoding="utf-8"))

def save_client(cid: str, data: dict):
    f = DATA_DIR / f"{cid}.json"
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def to_hensachi(avg_1to5: float) -> float:
    # 3.0 → 50（直線）
    return round(50 + (avg_1to5 - 3.0) * 10, 1)

# =========================
# URL パラメータ（?client=... だけ使う）
# =========================
client_id = None
try:
    # Streamlit 新API
    client_id = st.query_params.get("client", None)
except Exception:
    # 旧API保険
    client_id = st.experimental_get_query_params().get("client", [None])
    client_id = client_id[0] if isinstance(client_id, list) else client_id

if not client_id:
    st.warning("このページは専用URLからアクセスしてください。（末尾に ?client=お客様ID が付きます）")
    st.stop()

payload = load_client(client_id)
if not payload:
    st.error("このお客様IDのデータが見つかりません。管理側で発行したURLをご確認ください。")
    st.stop()

name = payload.get("meta", {}).get("name", "お客様")
st.title("理想の住まいへのロードマップ")
st.success(f"{name} 専用ページ（ID: {client_id}）")

# ============================================
# ① 5W2H ヒアリング（PDF出力付き）
# ============================================
st.header("① 5W2H ヒアリング")

TO_EMAIL_DEFAULT = payload.get("hearing", {}).get("pdf_recipient", "")

base_defaults = {
    "name": name,
    "now_area": "", "now_years": 5, "is_owner": "賃貸",
    "housing_cost": 10, "family": "",
    "sat_point": "", "sat_price": 3, "sat_location": 3, "sat_size": 3, "sat_age": 3, "sat_spec": 3,
    "dissat_free": "",
    # 5W2H
    "w_why": "", "w_when": "", "w_where": "", "w_who": "",
    "w_what": "", "w_how": "", "w_howmuch": "", "w_free": "",
    # トレードオフ（大カテゴリー5本に統一）
    "prio_price": 3, "prio_location": 3, "prio_size_layout": 3, "prio_spec": 3, "prio_mgmt": 3,
    # 連絡
    "contact_pref": "", "share_method": "", "pdf_recipient": TO_EMAIL_DEFAULT,
}

if "hearing" not in payload:
    payload["hearing"] = base_defaults.copy()
else:
    # 足りないキーを補完
    for k, v in base_defaults.items():
        payload["hearing"].setdefault(k, v)

hearing = payload["hearing"]

with st.form("hearing_form", clear_on_submit=False):
    st.markdown("#### 基礎情報")
    c1, c2, c3 = st.columns(3)
    with c1:
        hearing["name"] = st.text_input("お名前", value=hearing["name"])
        hearing["now_area"] = st.text_input("現在の居住エリア・駅", value=hearing["now_area"])
    with c2:
        hearing["now_years"] = st.number_input("居住年数（年）", 0, 100, int(hearing["now_years"]))
        hearing["is_owner"] = st.selectbox("持ち家・賃貸", ["賃貸", "持ち家"], index=0 if hearing["is_owner"] == "賃貸" else 1)
    with c3:
        hearing["housing_cost"] = st.number_input("住居費（万円/月）", 0, 200, int(hearing["housing_cost"]))
    hearing["family"] = st.text_input("ご家族構成（人数・年齢・将来予定）", value=hearing["family"])

    st.divider()
    st.markdown("#### 現在の住まい（満足・不満）")
    hearing["sat_point"] = st.text_area("満足点（自由入力）", value=hearing["sat_point"])
    sc1, sc2, sc3, sc4, sc5 = st.columns(5)
    with sc1: hearing["sat_price"] = st.slider("満足度：価格", 1, 5, int(hearing["sat_price"]))
    with sc2: hearing["sat_location"] = st.slider("満足度：立地", 1, 5, int(hearing["sat_location"]))
    with sc3: hearing["sat_size"] = st.slider("満足度：広さ", 1, 5, int(hearing["sat_size"]))
    with sc4: hearing["sat_age"] = st.slider("満足度：築年数", 1, 5, int(hearing["sat_age"]))
    with sc5: hearing["sat_spec"] = st.slider("満足度：スペック", 1, 5, int(hearing["sat_spec"]))
    st.caption(f"満足度合計：{int(hearing['sat_price'])+int(hearing['sat_location'])+int(hearing['sat_size'])+int(hearing['sat_age'])+int(hearing['sat_spec'])} / 25")
    hearing["dissat_free"] = st.text_area("不満点（自由入力）", value=hearing["dissat_free"])

    st.divider()
    st.markdown("#### 5W2H（購入計画）")
    c1, c2 = st.columns(2)
    with c1:
        hearing["w_why"] = st.text_input("Why（なぜ）：購入理由", value=hearing["w_why"])
        hearing["w_when"] = st.text_input("When（いつ）：購入/入居タイミング", value=hearing["w_when"])
        hearing["w_where"] = st.text_input("Where（どこで）：希望エリア・沿線", value=hearing["w_where"])
        hearing["w_who"] = st.text_input("Who（誰が）：居住メンバー", value=hearing["w_who"])
    with c2:
        hearing["w_what"] = st.text_input("What（何を）：種別・広さ・階数・設備", value=hearing["w_what"])
        hearing["w_how"] = st.text_input("How（どう買う）：ローン/頭金", value=hearing["w_how"])
        hearing["w_howmuch"] = st.text_input("How much（いくら）：総予算/月返済上限", value=hearing["w_howmuch"])
        hearing["w_free"] = st.text_area("補足（自由入力）", value=hearing["w_free"])

    st.divider()
    st.markdown("#### 重要度のトレードオフ（1=最優先〜5）")
    p1, p2, p3, p4, p5 = st.columns(5)
    with p1: hearing["prio_price"] = st.selectbox("価格", [1,2,3,4,5], index=int(hearing["prio_price"]) - 1)
    with p2: hearing["prio_location"] = st.selectbox("立地", [1,2,3,4,5], index=int(hearing["prio_location"]) - 1)
    with p3: hearing["prio_size_layout"] = st.selectbox("広さ・間取り", [1,2,3,4,5], index=int(hearing["prio_size_layout"]) - 1)
    with p4: hearing["prio_spec"] = st.selectbox("スペック（専有）", [1,2,3,4,5], index=int(hearing["prio_spec"]) - 1)
    with p5: hearing["prio_mgmt"] = st.selectbox("管理・共有部・その他", [1,2,3,4,5], index=int(hearing["prio_mgmt"]) - 1)

    st.divider()
    st.markdown("#### 連絡・共有")
    cc1, cc2, cc3 = st.columns(3)
    with cc1: hearing["contact_pref"] = st.text_input("希望連絡手段・時間帯", value=hearing["contact_pref"])
    with cc2: hearing["share_method"] = st.text_input("資料共有（LINE/メール 等）", value=hearing["share_method"])
    with cc3: hearing["pdf_recipient"] = st.text_input("PDF送付先メール", value=hearing.get("pdf_recipient", TO_EMAIL_DEFAULT))

    submitted = st.form_submit_button("保存 / PDF作成")

# 保存 & PDF
if submitted:
    payload["hearing"] = hearing
    save_client(client_id, payload)
    st.success("ヒアリングを保存しました。PDFを生成します。")

    import urllib.request
    REG_NAME = "NotoSansJP-Regular.ttf"
    BLD_NAME = "NotoSansJP-Bold.ttf"
    RAW_REG = "https://raw.githubusercontent.com/Naobro/fp/main/fonts/NotoSansJP-Regular.ttf"
    RAW_BLD = "https://raw.githubusercontent.com/Naobro/fp/main/fonts/NotoSansJP-Bold.ttf"

    def ensure_fonts_dir() -> Path:
        candidates = [Path(__file__).resolve().parent / "fonts", Path.cwd() / "fonts",
                      Path("/mount/src/fp/fonts"), Path("/app/fonts")]
        for d in candidates:
            if (d / REG_NAME).exists() and (d / BLD_NAME).exists(): return d.resolve()
        for d in candidates:
            if (d / REG_NAME).exists():
                (d / BLD_NAME).write_bytes((d / REG_NAME).read_bytes()); return d.resolve()
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

    save_cwd = os.getcwd()
    os.chdir(str(font_dir))
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.add_font("NotoSansJP", "", reg_path.name, uni=True)
        pdf.add_font("NotoSansJP", "B", bld_path.name, uni=True)

        def title(t): pdf.set_font("NotoSansJP", "B", 14); pdf.cell(0, 10, t, 0, 1)
        def pair(label, val):
            pdf.set_font("NotoSansJP","B",11); pdf.multi_cell(0, 7, label)
            pdf.set_font("NotoSansJP","",11); pdf.multi_cell(0, 7, str(val) if val not in [None, ""] else "（未入力）")
            pdf.ln(1)

        pdf.set_font("NotoSansJP", "B", 16)
        pdf.cell(0, 10, "不動産ヒアリングシート", 0, 1, "C")
        pdf.set_font("NotoSansJP", "", 10)
        pdf.cell(0, 8, f"作成日時：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, "R"); pdf.ln(2)

        title("基本情報")
        pair("お名前", hearing["name"]); pair("現在の居住エリア・駅", hearing["now_area"])
        pair("居住年数（年）", hearing["now_years"]); pair("種別（賃貸/持ち家）", hearing["is_owner"])
        pair("住居費（万円/月）", hearing["housing_cost"]); pair("ご家族構成", hearing["family"])

        title("現在の住まい（満足・不満）")
        pair("満足点", hearing["sat_point"])
        pair("満足度（価格/立地/広さ/築年数/スペック）",
             f"{hearing['sat_price']}/{hearing['sat_location']}/{hearing['sat_size']}/{hearing['sat_age']}/{hearing['sat_spec']}")
        pair("不満点", hearing["dissat_free"])

        title("5W2H（購入計画）")
        pair("Why", hearing["w_why"]); pair("When", hearing["w_when"]); pair("Where", hearing["w_where"]); pair("Who", hearing["w_who"])
        pair("What", hearing["w_what"]); pair("How", hearing["w_how"]); pair("How much", hearing["w_howmuch"]); pair("補足", hearing["w_free"])

        title("重要度のトレードオフ")
        pair("価格 / 立地 / 広さ・間取り / スペック / 管理その他",
             f"{hearing['prio_price']}/{hearing['prio_location']}/{hearing['prio_size_layout']}/{hearing['prio_spec']}/{hearing['prio_mgmt']}")

        title("連絡・共有")
        pair("希望連絡手段・時間帯", hearing["contact_pref"]); pair("資料共有", hearing["share_method"]); pair("PDF送付先", hearing["pdf_recipient"])

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            pdf.output(tmp_file.name)
            pdf_path = tmp_file.name

        with open(pdf_path, "rb") as f:
            st.download_button("📄 PDFをダウンロード", data=f.read(), file_name="hearing_sheet.pdf", mime="application/pdf")
    finally:
        os.chdir(save_cwd)

st.divider()

# ============================================
# ② 現状把握（基準データ：偏差値50の「今の家」）
# ============================================
st.header("② 現状把握（基準：今の家 = 偏差値50）")

if "baseline" not in payload:
    payload["baseline"] = {
        "walk_min": 10, "area_m2": 60, "floor": 3,
        "corner": None, "inner_corridor": None,
        "balcony_aspect": "S", "balcony_depth_m": 1.5,
        "husband_commute_min": 30, "wife_commute_min": 40,
    }
b = payload["baseline"]

with st.form("baseline_form"):
    c1,c2,c3 = st.columns(3)
    with c1:
        b["walk_min"] = st.number_input("最寄駅 徒歩（分）", 0, 60, int(b.get("walk_min",10)))
        b["area_m2"] = st.number_input("専有面積（㎡）", 0, 300, int(b.get("area_m2",60)))
    with c2:
        b["floor"] = st.number_input("所在階", 0, 70, int(b.get("floor",3)))
        b["corner"] = st.selectbox("角部屋", ["不明","いいえ","はい"], index=0 if b.get("corner") is None else (2 if b.get("corner") else 1))
        b["inner_corridor"] = st.selectbox("内廊下", ["不明","いいえ","はい"], index=0 if b.get("inner_corridor") is None else (2 if b.get("inner_corridor") else 1))
    with c3:
        b["balcony_aspect"] = st.selectbox("バルコニー向き", ["N","NE","E","SE","S","SW","W","NW"],
                                           index=["N","NE","E","SE","S","SW","W","NW"].index(b.get("balcony_aspect","S")))
        b["balcony_depth_m"] = st.number_input("バルコニー奥行（m）", 0.0, 5.0, float(b.get("balcony_depth_m",1.5)), step=0.1)
        b["husband_commute_min"] = st.number_input("ご主人 通勤（分）", 0, 180, int(b.get("husband_commute_min",30)))
        b["wife_commute_min"] = st.number_input("奥様 通勤（分）", 0, 180, int(b.get("wife_commute_min",40)))

    if st.form_submit_button("基準を保存（偏差値50）"):
        b["corner"] = (True if b["corner"]=="はい" else (False if b["corner"]=="いいえ" else None))
        b["inner_corridor"] = (True if b["inner_corridor"]=="はい" else (False if b["inner_corridor"]=="いいえ" else None))
        payload["baseline"] = b
        save_client(client_id, payload)
        st.success("基準（今の家）を保存しました。以後、比較ページで偏差値50の基準として使われます。")

st.divider()

st.header("③ 希望条件（◎=必要／○=あったほうがよい／△=どちらでもよい／×=なくてよい）")
CHO = {"◎ 必要":"must","○ あったほうがよい":"want","△ どちらでもよい":"neutral","× なくてよい":"no_need"}
if "wish" not in payload: payload["wish"] = {}
wish = payload["wish"]

def wish_select(label, key):
    cur = wish.get(key, "neutral")
    cur_label = [k for k,v in CHO.items() if v==cur][0] if cur in CHO.values() else "△ どちらでもよい"
    sel = st.selectbox(label, list(CHO.keys()), index=list(CHO.keys()).index(cur_label), key=f"wish-{key}")
    wish[key] = CHO[sel]

with st.expander("立地", expanded=True):
    for k, label in [
        ("loc_walk","最寄駅まで近いこと"),
        ("loc_lines","複数路線利用できること"),
        ("loc_access","職場アクセスが良いこと"),
        ("loc_shop","商業施設の充実"),
        ("loc_edu","教育環境の良さ"),
        ("loc_med","医療アクセスの良さ"),
        ("loc_security","治安の良さ"),
        ("loc_hazard_low","災害リスクが低いこと"),
        ("loc_park","公園・緑地の充実"),
        ("loc_silent","静かな環境"),
    ]:
        wish_select(label, k)

with st.expander("広さ・間取り", expanded=False):
    for k, label in [
        ("sz_area","専有面積の広さ"), ("sz_living","リビングの広さ"),
        ("sz_layout","優れた間取り（ワイドスパン等）"), ("sz_storage","収納量の充実"),
        ("sz_ceiling","天井高が高い"), ("sz_aspect","日当たり（向き）の良さ"),
        ("sz_balcony_depth","バルコニー奥行の余裕"), ("sz_sun_wind","採光・通風の良さ"),
        ("sz_flow","廊下幅・家事動線の良さ"),
    ]:
        wish_select(label, k)

with st.expander("スペック（専有）", expanded=False):
    for k, label in [
        ("k_dishwasher","食洗機"), ("k_purifier","浄水器/整水器"),
        ("k_disposer","ディスポーザー"), ("k_highend_cooktop","高機能コンロ（IH/高火力）"),
        ("k_bi_oven","ビルトインオーブン"), ("b_dryer","浴室暖房乾燥機"),
        ("b_reheating","追い焚き機能"), ("b_mist_sauna","ミストサウナ"),
        ("b_tv","浴室テレビ"), ("b_window","浴室に窓"),
        ("h_floorheat","床暖房"), ("h_aircon_built","エアコン（備付）"),
        ("w_multi","複層ガラス"), ("w_low_e","Low-Eガラス"),
        ("w_double_sash","二重サッシ"), ("w_premium_doors","建具ハイグレード"),
        ("s_allrooms","全居室収納"), ("s_wic","WIC"), ("s_sic","SIC"),
        ("s_pantry","パントリー"), ("s_linen","リネン庫"),
        ("sec_tvphone","TVモニター付インターホン"), ("sec_sensor","玄関センサー"),
        ("net_ftth","光配線方式（各戸まで）"),
    ]:
        wish_select(label, k)

with st.expander("管理・共有部・その他", expanded=False):
    for k, label in [
        ("c_concierge","コンシェルジュサービス"), ("c_box","宅配ボックス"),
        ("c_guest","ゲストルーム"), ("c_lounge_kids","ラウンジ/キッズルーム"),
        ("c_gym_pool","ジム/プール"), ("c_parking_type","駐車場形態（平置き等）"),
        ("c_gomi24","24時間ゴミ出し"), ("c_seismic","免震・制震構造"),
        ("c_security","強いセキュリティ"), ("c_design","外観・エントランスのデザイン"),
        ("c_ev_enough","エレベーター台数の十分さ"), ("c_brand_tower","ブランド/タワー属性"),
        ("c_pet_ok","ペット可"), ("c_ltp_plan","長期修繕/資金計画"),
        ("c_fee_reasonable","修繕積立金 妥当性"), ("c_mgmt","管理体制"),
        ("c_history","共用部修繕履歴"), ("c_yield","収益性（将来の利回り）"),
    ]:
        wish_select(label, k)

if st.button("希望条件を保存"):
    payload["wish"] = wish
    save_client(client_id, payload)
    st.success("希望条件を保存しました。")

st.divider()
st.header("④ 物件比較ページへ")
st.caption("内見物件を入力すると、現住まい（偏差値50）を基準に偏差値を算出します。")
# 別ページ 3_compare.py に client を渡すだけ
app_base = ""  # 相対遷移（Streamlit Cloud想定）
st.link_button("↔ 物件比較へ", f"{app_base}/compare?client={client_id}")