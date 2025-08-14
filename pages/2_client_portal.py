# -*- coding: utf-8 -*-
import os, json, tempfile, uuid
from datetime import datetime
from pathlib import Path

import streamlit as st
from fpdf import FPDF

st.set_page_config(page_title="理想の住まいへのロードマップ", layout="wide")

# =========================
# データ入出力ユーティリティ
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

def new_payload(name: str, pin: str = "") -> dict:
    return {
        "meta": {"name": name, "client_id": "", "pin": pin},
        "hearing": {},
        "baseline": {},
        "current_home": {},
        "wish": {}
    }

# 偏差値換算（平均3.0→50、1.0→30、5.0→70）
def to_hensachi(avg_1to5: float) -> float:
    return round(50 + (avg_1to5 - 3.0) * 10, 1)

# =========================
# クライアント選択 / 新規作成（?client= は任意）
# =========================
q = st.query_params
cid_from_qs = q.get("client")

with st.sidebar:
    st.markdown("### クライアント")
    default_cid = cid_from_qs or st.session_state.get("client_id", "")
    client_id = st.text_input("クライアントID（自由入力 or 既存ID）", value=default_cid, placeholder="例: yamada-2025-01")
    client_name = st.text_input("お客様名（新規作成時）", value=st.session_state.get("client_name", ""))
    client_pin = st.text_input("PIN（任意・比較ページ共有用）", type="password", value=st.session_state.get("client_pin", ""))

    col_sb1, col_sb2 = st.columns(2)
    with col_sb1:
        make_new = st.button("新規作成")
    with col_sb2:
        open_exist = st.button("既存を開く")

# 状態決定
payload = None
if make_new:
    cid = client_id.strip() or f"cid-{uuid.uuid4().hex[:8]}"
    name = client_name.strip() or "お客様"
    payload = new_payload(name=name, pin=client_pin.strip())
    payload["meta"]["client_id"] = cid
    save_client(cid, payload)
    st.session_state["client_id"] = cid
    st.session_state["client_name"] = name
    st.session_state["client_pin"] = payload["meta"]["pin"]
elif open_exist:
    cid = client_id.strip()
    payload = load_client(cid) if cid else None
    if payload:
        st.session_state["client_id"] = cid
        st.session_state["client_name"] = payload.get("meta", {}).get("name", "")
        st.session_state["client_pin"] = payload.get("meta", {}).get("pin", "")
else:
    # 自動ロード：QS またはセッション
    cid = (client_id or "").strip()
    cid = cid or st.session_state.get("client_id", "")
    if cid:
        payload = load_client(cid)

st.title("理想の住まいへのロードマップ")

if not payload:
    st.info("左のサイドバーから **クライアントID** を入力して「既存を開く」か、「新規作成」を押してください。")
    st.stop()

# 確定したID・PIN・名前
client_id = payload["meta"].get("client_id") or st.session_state.get("client_id")
pin_in = payload["meta"].get("pin", "")
st.success(f"{payload.get('meta',{}).get('name','お客様')} 専用ページ（ID: {client_id}）")

# ============================================
# ① ヒアリング（5W2H）＋ PDF出力
# ============================================
st.header("① ヒアリング（5W2H）")

TO_EMAIL_DEFAULT = payload.get("hearing",{}).get("pdf_recipient","naoki.nishiyama@terass.com")
base_hearing = {
    "name": payload.get("meta",{}).get("name",""),
    "now_area": "", "now_years": 5, "is_owner": "賃貸",
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
    "contact_pref": "", "share_method": "", "pdf_recipient": TO_EMAIL_DEFAULT,
}

hearing = payload.get("hearing", {})
for k, v in base_hearing.items():
    hearing.setdefault(k, v)

