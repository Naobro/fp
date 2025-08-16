# -*- coding: utf-8 -*-
import os, json, tempfile
from datetime import datetime
from pathlib import Path

import streamlit as st
from fpdf import FPDF

# --- バルコニー方位：マスター ↔ UI 変換ユーティリティ ---
from pathlib import Path as _Path
import json as _json

def _load_master_balcony_pairs():
    p = _Path("data/master_options.json")
    if not p.exists():
        # 予備（日本語表示 / 英字コード）
        return [["北","N"],["北東","NE"],["東","E"],["南東","SE"],
                ["南","S"],["南西","SW"],["西","W"],["北西","NW"]]
    try:
        m = _json.loads(p.read_text(encoding="utf-8"))
        return m.get("balcony_facings", [])
    except Exception:
        return [["北","N"],["北東","NE"],["東","E"],["南東","SE"],
                ["南","S"],["南西","SW"],["西","W"],["北西","NW"]]

def _code_to_disp(code: str) -> str:
    for disp, c in _load_master_balcony_pairs():
        if c == code:
            return disp
    return "不明"

def _disp_to_code(disp: str) -> str:
    for d, code in _load_master_balcony_pairs():
        if d == disp:
            return code
    return "S"  # 既定値（南）

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

TO_EMAIL_DEFAULT = payload.get("hearing",{}).get("pdf_recipient","")
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
        hearing["name"]      = st.text_input("お名前", value=hearing["name"], key="h_name")
        hearing["now_area"]  = st.text_input("現在の居住エリア・駅", value=hearing["now_area"], key="h_now_area")
    with c2:
        hearing["now_years"] = st.number_input("居住年数（年）", 0, 100, int(hearing["now_years"]), key="h_now_years")
        hearing["is_owner"]  = st.selectbox("持ち家・賃貸", ["賃貸", "持ち家"], index=0 if hearing["is_owner"]=="賃貸" else 1, key="h_is_owner")
    with c3:
        hearing["housing_cost"] = st.number_input("住居費（万円/月）", 0, 200, int(hearing["housing_cost"]), key="h_housing_cost")
    hearing["family"] = st.text_input("ご家族構成（人数・年齢・将来予定）", value=hearing["family"], key="h_family")

    st.divider()

    st.markdown("#### 現在の住まい（満足・不満）")
    hearing["sat_point"] = st.text_area("現在の住宅の満足点（自由入力）", value=hearing["sat_point"], key="h_sat_point")
    sc1, sc2, sc3, sc4, sc5 = st.columns(5)
    with sc1: hearing["sat_price"]    = st.slider("満足度：価格", 1, 5, int(hearing["sat_price"]), key="h_sat_price")
    with sc2: hearing["sat_location"] = st.slider("満足度：立地", 1, 5, int(hearing["sat_location"]), key="h_sat_location")
    with sc3: hearing["sat_size"]     = st.slider("満足度：広さ", 1, 5, int(hearing["sat_size"]), key="h_sat_size")
    with sc4: hearing["sat_age"]      = st.slider("満足度：築年数", 1, 5, int(hearing["sat_age"]), key="h_sat_age")
    with sc5: hearing["sat_spec"]     = st.slider("満足度：スペック", 1, 5, int(hearing["sat_spec"]), key="h_sat_spec")
    sat_total = int(hearing["sat_price"]) + int(hearing["sat_location"]) + int(hearing["sat_size"]) + int(hearing["sat_age"]) + int(hearing["sat_spec"])
    st.caption(f"満足度スコア合計：**{sat_total} / 25**")
    hearing["dissat_free"] = st.text_area("不満な点（自由入力）", value=hearing["dissat_free"], key="h_dissat_free")

    st.divider()

    st.markdown("#### 5W2H（購入計画）")
    c1, c2 = st.columns(2)
    with c1:
        hearing["w_why"]   = st.text_input("Why（なぜ）：購入理由", value=hearing["w_why"], key="h_w_why")
        hearing["w_when"]  = st.text_input("When（いつ）：購入／入居タイミング", value=hearing["w_when"], key="h_w_when")
        hearing["w_where"] = st.text_input("Where（どこで）：希望エリア・沿線", value=hearing["w_where"], key="h_w_where")
        hearing["w_who"]   = st.text_input("Who（誰が）：居住メンバー", value=hearing["w_who"], key="h_w_who")
    with c2:
        hearing["w_what"]     = st.text_input("What（何を）：種別・広さ・階数・設備", value=hearing["w_what"], key="h_w_what")
        hearing["w_how"]      = st.text_input("How（どう買う）：ローン・頭金", value=hearing["w_how"], key="h_w_how")
        hearing["w_howmuch"]  = st.text_input("How much（いくら）：総予算／月返済上限", value=hearing["w_howmuch"], key="h_w_howmuch")
        hearing["w_free"]     = st.text_area("補足（自由入力）", value=hearing["w_free"], key="h_w_free")

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        save_only = st.form_submit_button("💾 ① 入力を上書き保存")
    with col_b:
        save_and_pdf = st.form_submit_button("📄 保存してPDF作成")

