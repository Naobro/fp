# -*- coding: utf-8 -*-
import os, json, tempfile
from datetime import datetime
from pathlib import Path

import streamlit as st
from fpdf import FPDF

st.set_page_config(page_title="理想の住まいへのロードマップ", layout="wide")

# ====== ここだけお客様ごとに変更 ======
CLIENT_ID = "c-XXXXXX"   # ← お客様IDに置換（例: "c-b62z51"）
# =====================================

# =========================
# データ入出力ユーティリティ
# =========================
DATA_DIR = Path("data/clients")
DATA_DIR.mkdir(parents=True, exist_ok=True)

def _client_path(cid: str) -> Path:
    return DATA_DIR / f"{cid}.json"

def load_or_init_client(cid: str):
    f = _client_path(cid)
    if not f.exists():
        payload = {"meta": {"id": cid, "name": ""}}
        f.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload
    return json.loads(f.read_text(encoding="utf-8"))

def save_client(cid: str, data: dict):
    _client_path(cid).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# 偏差値換算（平均3.0→50、1.0→30、5.0→70）
def to_hensachi(avg_1to5: float) -> float:
    return round(50 + (avg_1to5 - 3.0) * 10, 1)

# =========================
# 本体（直アクセス専用）
# =========================
payload = load_or_init_client(CLIENT_ID)

st.title("理想の住まいへのロードマップ")
header_name = payload.get("meta",{}).get("name") or "お客様"
st.success(f"{header_name} 専用ページ")

# ============================================
# ① ヒアリング（5W2H）＋ PDF出力
# ============================================
st.header("① ヒアリング（5W2H）")

TO_EMAIL_DEFAULT = payload.get("hearing",{}).get("pdf_recipient","naoki.nishiyama@terass.com")
base_defaults = {
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
    # トレードオフ（大カテゴリー5本）
    "prio_price": 3, "prio_location": 3, "prio_size_layout": 3, "prio_spec": 3, "prio_mgmt": 3,
    # 任意チェック
    "spec_parking": False, "spec_bicycle": False, "spec_ev": False, "spec_pet": False,
    "spec_barrierfree": False, "spec_security": False, "spec_disaster": False,
    "spec_mgmt_good": False, "spec_fee_ok": False, "spec_free": "",
    "contact_pref": "", "share_method": "", "pdf_recipient": TO_EMAIL_DEFAULT,
}

# セッション（編集しながら保持）
if "hearing_data" not in st.session_state:
    st.session_state["hearing_data"] = payload.get("hearing", base_defaults.copy())
else:
    for k, v in base_defaults.items():
        st.session_state["hearing_data"].setdefault(k, v)

hearing = st.session_state["hearing_data"]

with st.form("hearing_form", clear_on_submit=False):
    st.markdown("#### 基礎情報")
    c1, c2, c3 = st.columns(3)
    with c1:
        hearing["name"]      = st.text_input("お名前", value=hearing["name"])
        hearing["now_area"]  = st.text_input("現在の居住エリア・駅", value=hearing["now_area"])
    with c2:
        hearing["now_years"] = st.number_input("居住年数（年）", 0, 100, int(hearing["now_years"]))
        hearing["is_owner"]  = st.selectbox("持ち家・賃貸", ["賃貸", "持ち家"], index=0 if hearing["is_owner"]=="賃貸" else 1)
    with c3:
        hearing["housing_cost"] = st.number_input("住居費（万円/月）", 0, 200, int(hearing["housing_cost"]))
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
    # 大カテゴリー統一：価格 / 立地 / 広さ・間取り / スペック / 管理・共有部・その他
    p1, p2, p3, p4, p5 = st.columns(5)
    with p1: hearing["prio_price"]       = st.selectbox("価格", [1,2,3,4,5], index=int(hearing["prio_price"])-1)
    with p2: hearing["prio_location"]    = st.selectbox("立地", [1,2,3,4,5], index=int(hearing["prio_location"])-1)
    with p3: hearing["prio_size_layout"] = st.selectbox("広さ・間取り", [1,2,3,4,5], index=int(hearing["prio_size_layout"])-1)
    with p4: hearing["prio_spec"]        = st.selectbox("スペック（専有）", [1,2,3,4,5], index=int(hearing["prio_spec"])-1)
    with p5: hearing["prio_mgmt"]        = st.selectbox("管理・共有部・その他", [1,2,3,4,5], index=int(hearing["prio_mgmt"])-1)

    st.divider()

    st.markdown("#### 連絡・共有")
    cc1, cc2, cc3 = st.columns(3)
    with cc1: hearing["contact_pref"] = st.text_input("希望連絡手段・時間帯", value=hearing["contact_pref"])
    with cc2: hearing["share_method"] = st.text_input("資料共有（LINE／メール 等）", value=hearing["share_method"])
    with cc3: hearing["pdf_recipient"] = st.text_input("PDF送付先メール", value=hearing.get("pdf_recipient", TO_EMAIL_DEFAULT))

    submitted = st.form_submit_button("保存 / PDF作成")