with st.form("hearing_form", clear_on_submit=False):
    st.markdown("#### 基礎情報")
    c1, c2, c3 = st.columns(3)
    with c1:
        hearing["name"]      = st.text_input("お名前", value=hearing["name"])
        hearing["now_area"]  = st.text_input("現在の居住エリア・駅", value=hearing["now_area"])
    with c2:
        hearing["now_years"] = st.number_input("居住年数（年）", min_value=0, max_value=100, value=int(hearing["now_years"]))
        hearing["is_owner"]  = st.selectbox("持ち家・賃貸", ["賃貸", "持ち家"], index=0 if hearing["is_owner"]=="賃貸" else 1)
    with c3:
        hearing["housing_cost"] = st.number_input("住居費（万円/月）", min_value=0, max_value=200, value=int(hearing["housing_cost"]))
    hearing["family"] = st.text_input("ご家族構成（人数・年齢・将来予定）", value=hearing["family"])

    st.divider()

    st.markdown("#### 現在の住まい（満足・不満）")
    hearing["sat_point"] = st.text_area("現在の住宅の満足点（自由入力）", value=hearing["sat_point"])
    sc1, sc2, sc3, sc4, sc5 = st.columns(5)
    with sc1: hearing["sat_price"] = st.slider("満足度：価格", 1, 5, int(hearing["sat_price"]))
    with sc2: hearing["sat_location"] = st.slider("満足度：立地", 1, 5, int(hearing["sat_location"]))
    with sc3: hearing["sat_size"] = st.slider("満足度：広さ", 1, 5, int(hearing["sat_size"]))
    with sc4: hearing["sat_age"] = st.slider("満足度：築年数", 1, 5, int(hearing["sat_age"]))
    with sc5: hearing["sat_spec"] = st.slider("満足度：スペック", 1, 5, int(hearing["sat_spec"]))
    sat_total = int(hearing["sat_price"]) + int(hearing["sat_location"]) + int(hearing["sat_size"]) + int(hearing["sat_age"]) + int(hearing["sat_spec"])
    st.caption(f"満足度スコア合計：**{sat_total} / 25**")
    hearing["dissat_free"] = st.text_area("不満な点（自由入力）", value=hearing["dissat_free"])

    st.divider()

    st.markdown("#### 5W2H（購入計画）")
    c1, c2 = st.columns(2)
    with c1:
        hearing["w_why"]     = st.text_input("Why（なぜ）：購入理由", value=hearing["w_why"])
        hearing["w_when"]    = st.text_input("When（いつ）：購入／入居タイミング", value=hearing["w_when"])
        hearing["w_where"]   = st.text_input("Where（どこで）：希望エリア・沿線", value=hearing["w_where"])
        hearing["w_who"]     = st.text_input("Who（誰が）：居住メンバー", value=hearing["w_who"])
    with c2:
        hearing["w_what"]    = st.text_input("What（何を）：種別・広さ・階数・設備", value=hearing["w_what"])
        hearing["w_how"]     = st.text_input("How（どう買う）：ローン・頭金", value=hearing["w_how"])
        hearing["w_howmuch"] = st.text_input("How much（いくら）：総予算／月返済上限", value=hearing["w_howmuch"])
        hearing["w_free"]    = st.text_area("補足（自由入力）", value=hearing["w_free"])

    st.divider()

    st.markdown("#### 重要度のトレードオフ（1=最優先〜5）")
    p1, p2, p3, p4, p5 = st.columns(5)
    with p1: hearing["prio_price"] = st.selectbox("価格", [1,2,3,4,5], index=int(hearing["prio_price"])-1)
    with p2: hearing["prio_location"] = st.selectbox("立地（資産性）", [1,2,3,4,5], index=int(hearing["prio_location"])-1)
    with p3: hearing["prio_size"] = st.selectbox("広さ・間取り", [1,2,3,4,5], index=int(hearing["prio_size"])-1)
    with p4: hearing["prio_age"] = st.selectbox("築年数（参考）", [1,2,3,4,5], index=int(hearing["prio_age"])-1)
    with p5: hearing["prio_spec"] = st.selectbox("スペック（専有）", [1,2,3,4,5], index=int(hearing["prio_spec"])-1)

    st.divider()

    st.markdown("#### 連絡・共有")
    cc1, cc2, cc3 = st.columns(3)
    with cc1: hearing["contact_pref"] = st.text_input("希望連絡手段・時間帯", value=hearing["contact_pref"])
    with cc2: hearing["share_method"] = st.text_input("資料共有（LINE／メール 等）", value=hearing["share_method"])
    with cc3: hearing["pdf_recipient"] = st.text_input("PDF送付先メール", value=hearing.get("pdf_recipient", TO_EMAIL_DEFAULT))

    submitted = st.form_submit_button("保存 / PDF作成")