# 保存ハンドラ
if 'save_only' in locals() and save_only:
    payload["hearing"] = dict(hearing)
    payload.setdefault("meta", {}).update({"name": hearing.get("name","")})
    save_client(CLIENT_ID, payload)
    st.session_state["hearing_data"] = dict(payload["hearing"])
    st.success("① ヒアリングを上書き保存しました。")
    st.experimental_rerun()

if 'save_and_pdf' in locals() and save_and_pdf:
    payload["hearing"] = dict(hearing)
    payload.setdefault("meta", {}).update({"name": hearing.get("name","")})
    save_client(CLIENT_ID, payload)
    st.session_state["hearing_data"] = dict(payload["hearing"])
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
        "balcony_aspect": "S",         # N/NE/E/SE/S/SW/W/NW
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
        opts = [d for d,_ in _load_master_balcony_pairs()]
        cur_disp = _code_to_disp(b.get("balcony_aspect","S"))
        b_disp = st.selectbox("バルコニー向き", opts, index=opts.index(cur_disp) if cur_disp in opts else 4)  # 既定は「南」
    with c4:
        b["view"] = st.selectbox("眺望", ["未設定","開放","一部遮り","正面に遮り"],
                                 index=["未設定","開放","一部遮り","正面に遮り"].index(b.get("view","未設定")))

    submitted_baseline = st.form_submit_button("💾 ② 現状把握を上書き保存")