# PDF生成 & 保存
if submitted:
    payload["hearing"] = hearing
    payload.setdefault("meta", {}).update({"name": hearing.get("name","")})
    save_client(CLIENT_ID, payload)
    st.success("ヒアリング内容を保存しました。PDFを生成します。")

    # フォント準備
    import urllib.request
    REG_NAME = "NotoSansJP-Regular.ttf"
    BLD_NAME = "NotoSansJP-Bold.ttf"
    RAW_REG = "https://raw.githubusercontent.com/Naobro/fp/main/fonts/NotoSansJP-Regular.ttf"
    RAW_BLD = "https://raw.githubusercontent.com/Naobro/fp/main/fonts/NotoSansJP-Bold.ttf"

    def ensure_fonts_dir() -> Path:
        candidates = [Path(__file__).resolve().parent / "fonts", Path.cwd() / "fonts",
                      Path("/mount/src/fp/fonts"), Path("/app/fonts")]
        for d in candidates:
            if (d / REG_NAME).exists() and (d / BLD_NAME).exists():
                return d.resolve()
        for d in candidates:
            if (d / REG_NAME).exists():
                (d / BLD_NAME).write_bytes((d / REG_NAME).read_bytes()); return d.resolve()
        tmp = Path(tempfile.mkdtemp(prefix="fonts_"))
        urllib.request.urlretrieve(RAW_REG, str(tmp / REG_NAME))
        try: urllib.request.urlretrieve(RAW_BLD, str(tmp / BLD_NAME))
        except Exception: (tmp / BLD_NAME).write_bytes((tmp / REG_NAME).read_bytes())
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
        pair("不満な点", hearing["dissat_free"])

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
# ② 現状把握（現在の住宅の基礎情報）
# ============================================
st.header("② 現状把握（現在の住宅の基礎情報）")

if "baseline" not in payload:
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
        _corner = st.selectbox("角部屋", ["不明","いいえ","はい"],
                               index=0 if b.get("corner") is None else (2 if b.get("corner") else 1))
        _inner  = st.selectbox("内廊下", ["不明","いいえ","はい"],
                               index=0 if b.get("inner_corridor") is None else (2 if b.get("inner_corridor") else 1))
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
        b["wife_commute_min"]    = st.number_input("奥様 通勤（分）", 0, 180, int(b.get("wife_commute_min",40)))

    if st.form_submit_button("② 現状把握を保存"):
        b["corner"] = True if _corner=="はい" else (False if _corner=="いいえ" else None)
        b["inner_corridor"] = True if _inner=="はい" else (False if _inner=="いいえ" else None)
        payload["baseline"] = b
        save_client(CLIENT_ID, payload)
        st.success("保存しました。")

st.divider()

# ============================================
# ③ 現在の住居スコアリング
# ============================================
st.header("③ 現在の住居スコアリング")