# PDF生成
if submitted:
    payload["hearing"] = hearing
    save_client(client_id, payload)
    st.success("ヒアリング内容を保存しました。PDFを生成します。")

    # フォント（NotoSansJP）準備
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
        pair("満足度（価格/立地/広さ/築年数/スペック）", f"{hearing['sat_price']}/{hearing['sat_location']}/{hearing['sat_size']}/{hearing['sat_age']}/{hearing['sat_spec']}")
        pair("不満な点", hearing["dissat_free"])

        title("5W2H（購入計画）")
        pair("Why", hearing["w_why"]); pair("When", hearing["w_when"]); pair("Where", hearing["w_where"]); pair("Who", hearing["w_who"])
        pair("What", hearing["w_what"]); pair("How", hearing["w_how"]); pair("How much", hearing["w_howmuch"]); pair("補足", hearing["w_free"])

        title("重要度のトレードオフ")
        pair("価格/立地/広さ/築年数/スペック", f"{hearing['prio_price']}/{hearing['prio_location']}/{hearing['prio_size']}/{hearing['prio_age']}/{hearing['prio_spec']}")

        title("連絡・共有")
        pair("希望連絡手段・時間帯", hearing["contact_pref"]); pair("資料共有", hearing["share_method"]); pair("PDF送付先", hearing["pdf_recipient"])

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            pdf.output(tmp_file.name)
            pdf_path = tmp_file.name
        with open(pdf_path, "rb") as f:
            st.download_button("📄 PDFをダウンロード", data=f.read(), file_name="hearing_sheet.pdf", mime="application/pdf")
    finally:
        os.chdir(save_cwd)

payload["hearing"] = hearing
save_client(client_id, payload)

st.divider()

# ============================================
# ② 現状把握（現在の住宅の基礎情報）
# ============================================
st.header("② 現状把握（現在の住宅の基礎情報）")

if "baseline" not in payload or not payload["baseline"]:
    payload["baseline"] = {
        "housing_cost_m": 10,
        "walk_min": 10,
        "area_m2": 60,
        "floor": 3,
        "corner": None,                # True/False/None
        "inner_corridor": None,        # True/False/None
        "balcony_aspect": "S",         # N/NE/E/SE/S/SW/W/NW
        "balcony_depth_m": 1.5,        # 奥行
        "view": "未設定",
        "husband_commute_min": 30,
        "wife_commute_min": 40,
        "spec_current": {}
    }

b = payload["baseline"]

with st.form("baseline_form"):
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        b["housing_cost_m"] = st.number_input("住居費（万円/月）", 0, 200, int(b.get("housing_cost_m",10)))
        b["walk_min"] = st.number_input("最寄駅 徒歩（分）", 0, 60, int(b.get("walk_min",10)))
    with c2:
        b["area_m2"] = st.number_input("専有面積（㎡）", 0, 300, int(b.get("area_m2",60)))
        b["floor"] = st.number_input("所在階（数値）", 0, 70, int(b.get("floor",3)))
    with c3:
        corner_label = "不明" if b.get("corner") is None else ("はい" if b.get("corner") else "いいえ")
        inner_label = "不明" if b.get("inner_corridor") is None else ("はい" if b.get("inner_corridor") else "いいえ")
        corner_sel = st.selectbox("角部屋", ["不明","いいえ","はい"], index=["不明","いいえ","はい"].index(corner_label))
        inner_sel = st.selectbox("内廊下", ["不明","いいえ","はい"], index=["不明","いいえ","はい"].index(inner_label))
    with c4:
        b["balcony_aspect"] = st.selectbox("バルコニー向き", ["N","NE","E","SE","S","SW","W","NW"],
                                           index=["N","NE","E","SE","S","SW","W","NW"].index(b.get("balcony_aspect","S")))
        b["balcony_depth_m"] = st.number_input("バルコニー奥行（m）", 0.0, 5.0, float(b.get("balcony_depth_m",1.5)), step=0.1)

    c5, c6 = st.columns(2)
    with c5:
        b["view"] = st.selectbox("眺望", ["未設定","開放","一部遮り","正面に遮り"],
                                 index=["未設定","開放","一部遮り","正面に遮り"].index(b.get("view","未設定")))
    with c6:
        b["husband_commute_min"] = st.number_input("ご主人様 通勤（分）", 0, 180, int(b.get("husband_commute_min",30)))
        b["wife_commute_min"] = st.number_input("奥様 通勤（分）", 0, 180, int(b.get("wife_commute_min",40)))

    if st.form_submit_button("② 現状把握を保存"):
        b["corner"] = (True if corner_sel=="はい" else (False if corner_sel=="いいえ" else None))
        b["inner_corridor"] = (True if inner_sel=="はい" else (False if inner_sel=="いいえ" else None))
        payload["baseline"] = b
        save_client(client_id, payload)
        st.success("保存しました。")