if submitted_baseline:
    b["balcony_aspect"] = _disp_to_code(b_disp)
    payload["baseline"] = dict(b)
    save_client(CLIENT_ID, payload)
    st.success("② 現状把握を上書き保存しました。")
    st.experimental_rerun()

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
        "balcony_aspect": b.get("balcony_aspect","S"), "balcony_depth_m": 1.5,
        "sun_wind_level": "普通", "hall_flow_level": "普通",
        # 専有（設備）
        "k_dishwasher": False, "k_purifier": False, "k_disposer": False, "k_highend_cooktop": False, "k_bi_oven": False,
        "b_dryer": False, "b_reheating": False, "b_mist_sauna": False, "b_tv": False, "b_window": False,
        "h_floorheat": False, "h_aircon_built": False,
        "w_multi": False, "w_low_e": False, "w_double_sash": False, "w_premium_doors": False,
        "s_allrooms": False, "s_wic": False, "s_sic": False, "s_pantry": False, "s_linen": False,
        "sec_tvphone": False, "sec_sensor": False, "net_ftth": False,
        # 管理・共用（デフォルトは全て未チェック）
        "c_box": False, "c_parking": "なし", "c_gomi24": False,
        "c_seismic": False, "c_security": False,
        "c_design_level": "普通",
        "c_ev_count": 0, "c_pet_ok": False,
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
        cur["area_m2"] = st.number_input("専有面積（㎡）", 0.0, 300.0, float(cur["area_m2"]))
        cur["living_jyo"] = st.number_input("リビングの広さ（帖）", 0.0, 50.0, float(cur["living_jyo"]))
        cur["layout_type"] = st.selectbox(
            "間取りタイプ",
            ["田の字","ワイドスパン","センターイン","その他"],
            index=["田の字","ワイドスパン","センターイン","その他"].index(cur["layout_type"])
        )
    with c2:
        cur["storage_level"] = st.selectbox(
            "収納量（WIC・SIC含む総合）",
            ["多い","普通","少ない"],
            index=["多い","普通","少ない"].index(cur["storage_level"])
        )
        cur["ceiling_level"] = st.selectbox(
            "天井高",
            ["高い","普通","低い"],
            index=["高い","普通","低い"].index(cur["ceiling_level"])
        )
        # 方位：日本語表示→コード保存
        opts2 = [d for d,_ in _load_master_balcony_pairs()]
        cur_disp2 = _code_to_disp(cur.get("balcony_aspect","S"))
        sel_disp2 = st.selectbox(
            "バルコニー向き",
            opts2,
            index=opts2.index(cur_disp2) if cur_disp2 in opts2 else 4
        )
        cur["balcony_aspect"] = _disp_to_code(sel_disp2)
    with c3:
        cur["balcony_depth_m"] = st.number_input(
            "バルコニー奥行（m）",
            0.0, 5.0, float(cur.get("balcony_depth_m",1.5)),
            step=0.1
        )
        cur["sun_wind_level"] = st.selectbox(
            "採光・通風",
            ["良い","普通","悪い"],
            index=["良い","普通","悪い"].index(cur["sun_wind_level"])
        )
        cur["hall_flow_level"] = st.selectbox(
            "廊下幅・家事動線効率",
            ["良い","普通","悪い"],
            index=["良い","普通","悪い"].index(cur["hall_flow_level"])
        )

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
        cur["c_ev_count"] = st.number_input("エレベーター台数（基数）", 0, 20, int(cur["c_ev_count"]))
        cur["c_pet_ok"] = st.checkbox("ペット飼育可", value=cur["c_pet_ok"])

if st.button("💾 ③ 現状スコアリングを上書き保存"):
    payload["current_home"] = dict(cur)
    save_client(CLIENT_ID, payload)
    st.success("③ 現状スコアリングを上書き保存しました。")
    st.experimental_rerun()

st.divider()

# ============================================
# ③.5 基本の希望条件（マスト項目：④の前に入れる）
# ============================================
st.header("④.5 基本の希望条件（マスト項目）")

if "basic_prefs" not in payload:
    payload["basic_prefs"] = {
        "budget_man": None,
        "areas": {"line1":"", "ekifrom1":"", "ekito1":"", "line2":"", "ekifrom2":"", "ekito2":"", "line3":"", "ekifrom3":"", "ekito3":"", "free":""},
        "types": [],
        "layout_free": "",
        "age_limit_year": None,
        "dist_limit_min": None,
        "bus_ok": "不問",
        "parking_must": False,
        "must_free": "",
        "importance": {"price":1, "location":2, "size_layout":3, "spec":4, "management":5}
    }
bp = payload["basic_prefs"]