if "current_home" not in payload:
    payload["current_home"] = {
        # 立地
        "walk_min": b.get("walk_min",10), "multi_lines": 1, "access_min": 30,
        "shop_level": "普通", "edu_level": "普通", "med_level": "普通",
        "security_level": "普通", "hazard_level": "中",
        "park_level": "普通", "noise_level": "普通",
        # 広さ・間取り
        "area_m2": b.get("area_m2",60), "living_jyo": 12,
        "layout_type": "田の字", "storage_level": "普通", "ceiling_level": "普通",
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
        cur["walk_min"] = st.number_input("最寄駅までの徒歩分数", 0, 60, cur["walk_min"])
        cur["multi_lines"] = st.number_input("複数路線利用の可否（本数）", 0, 10, cur["multi_lines"])
        cur["access_min"] = st.number_input("職場までのアクセス時間（分）", 0, 180, cur["access_min"])
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
        cur["area_m2"] = st.number_input("専有面積（㎡）", 0, 300, cur["area_m2"])
        cur["living_jyo"] = st.number_input("リビングの広さ（帖）", 0, 50, cur["living_jyo"])
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
    with k1: cur["k_dishwasher"] = st.checkbox("食洗機", value=cur["k_dishwasher"])
    with k2: cur["k_purifier"] = st.checkbox("浄水器／整水器", value=cur["k_purifier"])
    with k3: cur["k_disposer"] = st.checkbox("ディスポーザー", value=cur["k_disposer"])
    with k4: cur["k_highend_cooktop"] = st.checkbox("高機能コンロ（IH/高火力）", value=cur["k_highend_cooktop"])
    with k5: cur["k_bi_oven"] = st.checkbox("ビルトインオーブン", value=cur["k_bi_oven"])

    st.caption("【バスルーム】")
    b1,b2,b3,b4,b5 = st.columns(5)
    with b1: cur["b_dryer"] = st.checkbox("浴室暖房乾燥機", value=cur["b_dryer"])
    with b2: cur["b_reheating"] = st.checkbox("追い焚き機能", value=cur["b_reheating"])
    with b3: cur["b_mist_sauna"] = st.checkbox("ミストサウナ", value=cur["b_mist_sauna"])
    with b4: cur["b_tv"] = st.checkbox("浴室テレビ", value=cur["b_tv"])
    with b5: cur["b_window"] = st.checkbox("浴室に窓", value=cur["b_window"])

    st.caption("【暖房・空調】")
    h1,h2 = st.columns(2)
    with h1: cur["h_floorheat"] = st.checkbox("床暖房", value=cur["h_floorheat"])
    with h2: cur["h_aircon_built"] = st.checkbox("エアコン（備付）", value=cur["h_aircon_built"])

    st.caption("【窓・建具】")
    w1,w2,w3,w4 = st.columns(4)
    with w1: cur["w_multi"] = st.checkbox("複層ガラス", value=cur["w_multi"])
    with w2: cur["w_low_e"] = st.checkbox("Low-Eガラス", value=cur["w_low_e"])
    with w3: cur["w_double_sash"] = st.checkbox("二重サッシ", value=cur["w_double_sash"])
    with w4: cur["w_premium_doors"] = st.checkbox("建具ハイグレード（鏡面等）", value=cur["w_premium_doors"])

    st.caption("【収納】")
    s1,s2,s3,s4,s5 = st.columns(5)
    with s1: cur["s_allrooms"] = st.checkbox("全居室収納", value=cur["s_allrooms"])
    with s2: cur["s_wic"] = st.checkbox("WIC", value=cur["s_wic"])
    with s3: cur["s_sic"] = st.checkbox("SIC", value=cur["s_sic"])
    with s4: cur["s_pantry"] = st.checkbox("パントリー", value=cur["s_pantry"])
    with s5: cur["s_linen"] = st.checkbox("リネン庫", value=cur["s_linen"])

    st.caption("【セキュリティ・通信】")
    t1,t2,t3 = st.columns(3)
    with t1: cur["sec_tvphone"] = st.checkbox("TVモニター付インターホン", value=cur["sec_tvphone"])
    with t2: cur["sec_sensor"] = st.checkbox("玄関センサーライト", value=cur["sec_sensor"])
    with t3: cur["net_ftth"] = st.checkbox("光配線方式（各戸まで）", value=cur["net_ftth"])

with st.expander("管理・共用部", expanded=False):
    m1,m2,m3,m4 = st.columns(4)
    with m1:
        cur["c_box"] = st.checkbox("宅配ボックス", value=cur["c_box"])
        cur["c_parking"] = st.selectbox("駐車場形態", ["平置き","機械式","なし"], index=["平置き","機械式","なし"].index(cur["c_parking"]))
    with m2:
        cur["c_gomi24"] = st.checkbox("24時間ゴミ出し", value=cur["c_gomi24"])
        cur["c_seismic"] = st.checkbox("免震・制震構造", value=cur["c_seismic"])
    with m3:
        cur["c_security"] = st.checkbox("オートロック等セキュリティ", value=cur["c_security"])
        cur["c_design_level"] = st.selectbox("外観・エントランスのデザイン", ["良い","普通","弱い"], index=["良い","普通","弱い"].index(cur["c_design_level"]))
    with m4:
        cur["c_ev_count"] = st.number_input("エレベーター台数（基数）", 0, 20, cur["c_ev_count"])
        cur["c_pet_ok"] = st.checkbox("ペット飼育可", value=cur["c_pet_ok"])

if st.button("③ 現状スコアリングを保存"):
    payload["current_home"] = cur
    save_client(CLIENT_ID, payload)
    st.success("保存しました。")

st.divider()

# ============================================
# ④ 希望条件（◎/○/△/×）
# ============================================
st.header("④ 希望条件（◎=必要／○=あったほうがよい／△=どちらでもよい／×=なくてよい）")

CHO = {"◎ 必要":"must","○ あったほうがよい":"want","△ どちらでもよい":"neutral","× なくてよい":"no_need"}
if "wish" not in payload: payload["wish"] = {}
wish = payload["wish"]

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
    for k in ["k_dishwasher","k_purifier","k_disposer","k_highend_cooktop","k_bi_oven"]:
        wish_select({"k_dishwasher":"食洗機","k_purifier":"浄水器／整水器","k_disposer":"ディスポーザー",
                     "k_highend_cooktop":"高機能コンロ（IH/高火力）","k_bi_oven":"ビルトインオーブン"}[k], k)
    st.caption("【バスルーム】")
    for k in ["b_dryer","b_reheating","b_mist_sauna","b_tv","b_window"]:
        wish_select({"b_dryer":"浴室暖房乾燥機","b_reheating":"追い焚き機能","b_mist_sauna":"ミストサウナ",
                     "b_tv":"浴室テレビ","b_window":"浴室に窓"}[k], k)
    st.caption("【暖房・空調】")
    for k in ["h_floorheat","h_aircon_built"]:
        wish_select({"h_floorheat":"床暖房","h_aircon_built":"エアコン（備付）"}[k], k)
    st.caption("【窓・建具】")
    for k in ["w_multi","w_low_e","w_double_sash","w_premium_doors"]:
        wish_select({"w_multi":"複層ガラス","w_low_e":"Low-Eガラス","w_double_sash":"二重サッシ",
                     "w_premium_doors":"建具ハイグレード（鏡面等）"}[k], k)
    st.caption("【収納】")
    for k in ["s_allrooms","s_wic","s_sic","s_pantry","s_linen"]:
        wish_select({"s_allrooms":"全居室収納","s_wic":"WIC","s_sic":"SIC","s_pantry":"パントリー","s_linen":"リネン庫"}[k], k)
    st.caption("【セキュリティ・通信】")
    for k in ["sec_tvphone","sec_sensor","net_ftth"]:
        wish_select({"sec_tvphone":"TVモニター付インターホン","sec_sensor":"玄関センサーライト","net_ftth":"光配線方式（各戸まで）"}[k], k)

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
    save_client(CLIENT_ID, payload)
    st.success("保存しました。")

st.divider()

# ============================================
# ⑤ 物件比較（このページ内で開く：現住居=偏差値50が基準）
# ============================================
st.header("⑤ 物件比較")
st.caption("このページ内で、現住居=偏差値50 を基準に内見物件との比較を行います。")

# ---- 比較UIの表示トグル ----
if "show_compare" not in st.session_state:
    st.session_state["show_compare"] = False

col_btn = st.columns([1,2,1])
with col_btn[1]:
    if st.button("↔ このページ内で 物件比較ツール を表示", use_container_width=True):
        st.session_state["show_compare"] = True

# ---- ユーティリティ（3_compare.py と同等）----
def map3(x, good="良い", mid="普通", bad="悪い"):
    if x == good or x in ["充実","近い","静か","低い"]:
        return 5.0
    if x == mid:
        return 3.0
    return 2.5

def bool_score(b): return 5.0 if b else 2.5

def price_score(price_m):
    if price_m <= 5000: return 4.0
    if price_m <= 8000: return 3.5
    if price_m <= 10000: return 3.0
    return 2.5

def fee_score(fee_yen):
    if fee_yen == 0: return 3.0
    if fee_yen <= 15000: return 4.0
    if fee_yen <= 25000: return 3.5
    if fee_yen <= 35000: return 3.0
    return 2.5

def tsubo_score(tsubo_m):
    if tsubo_m == 0: return 3.0
    if tsubo_m <= 300: return 4.0
    if tsubo_m <= 400: return 3.5
    if tsubo_m <= 500: return 3.0
    return 2.5

def size_score(area, liv):
    base = 3.0
    if area >= 70: base += 0.5
    if liv >= 14: base += 0.5
    return min(5.0, base)

def score_location_from_current(cur):
    return (
        (5.0 if cur.get("walk_min",999)<=5 else 4.0 if cur.get("walk_min",999)<=10 else 3.0 if cur.get("walk_min",999)<=15 else 2.5) +
        (5.0 if cur.get("multi_lines",0)>=3 else 4.0 if cur.get("multi_lines",0)==2 else 3.0 if cur.get("multi_lines",0)==1 else 2.5) +
        (5.0 if cur.get("access_min",999)<=20 else 4.0 if cur.get("access_min",999)<=35 else 3.0 if cur.get("access_min",999)<=50 else 2.5) +
        map3(cur.get("shop_level","普通"),"充実","普通","乏しい") +
        map3(cur.get("edu_level","普通"),"良い","普通","弱い") +
        map3(cur.get("med_level","普通"),"近い","普通","遠い") +
        map3(cur.get("security_level","普通"),"良い","普通","悪い") +
        map3(cur.get("hazard_level","中"),"低い","中","高") +
        map3(cur.get("park_level","普通"),"充実","普通","乏しい") +
        map3(cur.get("noise_level","普通"),"静か","普通","うるさい")
    ) / 10

def score_size_from_current(cur):
    lay = 3.5 if cur.get("layout_type") in ["ワイドスパン","センターイン"] else 3.0
    return (
        size_score(cur.get("area_m2",0), cur.get("living_jyo",0)) +
        lay +
        map3(cur.get("storage_level","普通"),"多い","普通","少ない") +
        map3(cur.get("ceiling_level","普通"),"高い","普通","低い") +
        3.0 +
        (4.0 if cur.get("balcony_depth_m",0)>=1.5 else 3.0) +
        map3(cur.get("sun_wind_level","普通"),"良い","普通","悪い") +
        map3(cur.get("hall_flow_level","普通"),"良い","普通","悪い")
    ) / 8

def score_spec_from_current(cur):
    keys = [
        "k_dishwasher","k_purifier","k_disposer","k_highend_cooktop","k_bi_oven",
        "b_dryer","b_reheating","b_mist_sauna","b_tv","b_window",
        "h_floorheat","h_aircon_built",
        "w_multi","w_low_e","w_double_sash","w_premium_doors",
        "s_allrooms","s_wic","s_sic","s_pantry","s_linen",
        "sec_tvphone","sec_sensor","net_ftth"
    ]
    pts = [bool_score(bool(payload.get("current_home",{}).get(k, False))) for k in keys]
    return sum(pts)/len(pts) if pts else 3.0

def score_mgmt_from_current(cur):
    pts = 0; n = 0
    for k in ["c_box","c_gomi24","c_seismic","c_security","c_pet_ok"]:
        if k in cur:
            n += 1; pts += 1 if cur[k] else 0
    ratio = (pts/n) if n else 0.5
    extra = 0.0
    dl = cur.get("c_design_level","普通")
    if dl == "良い": extra += 0.5
    elif dl == "弱い": extra -= 0.5
    ev = cur.get("c_ev_count",0)
    if ev >= 3: extra += 0.2
    pk = cur.get("c_parking","なし")
    if pk == "平置き": extra += 0.2
    elif pk == "機械式": extra += 0.1
    base = 2.5 + ratio*2.5 + extra
    return max(1.0, min(5.0, base))

def score_location_from_input(t):
    walk,lines,acc,shop,edu,med,sec,haz,park,noise = t
    return (
        (5.0 if walk<=5 else 4.0 if walk<=10 else 3.0 if walk<=15 else 2.5) +
        (5.0 if lines>=3 else 4.0 if lines==2 else 3.0 if lines==1 else 2.5) +
        (5.0 if acc<=20 else 4.0 if acc<=35 else 3.0 if acc<=50 else 2.5) +
        map3(shop,"充実","普通","乏しい") +
        map3(edu,"良い","普通","弱い") +
        map3(med,"近い","普通","遠い") +
        map3(sec,"良い","普通","悪い") +
        map3(haz,"低い","中","高") +
        map3(park,"充実","普通","乏しい") +
        map3(noise,"静か","普通","うるさい")
    ) / 10

def score_size_from_input(t):
    area, liv, layout, storage, ceil, aspect, depth, sunwind, flow = t
    lay = 3.5 if layout in ["ワイドスパン","センターイン"] else 3.0
    return (
        size_score(area, liv) + lay +
        map3(storage,"多い","普通","少ない") +
        map3(ceil,"高い","普通","低い") +
        3.0 + (4.0 if depth>=1.5 else 3.0) +
        map3(sunwind,"良い","普通","悪い") +
        map3(flow,"良い","普通","悪い")
    ) / 8

def score_spec_from_input(sp):
    keys = ["dw","disp","pur","oven","cook","dry","reh","sauna","btv","bwin",
            "fh","ac","lowe","twin","multi","doors",
            "allst","wic","sic","pantry","linen","video","sensor","ftth"]
    return sum(bool_score(sp.get(k, False)) for k in keys)/len(keys)

def score_mgmt_from_input(m):
    pts = 0; n = 0
    for k in ["concierge","box","guest","lounge","gym","pool","gomi","seismic","sec","brand","pet"]:
        n += 1; pts += 1 if m.get(k, False) else 0
    ratio = pts/n if n else 0.5
    extra = 0.0
    dl = m.get("design","普通")
    if dl == "良い": extra += 0.5
    elif dl == "弱い": extra -= 0.5
    ev = m.get("ev",0)
    if ev >= 3: extra += 0.2
    pk = m.get("parking","なし")
    if pk == "平置き": extra += 0.2
    elif pk == "機械式": extra += 0.1
    base = 2.5 + ratio*2.5 + extra
    return max(1.0, min(5.0, base))

if st.session_state["show_compare"]:
    st.subheader("比較対象の入力（A/B/C…）")
    # ---- 基準（現住居）スコア算出 ----
    cur = payload.get("current_home", {})
    w_price = int(payload.get("hearing",{}).get("prio_price",3))
    w_location = int(payload.get("hearing",{}).get("prio_location",3))
    w_size = int(payload.get("hearing",{}).get("prio_size_layout",3))
    w_spec = int(payload.get("hearing",{}).get("prio_spec",3))
    w_mgmt = int(payload.get("hearing",{}).get("prio_mgmt",3))
    wsum = w_price + w_location + w_size + w_spec + w_mgmt

    s_price_cur = 3.0
    s_loc_cur   = score_location_from_current(cur) if cur else 3.0
    s_size_cur  = score_size_from_current(cur) if cur else 3.0
    s_spec_cur  = score_spec_from_current(cur) if cur else 3.0
    s_mgmt_cur  = score_mgmt_from_current(cur) if cur else 3.0
    avg_cur_w = (s_price_cur*w_price + s_loc_cur*w_location + s_size_cur*w_size + s_spec_cur*w_spec + s_mgmt_cur*w_mgmt) / (wsum or 1)
    st.info(f"基準：現住居の重み付き平均 = {avg_cur_w:.2f}（偏差値はここを50とします）")

    # ---- 入力行数 ----
    if "compare_rows" not in st.session_state:
        st.session_state["compare_rows"] = 3
    rows = st.session_state["compare_rows"]

    cols = st.columns(rows)
    names = []
    for i in range(rows):
        with cols[i]:
            names.append(st.text_input(f"物件名 {chr(65+i)}", value=f"物件{chr(65+i)}", key=f"name_{i}"))

    st.markdown("### ① 価格")
    c_price = st.columns(rows)
    price_val = []; tsubo_val = []; fee_val = []; renov_val = []
    for i in range(rows):
        with c_price[i]:
            price_val.append(st.number_input(f"{names[i]}：売出価格（万円）", 0, 50000, 0, key=f"price_{i}"))
            tsubo_val.append(st.number_input(f"{names[i]}：坪単価（万円/坪）", 0, 2000, 0, key=f"tsubo_{i}"))
            fee_val.append(st.number_input(f"{names[i]}：管理費等（月額・円）", 0, 200000, 0, key=f"fee_{i}"))
            renov_val.append(st.number_input(f"{names[i]}：追加リフォーム費用（万円）", 0, 5000, 0, key=f"renov_{i}"))

    st.markdown("### ② 立地（資産性）")
    loc_inputs = []
    for i in range(rows):
        c1,c2,c3 = st.columns(3)
        with c1:
            walk = st.number_input(f"{names[i]}：最寄徒歩（分）", 0, 60, 10, key=f"walk_{i}")
            lines = st.number_input(f"{names[i]}：複線数（本）", 0, 10, 1, key=f"lines_{i}")
            acc = st.number_input(f"{names[i]}：職場アクセス（分）", 0, 180, 30, key=f"acc_{i}")
        with c2:
            shop = st.selectbox(f"{names[i]}：商業施設", ["充実","普通","乏しい"], key=f"shop_{i}")
            edu = st.selectbox(f"{names[i]}：教育", ["良い","普通","弱い"], key=f"edu_{i}")
            med = st.selectbox(f"{names[i]}：医療", ["近い","普通","遠い"], key=f"med_{i}")
        with c3:
            sec = st.selectbox(f"{names[i]}：治安", ["良い","普通","悪い"], key=f"sec_{i}")
            haz = st.selectbox(f"{names[i]}：災害", ["低い","中","高"], key=f"haz_{i}")
            park = st.selectbox(f"{names[i]}：公園・緑地", ["充実","普通","乏しい"], key=f"park_{i}")
            noise = st.selectbox(f"{names[i]}：騒音", ["静か","普通","うるさい"], key=f"noise_{i}")
        loc_inputs.append((walk,lines,acc,shop,edu,med,sec,haz,park,noise))

    st.markdown("### ③ 広さ・間取り")
    size_inputs = []
    for i in range(rows):
        c1,c2,c3 = st.columns(3)
        with c1:
            area = st.number_input(f"{names[i]}：専有面積（㎡）", 0, 300, 60, key=f"area_{i}")
            liv  = st.number_input(f"{names[i]}：リビング（帖）", 0, 50, 12, key=f"liv_{i}")
            layout = st.selectbox(f"{names[i]}：間取りタイプ", ["田の字","ワイドスパン","センターイン","その他"], key=f"layout_{i}")
        with c2:
            storage = st.selectbox(f"{names[i]}：収納量", ["多い","普通","少ない"], key=f"storage_{i}")
            ceil = st.selectbox(f"{names[i]}：天井高", ["高い","普通","低い"], key=f"ceil_{i}")
            aspect = st.selectbox(f"{names[i]}：バルコニー向き", ["N","NE","E","SE","S","SW","W","NW"], key=f"aspect_{i}")
        with c3:
            depth = st.number_input(f"{names[i]}：バルコニー奥行（m）", 0.0, 5.0, 1.5, step=0.1, key=f"depth_{i}")
            sunwind = st.selectbox(f"{names[i]}：採光・通風", ["良い","普通","悪い"], key=f"sunwind_{i}")
            flow = st.selectbox(f"{names[i]}：廊下幅・家事動線", ["良い","普通","悪い"], key=f"flow_{i}")
        size_inputs.append((area, liv, layout, storage, ceil, aspect, depth, sunwind, flow))

    st.markdown("### ④ スペック（専有部分）")
    spec_inputs = []
    for i in range(rows):
        k1,k2,k3,k4,k5 = st.columns(5)
        with k1:
            dw = st.checkbox(f"{names[i]}：食洗機", key=f"dw_{i}")
            disp = st.checkbox(f"{names[i]}：ディスポーザー", key=f"disp_{i}")
        with k2:
            pur = st.checkbox(f"{names[i]}：浄水器/整水器", key=f"pur_{i}")
            oven = st.checkbox(f"{names[i]}：ビルトインオーブン", key=f"oven_{i}")
        with k3:
            cook = st.checkbox(f"{names[i]}：高機能コンロ（IH/高火力）", key=f"cook_{i}")
            dryer = st.checkbox(f"{names[i]}：浴室乾燥機", key=f"dry_{i}")
        with k4:
            reheat = st.checkbox(f"{names[i]}：追い焚き", key=f"reh_{i}")
            sauna = st.checkbox(f"{names[i]}：ミストサウナ", key=f"sauna_{i}")
        with k5:
            btv = st.checkbox(f"{names[i]}：浴室TV", key=f"btv_{i}")
            bwin = st.checkbox(f"{names[i]}：浴室に窓", key=f"bwin_{i}")

        h1,h2,h3,h4 = st.columns(4)
        with h1:  fh = st.checkbox(f"{names[i]}：床暖房", key=f"fh_{i}")
        with h2:  ac = st.checkbox(f"{names[i]}：エアコン（備付）", key=f"ac_{i}")
        with h3:  lowe = st.checkbox(f"{names[i]}：Low-E", key=f"lowe_{i}")
        with h4:  twin = st.checkbox(f"{names[i]}：二重サッシ", key=f"twin_{i}")
        w1,w2 = st.columns(2)
        with w1: multi = st.checkbox(f"{names[i]}：複層ガラス", key=f"multi_{i}")
        with w2: doors = st.checkbox(f"{names[i]}：建具ハイグレード（鏡面等）", key=f"doors_{i}")

        s1,s2,s3,s4,s5 = st.columns(5)
        with s1: allst = st.checkbox(f"{names[i]}：全居室収納", key=f"allst_{i}")
        with s2: wic = st.checkbox(f"{names[i]}：WIC", key=f"wic_{i}")
        with s3: sic = st.checkbox(f"{names[i]}：SIC", key=f"sic_{i}")
        with s4: pantry = st.checkbox(f"{names[i]}：パントリー", key=f"pantry_{i}")
        with s5: linen = st.checkbox(f"{names[i]}：リネン庫", key=f"linen_{i}")

        sec1,sec2,sec3 = st.columns(3)
        with sec1: video = st.checkbox(f"{names[i]}：TVモニターインターホン", key=f"video_{i}")
        with sec2: sensor = st.checkbox(f"{names[i]}：玄関センサー", key=f"sensor_{i}")
        with sec3: ftth = st.checkbox(f"{names[i]}：光配線（各戸）", key=f"ftth_{i}")

        spec_inputs.append({
            "dw":dw, "disp":disp, "pur":pur, "oven":oven, "cook":cook,
            "dry":dryer, "reh":reheat, "sauna":sauna, "btv":btv, "bwin":bwin,
            "fh":fh, "ac":ac, "lowe":lowe, "twin":twin, "multi":multi, "doors":doors,
            "allst":allst, "wic":wic, "sic":sic, "pantry":pantry, "linen":linen,
            "video":video, "sensor":sensor, "ftth":ftth
        })

    st.markdown("### ⑤ 管理・共有部・その他")
    mgmt_inputs = []
    for i in range(rows):
        c1,c2,c3,c4 = st.columns(4)
        with c1:
            concierge = st.checkbox(f"{names[i]}：コンシェルジュ", key=f"con_{i}")
            box = st.checkbox(f"{names[i]}：宅配ボックス", key=f"box_{i}")
        with c2:
            guest = st.checkbox(f"{names[i]}：ゲストルーム", key=f"guest_{i}")
            lounge = st.checkbox(f"{names[i]}：ラウンジ/キッズ", key=f"lounge_{i}")
        with c3:
            gym = st.checkbox(f"{names[i]}：ジム", key=f"gym_{i}")
            pool = st.checkbox(f"{names[i]}：プール", key=f"pool_{i}")
        with c4:
            parking = st.selectbox(f"{names[i]}：駐車場形態", ["平置き","機械式","なし"], key=f"park_{i}")

        line2 = st.columns(4)
        with line2[0]: gomi = st.checkbox(f"{names[i]}：24hゴミ出し", key=f"gomi_{i}")
        with line2[1]: seismic = st.checkbox(f"{names[i]}：免震・制震", key=f"sei_{i}")
        with line2[2]: sec = st.checkbox(f"{names[i]}：セキュリティ強", key=f"sec_{i}")
        with line2[3]: design = st.selectbox(f"{names[i]}：外観・エントランス", ["良い","普通","弱い"], key=f"design_{i}")

        line3 = st.columns(4)
        with line3[0]: ev = st.number_input(f"{names[i]}：EV台数（基数）", 0, 20, 2, key=f"ev_{i}")
        with line3[1]: brand = st.checkbox(f"{names[i]}：ブランド/タワー属性", key=f"brand_{i}")
        with line3[2]: pet = st.checkbox(f"{names[i]}：ペット可", key=f"pet_{i}")
        with line3[3]: note = st.text_input(f"{names[i]}：備考", key=f"note_{i}")
        mgmt_inputs.append({
            "concierge":concierge,"box":box,"guest":guest,"lounge":lounge,
            "gym":gym,"pool":pool,"parking":parking,"gomi":gomi,"seismic":seismic,
            "sec":sec,"design":design,"ev":ev,"brand":brand,"pet":pet,"note":note
        })

    st.divider()

    if st.button("スコア計算・偏差値表示"):
        for i in range(rows):
            s_price = (price_score(price_val[i]) + tsubo_score(tsubo_val[i]) + fee_score(fee_val[i]))/3
            s_loc   = score_location_from_input(loc_inputs[i])
            s_size  = score_size_from_input(size_inputs[i])
            s_spec  = score_spec_from_input(spec_inputs[i])
            s_mgmt  = score_mgmt_from_input(mgmt_inputs[i])

            avg_prop = (s_price*w_price + s_loc*w_location + s_size*w_size + s_spec*w_spec + s_mgmt*w_mgmt) / (wsum or 1)
            diff = avg_prop - avg_cur_w
            hensachi = round(50 + diff*10, 1)

            c1,c2,c3,c4,c5,c6 = st.columns(6)
            with c1: st.metric(f"{names[i]}｜価格", f"{s_price:.1f}/5", f"{s_price - s_price_cur:+.1f}")
            with c2: st.metric(f"{names[i]}｜立地", f"{s_loc:.1f}/5", f"{s_loc - s_loc_cur:+.1f}")
            with c3: st.metric(f"{names[i]}｜広さ", f"{s_size:.1f}/5", f"{s_size - s_size_cur:+.1f}")
            with c4: st.metric(f"{names[i]}｜専有スペック", f"{s_spec:.1f}/5", f"{s_spec - s_spec_cur:+.1f}")
            with c5: st.metric(f"{names[i]}｜管理その他", f"{s_mgmt:.1f}/5", f"{s_mgmt - s_mgmt_cur:+.1f}")
            with c6: st.metric(f"{names[i]}｜総合偏差値", f"{hensachi:.1f}", f"{(hensachi-50):+.1f}")