st.divider()

# ============================================
# ③ 現在の住居スコアリング
# ============================================
st.header("③ 現在の住居スコアリング")

if "current_home" not in payload or not payload["current_home"]:
    payload["current_home"] = {
        # 立地
        "walk_min": b.get("walk_min",10), "multi_lines": 1, "access_min": 30,
        "shop_level": "普通", "edu_level": "普通", "med_level": "普通",
        "security_level": "普通", "hazard_level": "中",
        "park_level": "普通", "noise_level": "普通",
        # 広さ・間取り
        "area_m2": b.get("area_m2",60), "living_jyo": 12,
        "layout_type": "田の字", "storage_level": "普通",
        "ceiling_level": "普通",
        "balcony_aspect": b.get("balcony_aspect","S"), "balcony_depth_m": b.get("balcony_depth_m",1.5),
        "sun_wind_level": "普通", "hall_flow_level": "普通",
        # 専有（設備）
        "k_dishwasher": False, "k_purifier": False, "k_disposer": False, "k_highend_cooktop": False, "k_bi_oven": False,
        "b_dryer": False, "b_reheating": False, "b_mist_sauna": False, "b_tv": False, "b_window": False,
        "h_floorheat": False, "h_aircon_built": False,
        "w_multi": False, "w_low_e": False, "w_double_sash": False, "w_premium_doors": False,
        "s_allrooms": False, "s_wic": False, "s_sic": False, "s_pantry": False, "s_linen": False,
        "sec_tvphone": False, "sec_sensor": False, "net_ftth": False,
        # 管理・共用
        "c_box": True, "c_parking": "機械式", "c_gomi24": True,
        "c_seismic": False, "c_security": True,
        "c_design_level": "普通",
        "c_ev_count": 2, "c_pet_ok": True,
    }

cur = payload["current_home"]

with st.expander("立地・環境", expanded=True):
    c1,c2,c3 = st.columns(3)
    with c1:
        cur["walk_min"] = st.number_input("最寄駅までの徒歩分数", 0, 60, int(cur["walk_min"]))
        cur["multi_lines"] = st.number_input("複数路線利用の可否（本数）", 0, 10, int(cur["multi_lines"]))
        cur["access_min"] = st.number_input("職場までのアクセス時間（分）", 0, 180, int(cur["access_min"]))
    with c2:
        cur["shop_level"] = st.selectbox("商業施設の充実度", ["充実","普通","乏しい"], index=["充実","普通","乏しい"].index(cur["shop_level"]))
        cur["edu_level"]  = st.selectbox("教育環境", ["良い","普通","弱い"], index=["良い","普通","弱い"].index(cur["edu_level"]))
        cur["med_level"]  = st.selectbox("医療施設の近さ", ["近い","普通","遠い"], index=["近い","普通","遠い"].index(cur["med_level"]))
    with c3:
        cur["security_level"] = st.selectbox("治安", ["良い","普通","悪い"], index=["良い","普通","悪い"].index(cur["security_level"]))
        cur["hazard_level"]   = st.selectbox("災害リスク（ハザード）", ["低い","中","高"], index=["低い","中","高"].index(cur["hazard_level"]))
        cur["park_level"]     = st.selectbox("公園・緑地（子育て環境）", ["充実","普通","乏しい"], index=["充実","普通","乏しい"].index(cur["park_level"]))
        cur["noise_level"]    = st.selectbox("騒音", ["静か","普通","うるさい"], index=["静か","普通","うるさい"].index(cur["noise_level"]))