with st.form("basic_prefs_form", clear_on_submit=False):
    c1,c2,c3 = st.columns(3)
    with c1:
        bp["budget_man"] = st.number_input("予算（万円）", min_value=0, value=int(bp.get("budget_man") or 0), step=100)
        bp["age_limit_year"] = st.number_input("築年数（〜年まで）", min_value=0, value=int(bp.get("age_limit_year") or 0), step=1)
        bp["dist_limit_min"] = st.number_input("駅までの距離（〜分）", min_value=0, value=int(bp.get("dist_limit_min") or 0), step=1)
    with c2:
        bp["bus_ok"] = st.selectbox("バス便 可否", ["可","不可","不問"], index={"可":0,"不可":1,"不問":2}.get(bp.get("bus_ok","不問"),2))
        bp["parking_must"] = st.checkbox("駐車場 必須", value=bool(bp.get("parking_must", False)))
        bp["types"] = st.multiselect("物件種別（複数選択可）", ["戸建","マンション","注文住宅（土地）","投資用","節税対策","リゾート"], default=bp.get("types", []))
    with c3:
        bp["layout_free"] = st.text_input("間取り（記述）", value=bp.get("layout_free",""))
        bp["must_free"] = st.text_area("その他 MUST 条件（記述）", value=bp.get("must_free",""), height=90)

    st.markdown("**エリア希望（第1〜第3）／自由記述**")
    a1,a2,a3,a4 = st.columns(4)
    with a1:
        bp["areas"]["line1"]    = st.text_input("第1：路線", value=bp["areas"].get("line1",""))
        bp["areas"]["ekifrom1"] = st.text_input("第1：駅（起点）", value=bp["areas"].get("ekifrom1",""))
        bp["areas"]["ekito1"]   = st.text_input("第1：駅（終点）", value=bp["areas"].get("ekito1",""))
    with a2:
        bp["areas"]["line2"]    = st.text_input("第2：路線", value=bp["areas"].get("line2",""))
        bp["areas"]["ekifrom2"] = st.text_input("第2：駅（起点）", value=bp["areas"].get("ekifrom2",""))
        bp["areas"]["ekito2"]   = st.text_input("第2：駅（終点）", value=bp["areas"].get("ekito2",""))
    with a3:
        bp["areas"]["line3"]    = st.text_input("第3：路線", value=bp["areas"].get("line3",""))
        bp["areas"]["ekifrom3"] = st.text_input("第3：駅（起点）", value=bp["areas"].get("ekifrom3",""))
        bp["areas"]["ekito3"]   = st.text_input("第3：駅（終点）", value=bp["areas"].get("ekito3",""))
    with a4:
        bp["areas"]["free"]     = st.text_area("（または）エリア自由記述", value=bp["areas"].get("free",""), height=90)

    submitted_basic = st.form_submit_button("💾 ④.5 基本の希望条件を上書き保存")