with st.expander("広さ・間取り", expanded=True):
    c1,c2,c3 = st.columns(3)
    with c1:
        cur["area_m2"] = st.number_input("専有面積（㎡）", 0, 300, float(cur["area_m2"]))
        cur["living_jyo"] = st.number_input("リビングの広さ（帖）", 0, 50, int(cur["living_jyo"]))
        cur["layout_type"] = st.selectbox("間取りタイプ", ["田の字","ワイドスパン","センターイン","その他"], index=["田の字","ワイドスパン","センターイン","その他"].index(cur["layout_type"]))
    with c2:
        cur["storage_level"] = st.selectbox("収納量（WIC・SIC含む総合）", ["多い","普通","少ない"], index=["多い","普通","少ない"].index(cur["storage_level"]))
        cur["ceiling_level"] = st.selectbox("天井高", ["高い","普通","低い"], index=["高い","普通","低い"].index(cur["ceiling_level"]))
        cur["balcony_aspect"] = st.selectbox("バルコニー向き", ["N","NE","E","SE","S","SW","W","NW"], index=["N","NE","E","SE","S","SW","W","NW"].index(cur["balcony_aspect"]))
    with c3:
        cur["balcony_depth_m"] = st.number_input("バルコニー奥行（m）", 0.0, 5.0, float(cur["balcony_depth_m"]), step=0.1)
        cur["sun_wind_level"] = st.selectbox("採光・通風", ["良い","普通","悪い"], index=["良い","普通","悪い"].index(cur["sun_wind_level"]))
        cur["hall_flow_level"] = st.selectbox("廊下幅・家事動線効率", ["良い","普通","悪い"], index=["良い","普通","悪い"].index(cur["hall_flow_level"]))

with st.expander("専有部分スペック（ある/ない）", expanded=False):
    st.caption("【キッチン】")
    k1,k2,k3,k4,k5 = st.columns(5)
    with k1: cur["k_dishwasher"] = st.checkbox("食洗機", value=bool(cur["k_dishwasher"]))
    with k2: cur["k_purifier"] = st.checkbox("浄水器／整水器", value=bool(cur["k_purifier"]))
    with k3: cur["k_disposer"] = st.checkbox("ディスポーザー", value=bool(cur["k_disposer"]))
    with k4: cur["k_highend_cooktop"] = st.checkbox("高機能コンロ（IH/高火力）", value=bool(cur["k_highend_cooktop"]))
    with k5: cur["k_bi_oven"] = st.checkbox("ビルトインオーブン", value=bool(cur["k_bi_oven"]))

    st.caption("【バスルーム】")
    b1,b2,b3,b4,b5 = st.columns(5)
    with b1: cur["b_dryer"] = st.checkbox("浴室暖房乾燥機", value=bool(cur["b_dryer"]))
    with b2: cur["b_reheating"] = st.checkbox("追い焚き機能", value=bool(cur["b_reheating"]))
    with b3: cur["b_mist_sauna"] = st.checkbox("ミストサウナ", value=bool(cur["b_mist_sauna"]))
    with b4: cur["b_tv"] = st.checkbox("浴室テレビ", value=bool(cur["b_tv"]))
    with b5: cur["b_window"] = st.checkbox("浴室に窓", value=bool(cur["b_window"]))

    st.caption("【暖房・空調】")
    h1,h2 = st.columns(2)
    with h1: cur["h_floorheat"] = st.checkbox("床暖房", value=bool(cur["h_floorheat"]))
    with h2: cur["h_aircon_built"] = st.checkbox("エアコン（備付）", value=bool(cur["h_aircon_built"]))

    st.caption("【窓・建具】")
    w1,w2,w3,w4 = st.columns(4)
    with w1: cur["w_multi"] = st.checkbox("複層ガラス", value=bool(cur["w_multi"]))
    with w2: cur["w_low_e"] = st.checkbox("Low-Eガラス", value=bool(cur["w_low_e"]))
    with w3: cur["w_double_sash"] = st.checkbox("二重サッシ", value=bool(cur["w_double_sash"]))
    with w4: cur["w_premium_doors"] = st.checkbox("建具ハイグレード（鏡面等）", value=bool(cur["w_premium_doors"]))

    st.caption("【収納】")
    s1,s2,s3,s4,s5 = st.columns(5)
    with s1: cur["s_allrooms"] = st.checkbox("全居室収納", value=bool(cur["s_allrooms"]))
    with s2: cur["s_wic"] = st.checkbox("WIC", value=bool(cur["s_wic"]))
    with s3: cur["s_sic"] = st.checkbox("SIC", value=bool(cur["s_sic"]))
    with s4: cur["s_pantry"] = st.checkbox("パントリー", value=bool(cur["s_pantry"]))
    with s5: cur["s_linen"] = st.checkbox("リネン庫", value=bool(cur["s_linen"]))

    st.caption("【セキュリティ・通信】")
    t1,t2,t3 = st.columns(3)
    with t1: cur["sec_tvphone"] = st.checkbox("TVモニター付インターホン", value=bool(cur["sec_tvphone"]))
    with t2: cur["sec_sensor"] = st.checkbox("玄関センサーライト", value=bool(cur["sec_sensor"]))
    with t3: cur["net_ftth"] = st.checkbox("光配線方式（各戸まで）", value=bool(cur["net_ftth"]))

with st.expander("管理・共用部", expanded=False):
    m1,m2,m3,m4 = st.columns(4)
    with m1:
        cur["c_box"] = st.checkbox("宅配ボックス", value=bool(cur["c_box"]))
        cur["c_parking"] = st.selectbox("駐車場形態", ["平置き","機械式","なし"], index=["平置き","機械式","なし"].index(cur["c_parking"]))
    with m2:
        cur["c_gomi24"] = st.checkbox("24時間ゴミ出し", value=bool(cur["c_gomi24"]))
        cur["c_seismic"] = st.checkbox("免震・制震構造", value=bool(cur["c_seismic"]))
    with m3:
        cur["c_security"] = st.checkbox("オートロック等セキュリティ", value=bool(cur["c_security"]))
        cur["c_design_level"] = st.selectbox("外観・エントランスのデザイン", ["良い","普通","弱い"], index=["良い","普通","弱い"].index(cur["c_design_level"]))
    with m4:
        cur["c_ev_count"] = st.number_input("エレベーター台数（基数）", 0, 20, int(cur["c_ev_count"]))
        cur["c_pet_ok"] = st.checkbox("ペット飼育可", value=bool(cur["c_pet_ok"]))

if st.button("③ 現状スコアリングを保存"):
    payload["current_home"] = cur
    save_client(client_id, payload)
    st.success("保存しました。")

st.divider()

# ============================================
# ④ 希望条件（◎/○/△/×）
# ============================================
st.header("④ 希望条件（◎=必要／○=あったほうがよい／△=どちらでもよい／×=なくてよい）")

CHO = {"◎ 必要":"must","○ あったほうがよい":"want","△ どちらでもよい":"neutral","× なくてよい":"no_need"}

wish = payload.get("wish", {})

def wish_select(label, key):
    current = wish.get(key, "neutral")
    current_label = [k for k,v in CHO.items() if v==current][0] if current in CHO.values() else "△ どちらでもよい"
    sel = st.selectbox(label, list(CHO.keys()), index=list(CHO.keys()).index(current_label), key=f"wish-{key}")
    wish[key] = CHO[sel]

with st.expander("立地（資産性）", expanded=True):
    wish_select("最寄駅まで近いこと", "loc_walk")
    wish_select("複数路線利用できること", "loc_lines")
    wish_select("職場アクセスが良いこと", "loc_access")
    wish_select("商業施設の充実", "loc_shop")
    wish_select("教育環境の良さ", "loc_edu")
    wish_select("医療アクセスの良さ", "loc_med")
    wish_select("治安の良さ", "loc_security")
    wish_select("災害リスクが低いこと", "loc_hazard_low")
    wish_select("公園・緑地の充実", "loc_park")
    wish_select("静かな環境", "loc_silent")