if submitted_basic:
    payload["basic_prefs"] = dict(bp)
    save_client(CLIENT_ID, payload)
    # 任意エクスポート
    try:
        export = {
            "budget_man": bp.get("budget_man"),
            "age_limit_year": bp.get("age_limit_year"),
            "dist_limit_min": bp.get("dist_limit_min"),
            "bus_ok": bp.get("bus_ok"),
            "parking_must": bp.get("parking_must"),
            "types": bp.get("types", []),
            "layout_free": bp.get("layout_free",""),
            "must_free": bp.get("must_free",""),
            "areas": bp.get("areas", {}),
            "importance": bp.get("importance", {})
        }
        os.makedirs("data", exist_ok=True)
        with open("data/client_prefs.json","w",encoding="utf-8") as f:
            json.dump(export, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    st.success("④.5 基本の希望条件を上書き保存しました。")
    st.experimental_rerun()

# ========= 重要度（1=最優先〜5）重複なし UI（「1番」表記） =========
st.subheader("⑥ 重要度のトレードオフ（1=最優先〜5）")
st.caption("※ 各カテゴリに 1番,2番,3番,4番,5番 を一度ずつ割当て（重複不可）。")

CATS = [
    ("price",       "価格"),
    ("location",    "立地"),
    ("size_layout", "広さ・間取り"),
    ("spec",        "スペック（専有）"),
    ("management",  "管理・共有部・その他"),
]
LABEL_MAP = {1:"1番", 2:"2番", 3:"3番", 4:"4番", 5:"5番"}

def _normalize_importance(imp: dict) -> dict:
    # 1..5 を各カテゴリに一意に割当て（不足/重複を解消）
    imp = dict(imp or {})
    cur = {k: int(v) for k, v in imp.items() if v in [1,2,3,4,5]}
    used = []
    out = {}
    for k,_ in CATS:
        v = cur.get(k)
        if v in [1,2,3,4,5] and v not in used:
            out[k] = v; used.append(v)
    free = [n for n in [1,2,3,4,5] if n not in used]
    for k,_ in CATS:
        if k not in out:
            out[k] = free.pop(0)
    return out

# 初期化（basic_prefs → セッション）
if "imp_state" not in st.session_state:
    st.session_state.imp_state = _normalize_importance(bp.get("importance", {"price":1,"location":2,"size_layout":3,"spec":4,"management":5}))

def _available_for(cat_key: str):
    cur_all = dict(st.session_state.imp_state)
    cur_val = cur_all.get(cat_key)
    used_other = {v for k, v in cur_all.items() if k != cat_key}
    opts = [n for n in [1,2,3,4,5] if (n == cur_val) or (n not in used_other)]
    return opts, cur_val

def _on_change(cat_key: str, widget_key: str):
    new_val = st.session_state.get(widget_key, None)
    if new_val is None: return
    new_val = int(new_val)
    cur_all = dict(st.session_state.imp_state)
    old_self = cur_all.get(cat_key)
    for k in list(cur_all.keys()):
        if k != cat_key and cur_all[k] == new_val:
            occupied = set(cur_all.values()) - {old_self}
            free = [n for n in [1,2,3,4,5] if n not in occupied and n != new_val]
            st.session_state.imp_state[k] = free[0] if free else (6 - new_val)
    st.session_state.imp_state[cat_key] = new_val

def _fmt(n: int) -> str:
    return LABEL_MAP.get(n, f"{n}番")

row1 = st.columns(3); row2 = st.columns(2); rows = row1 + row2
for idx, (k, label) in enumerate(CATS):
    col = rows[idx]
    opts, curv = _available_for(k)
    key = f"imp_{k}"
    col.selectbox(label, options=opts, index=opts.index(curv) if curv in opts else 0,
                  key=key, on_change=_on_change, args=(k, key,), format_func=_fmt,
                  help="各カテゴリに 1番〜5番 を重複なく割当て")

c1, c2 = st.columns(2)
with c1:
    if st.button("↺ リセット（1番→価格, 2番→立地 ...）", use_container_width=True):
        st.session_state.imp_state = {k: i+1 for i,(k,_) in enumerate(CATS)}
        st.experimental_rerun()
with c2:
    if st.button("💾 重要度を上書き保存", type="primary", use_container_width=True):
        bp["importance"] = dict(st.session_state.imp_state)
        payload["basic_prefs"] = bp
        save_client(CLIENT_ID, payload)
        try:
            export_path = "data/client_prefs.json"
            export = json.load(open(export_path,"r",encoding="utf-8")) if os.path.exists(export_path) else {}
            export["importance"] = dict(st.session_state.imp_state)
            with open(export_path,"w",encoding="utf-8") as f:
                json.dump(export, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        st.success("重要度を保存しました（重複なし・1番〜5番）。")
        st.experimental_rerun()

st.header("⑤ 希望条件（◎=必要／○=あったほうがよい／△=どちらでもよい／×=なくてよい）")

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

if st.button("💾 ④ 希望条件を上書き保存"):
    payload["wish"] = dict(wish)
    save_client(CLIENT_ID, payload)
    st.success("④ 希望条件を上書き保存しました。")
    st.experimental_rerun()

st.divider()

st.subheader("⑤ 物件比較（別ページ）")
st.markdown("""
比較ページでは、現住居=偏差値50 を基準に
内見物件の優劣を一覧で表示します。
""")

if st.button("物件比較ページを開く"):
    try:
        st.switch_page("pages/3_compare.py")
    except Exception:
        st.page_link("pages/3_compare.py", label="↔ 物件比較ページを開く", icon="↔️")