with st.expander("広さ・間取り", expanded=False):
    wish_select("専有面積の広さ", "sz_area")
    wish_select("リビングの広さ", "sz_living")
    wish_select("優れた間取り（ワイドスパン等）", "sz_layout")
    wish_select("収納量（WIC/SIC等）の充実", "sz_storage")
    wish_select("天井高が高い", "sz_ceiling")
    wish_select("日当たり（向き）の良さ", "sz_aspect")
    wish_select("バルコニー奥行の余裕", "sz_balcony_depth")
    wish_select("採光・通風の良さ", "sz_sun_wind")
    wish_select("廊下幅・家事動線の良さ", "sz_flow")

with st.expander("スペック（専有部分）", expanded=False):
    st.caption("【キッチン】")
    for k, lab in [
        ("k_dishwasher","食洗機"),
        ("k_purifier","浄水器／整水器"),
        ("k_disposer","ディスポーザー"),
        ("k_highend_cooktop","高機能コンロ（IH/高火力）"),
        ("k_bi_oven","ビルトインオーブン"),
    ]:
        wish_select(lab, k)
    st.caption("【バスルーム】")
    for k, lab in [
        ("b_dryer","浴室暖房乾燥機"),
        ("b_reheating","追い焚き機能"),
        ("b_mist_sauna","ミストサウナ"),
        ("b_tv","浴室テレビ"),
        ("b_window","浴室に窓"),
    ]:
        wish_select(lab, k)
    st.caption("【暖房・空調】")
    for k, lab in [
        ("h_floorheat","床暖房"),
        ("h_aircon_built","エアコン（備付）"),
    ]:
        wish_select(lab, k)
    st.caption("【窓・建具】")
    for k, lab in [
        ("w_multi","複層ガラス"),
        ("w_low_e","Low-Eガラス"),
        ("w_double_sash","二重サッシ"),
        ("w_premium_doors","建具ハイグレード（鏡面等）"),
    ]:
        wish_select(lab, k)
    st.caption("【収納】")
    for k, lab in [
        ("s_allrooms","全居室収納"),
        ("s_wic","WIC"),
        ("s_sic","SIC"),
        ("s_pantry","パントリー"),
        ("s_linen","リネン庫"),
    ]:
        wish_select(lab, k)
    st.caption("【セキュリティ・通信】")
    for k, lab in [
        ("sec_tvphone","TVモニター付インターホン"),
        ("sec_sensor","玄関センサーライト"),
        ("net_ftth","光配線方式（各戸まで）"),
    ]:
        wish_select(lab, k)

with st.expander("管理・共有部・その他", expanded=False):
    for key, label in [
        ("c_concierge","コンシェルジュサービス"), ("c_box","宅配ボックス"), ("c_guest","ゲストルーム"),
        ("c_lounge_kids","ラウンジ/キッズルーム"), ("c_gym_pool","ジム/プール"),
        ("c_parking_type","駐車場形態（平置き等）"), ("c_gomi24","24時間ゴミ出し"), ("c_seismic","免震・制震構造"),
        ("c_security","強いセキュリティ（有人/カメラ等）"), ("c_design","外観・エントランスのデザイン"),
        ("c_ev_enough","エレベーター台数の十分さ"), ("c_brand_tower","ブランド/タワーの属性"),
        ("c_pet_ok","ペット可"), ("c_ltp_plan","長期修繕/資金計画の良さ"), ("c_fee_reasonable","修繕積立金の妥当性"),
        ("c_mgmt","管理体制の良さ"), ("c_history","共用部修繕履歴の良さ"), ("c_yield","収益性（将来の利回り）")
    ]:
        wish_select(label, key)

if st.button("④ 希望条件を保存"):
    payload["wish"] = wish
    save_client(client_id, payload)
    st.success("保存しました。")

st.divider()

# ============================================
# ⑤ 物件比較（別ページへ遷移）
# ============================================
st.header("⑤ 物件比較（別ページ）")
st.caption("このページではプロフィールを整えます。比較は別ページで、物件を横並びで入力・偏差値表示します。")

# 比較ページへのリンク（client パラメータ付与）
link_label = "↔ 物件比較ページを開く"
base = "3_compare.py"
if pin_in:
    url = f"./{base}?client={client_id}&pin={pin_in}"
else:
    url = f"./{base}?client={client_id}"

try:
    st.page_link(base, label=link_label, icon="↔️")
except Exception:
    st.markdown(f"[{link_label}]({url})")