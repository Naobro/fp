# pages/compare.py
# 5W2H
# Why: 物件比較が「マスタ共有」になり、顧客別の下書きが消える問題を解消するため。
# What: URLの ?client=XXXX を顧客IDとして認識。顧客ごとに data/clients/<ID>/compare.json へ自動保存・自動復元。
# Who: 管理者が①で発行した顧客ID（またはヒアリング②のID）をそのまま使用。各お客様専用URLを共有。
# When: 本ファイルを上書き後すぐ有効。
# Where: /compare ページ。①②のページは変更不要（prefsの読み込みは顧客別ファイルがあれば自動で優先）。
# How: st.query_params から client を取得し、props 等をJSON保存。自動保存ON時は変更検知で即保存。手動保存も併設。
# How much: 追加ファイルは data/clients/<client_id>/ 以下に自動生成。既存の DRAFT_JSON は「顧客ID未設定時のみ」後方互換。

import streamlit as st
import json, os, datetime, hashlib
from typing import Dict, Any, List, Tuple

# ==== Supabase 接続設定（追記） ====
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = st.secrets.get("SUPABASE_ANON_KEY", "")
USE_DB = bool(SUPABASE_URL and SUPABASE_ANON_KEY)

# Pylance の未インポート警告を避けつつ、実行時はフォールバックするガード
try:
    from supabase import create_client, Client  # type: ignore
except Exception:  # ImportError など
    create_client = None  # type: ignore
    Client = Any          # type: ignore
    USE_DB = False

if USE_DB and create_client:
    try:
        sb: "Client" = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)  # type: ignore
    except Exception as e:
        USE_DB = False
        st.warning(f"Supabase初期化に失敗（ローカル保存にフォールバック）：{e}")

TABLE = "compare_states"

# ---------------- グローバル設定 ----------------
st.set_page_config(page_title="物件比較｜希望適合度×偏差値（顧客別自動保存）", layout="wide")

DATA_DIR    = "data"
CLIENTS_DIR = os.path.join(DATA_DIR, "clients")
MASTER_JSON = os.path.join(DATA_DIR, "master_options.json")
DRAFT_JSON  = os.path.join(DATA_DIR, "properties_draft.json")   # 後方互換（顧客ID未設定時のみ使用）
PREF_JSON   = os.path.join(DATA_DIR, "client_prefs.json")       # ②側の従来ファイル（共通）。顧客別があれば優先。

# ---------------- 初期マスター（無ければ生成） ----------------
DEFAULT_MASTER: Dict[str, Any] = {
    "balcony_facings": [
        ["北","N"], ["北東","NE"], ["東","E"], ["南東","SE"],
        ["南","S"], ["南西","SW"], ["西","W"], ["北西","NW"]
    ],
    "spec_categories": {
        "キッチン設備": [
            "システムキッチン","食器洗浄乾燥機（食洗機）","浄水器／整水器",
            "ディスポーザー","IHクッキングヒーター","ガスコンロ（3口・グリル付）",
            "オーブンレンジ（ビルトイン）","レンジフード（換気扇）",
            "キッチン収納（スライド・ソフトクローズ）"
        ],
        "バスルーム設備": ["浴室暖房乾燥機","追い焚き機能","ミストサウナ機能","浴室テレビ","浴室に窓","半身浴"],
        "洗面・トイレ設備": ["三面鏡付き洗面化粧台","シャワー水栓付き洗面台","ウォシュレット","手洗いカウンター（トイレ内）","タンクレストイレ"],
        "暖房・空調設備": ["床暖房（LD/全室/一部）","エアコン"],
        "窓・建具設備": ["複層ガラス（ペアガラス）","Low-Eガラス","二重サッシ","建具：鏡面仕上げ"],
        "収納設備": ["全居室収納","WIC（ウォークイン）","SIC（シューズイン）","パントリー（食品庫）","リネン庫"],
        "セキュリティ・通信設備": ["TVモニター付インターホン","センサーライト（玄関）","インターネット光配線方式（各戸まで光）"]
    },
    "mgmt_shared_etc": [
        "コンシェルジュサービス","宅配ボックス","ゲストルーム","ラウンジ","キッズルーム",
        "ジム","プール","ゴミ出し24時間可","免震・制震構造",
        "セキュリティ（オートロック・防犯カメラ・24h有人）",
        "外観・エントランスのデザイン","ブランドマンション","タワーマンション",
        "長期修繕計画・資金計画","修繕積立金 妥当性","管理体制","共有部修繕履歴","収益性（利回り）"
    ],
    "parking_types": ["平置き","機械式","なし/不明"]
}
os.makedirs(DATA_DIR, exist_ok=True)
if not os.path.exists(MASTER_JSON):
    with open(MASTER_JSON, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_MASTER, f, ensure_ascii=False, indent=2)
def load_master() -> Dict[str, Any]:
    with open(MASTER_JSON, "r", encoding="utf-8") as f:
        return json.load(f)       

def load_compare_state(client_id: str) -> Dict[str, Any]:
    """
    1) Supabase から state を取得
    2) 失敗/未設定時はローカル compare.json にフォールバック
    """
    # 1) DB
    if 'USE_DB' in globals() and USE_DB:
        try:
            res = sb.table(TABLE).select("state").eq("client_id", client_id).limit(1).execute()
            if res.data:
                return res.data[0]["state"]
        except Exception as e:
            st.warning(f"DB読込失敗（ローカルへフォールバック）：{e}")

    # 2) ローカル
    pth = _compare_json_path(client_id)
    if os.path.exists(pth):
        try:
            with open(pth, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

M = load_master()
BALC_J = [j for j,_ in M["balcony_facings"]]

# ---------------- 顧客IDユーティリティ ----------------
def _get_client_id_from_query() -> str | None:
    qp = st.query_params
    cid = qp.get("client", None)
    # streamlit 1.37+ では list の可能性あり
    if isinstance(cid, list):
        cid = cid[0] if cid else None
    if cid is not None:
        cid = str(cid).strip()
        if cid == "":
            cid = None
    return cid

def _client_dir(cid: str) -> str:
    return os.path.join(CLIENTS_DIR, cid)

def _ensure_client_dir(cid: str):
    os.makedirs(_client_dir(cid), exist_ok=True)

def _compare_json_path(cid: str) -> str:
    return os.path.join(_client_dir(cid), "compare.json")

def _client_pref_path(cid: str) -> str:
    # ②（client_portal.py）側で顧客別保存に対応している場合に自動で拾う
    return os.path.join(_client_dir(cid), "client_prefs.json")

# ---------------- ハッシュ（変更検知） ----------------
def _hash_dict(d: Dict[str, Any]) -> str:
    try:
        s = json.dumps(d, ensure_ascii=False, sort_keys=True)
    except Exception:
        # 直列化不能な値が混ざる場合は props のみで計算
        s = json.dumps(d.get("props", {}), ensure_ascii=False, sort_keys=True)
    return hashlib.md5(s.encode("utf-8")).hexdigest()

# ---------------- 希望条件の読込（②の成果物） ----------------
def load_prefs(client_id: str | None) -> Dict[str, Any]:
    # 顧客別があれば最優先
    if client_id:
        pth = _client_pref_path(client_id)
        if os.path.exists(pth):
            try:
                return json.load(open(pth, "r", encoding="utf-8"))
            except Exception:
                pass
    # 従来の共通 prefs
    if os.path.exists(PREF_JSON):
        try:
            return json.load(open(PREF_JSON, "r", encoding="utf-8"))
        except Exception:
            pass
    # 無ければ空テンプレ
    return {
        "budget_man": None,
        "area_opts": {
            "line1": "", "ekifrom1":"", "ekito1":"",
            "line2": "", "ekifrom2":"", "ekito2":"",
            "line3": "", "ekifrom3":"", "ekito3":"",
            "free": ""
        },
        "types": [],
        "layout_free": "",
        "age_limit_year": None,
        "dist_limit_min": None,
        "bus_ok": "不明",
        "parking_must": False,
        "must_free": "",
        "labels_spec": {},
        "labels_mgmt": {},
        "importance": {"price":1, "location":2, "size_layout":3, "spec":4, "management":5}
    }

# ---------------- ユーティリティ（採点） ----------------
def auto_tsubo_price(price_man: float, area_m2: float) -> float:
    # 坪単価（万/坪）= 価格(万円) / ㎡ × 3.30578
    if area_m2 <= 0: return 0.0
    return price_man / area_m2 * 3.30578

def build_age(year_built: int) -> int:
    if year_built<=0: return -1
    y = datetime.date.today().year
    return max(0, y - year_built)

def build_age_text(year_built: int) -> str:
    a = build_age(year_built)
    return "築年不明" if a<0 else f"築{a}年"

def norm_more(x: float, lo: float, hi: float) -> float:
    if hi<=lo: return 0.5
    x = min(max(x, lo), hi)
    return (x - lo) / (hi - lo)

def norm_less(x: float, lo: float, hi: float) -> float:
    if hi<=lo: return 0.5
    x = min(max(x, lo), hi)
    return 1.0 - (x - lo) / (hi - lo)

def imp_to_weight(imp: int) -> float:
    # 1=最優先 → 5点、5=最低 → 1点
    imp = int(imp or 5)
    return float(6 - min(max(imp,1),5))

def feature_label_score(present: bool, label: str) -> float:
    if label == "◎":   # 必須：無ければ0
        return 1.0 if present else 0.0
    if label == "○":   # 推奨：あれば1.0、無ければ0.0
        return 1.0 if present else 0.0
    if label == "△":   # どちらでも
        return 0.6
    if label == "×":   # 無い方がよい
        return 0.7 if not present else 0.4
    return 0.5

def aggregate_label_block(presence_map: Dict[str,bool], labels: Dict[str,str]) -> Tuple[float, Dict[str,float]]:
    if not labels:
        return 0.5, {}
    scores = {}
    need_count = 0
    unmet_need = 0
    for feat, lab in labels.items():
        pres = bool(presence_map.get(feat, False))
        s = feature_label_score(pres, lab)
        scores[feat] = s
        if lab == "◎":
            need_count += 1
            if pres is False:
                unmet_need += 1
    base = sum(scores.values())/max(1,len(scores))
    if need_count>0 and unmet_need>0:
        base *= 0.6  # 必須未充足あり→減衰
    return base, scores

def score_price_block(price_man: float, tsubo_price: float, prefs: Dict[str,Any]) -> float:
    b = prefs.get("budget_man")
    if not b:
        return 0.5
    return norm_less(price_man, 0, float(b)*1.4)

def score_location_block(p: Dict[str,Any], prefs: Dict[str,Any]) -> float:
    dist = p.get("dist_station", 10)
    access = p.get("access_work", 30)
    base = 0.6*norm_less(dist,0,20) + 0.4*norm_less(access,0,90)
    if p.get("redevelopment_bonus", False):
        base = min(1.0, base*1.2)
    return base

def score_size_layout_block(area_m2: float, layout_note: str, prefs: Dict[str,Any]) -> float:
    s = norm_more(area_m2, 40, 90)
    wish = prefs.get("layout_free","") or ""
    if wish and layout_note and any(w in layout_note for w in wish.split()):
        s = min(1.0, s + 0.05)
    return s

def score_spec_block(presence_map: Dict[str,bool], labels_spec: Dict[str,str]) -> float:
    val, _ = aggregate_label_block(presence_map, labels_spec)
    return val

def score_mgmt_block(presence_map: Dict[str,bool], labels_mgmt: Dict[str,str], parking_type: str, parking_must: bool) -> float:
    val, _ = aggregate_label_block(presence_map, labels_mgmt)
    if parking_must:
        ok = (parking_type in ["平置き","機械式"])
        if not ok:
            val *= 0.6
    return val

# ——（置き換え）戸建てスコア：簡易ルール —— 
# ——（置き換え）戸建てスコア：簡易ルール —— 
def _grade_to_score(v: str) -> float:
    """
    共通ラベル→スコア変換
    - 高い/良い/十分/適切/合致/良好/可 = 1.0
    - 普通/不明 = 0.6
    - 低い/不足/不適切/不一致/不良/不可 = 0.3
    - bool は True=1.0 / False=0.0
    """
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if v in ["高い","良い","十分","適切","合致","良好","可"]:
        return 1.0
    if v in ["普通","不明"]:
        return 0.6
    if v in ["低い","不足","不適切","不一致","不良","不可"]:
        return 0.3
    return 0.6


def score_house_spec(p: Dict[str,Any]) -> float:
    """
    戸建ての「建物（構造・性能）」スコア
    """
    # UIのキーに合わせてエイリアス（無ければ envelope を流用）
    exterior_wall = p.get("exterior_wall", p.get("envelope", "普通"))
    roof_state    = p.get("roof_state",    p.get("envelope", "普通"))

    base_keys = ["quake", "insulation", "deterioration"]
    base_vals = [
        _grade_to_score(p.get("quake", "普通")),
        _grade_to_score(p.get("insulation", "普通")),
        _grade_to_score(p.get("deterioration", "普通")),
        _grade_to_score(exterior_wall),
        _grade_to_score(roof_state),
    ]
    base = sum(base_vals)/len(base_vals) if base_vals else 0.5

    bonus = 0.0
    if p.get("long_term", False):     bonus += 0.05
    if p.get("zeh", False):           bonus += 0.05
    if p.get("energy_saving", False): bonus += 0.05
    return min(1.0, base + bonus)

def score_house_management_like(p: Dict[str,Any]) -> float:
    """
    戸建ての「管理・共用」相当を敷地/外構で評価
    """
    # UIの 'road' を丸めて評価（良好/普通/不良/不明）
    road_raw = str(p.get("road", "不明"))
    if road_raw == "良好":
        road_label = "良い"
    elif road_raw == "不良":
        road_label = "低い"
    elif road_raw in ["普通", "不明"]:
        road_label = road_raw
    else:
        road_label = "不明"

    parts = [
        _grade_to_score(road_label),                         # 接道状況の総合評価
        _grade_to_score(p.get("garbage_spot", "普通")),      # ゴミ捨て場
        _grade_to_score(p.get("utility_pole", "普通")),      # 電柱位置
        _grade_to_score(p.get("car_parking_ease", "普通")),  # 車の止め易さ
        _grade_to_score(p.get("site_retaining", "普通")),    # 高低差・擁壁・排水
    ]
    return sum(parts) / len(parts)
# —— ここから下は共有関数（削除してしまった場合の復旧用。既に他所にあれば重複定義は削除してください）——

def to_weights(importance: Dict[str,int]) -> Dict[str,float]:
    raw = {
        "price":       imp_to_weight(importance.get("price",3)),
        "location":    imp_to_weight(importance.get("location",3)),
        "size_layout": imp_to_weight(importance.get("size_layout",3)),
        "spec":        imp_to_weight(importance.get("spec",3)),
        "management":  imp_to_weight(importance.get("management",3)),
    }
    s = sum(raw.values()) or 1.0
    return {k: v/s for k,v in raw.items()}

def to_fit_score(blocks: Dict[str,float], weights: Dict[str,float]) -> float:
    return sum(blocks[k]*weights.get(k,0) for k in blocks)

def to_hensachi_abs(fit: float) -> float:
    return 50.0 + 50.0*max(0.0, min(1.0, fit))

def to_hensachi_rel(fit_cand: float, fit_current: float) -> float:
    return 50.0 + 50.0*(fit_cand - fit_current)

def save_compare_state(client_id: str, state: Dict[str, Any]):
    """
    1) Supabase へ UPSERT
    2) 失敗/未設定時はローカル compare.json へ保存
    """
    if 'USE_DB' in globals() and USE_DB:
        try:
            payload = {"client_id": client_id, "state": state, "updated_at": "now()"}
            sb.table(TABLE).upsert(payload, on_conflict="client_id").execute()
            return
        except Exception as e:
            st.warning(f"DB保存失敗（ローカルへフォールバック）：{e}")
    _ensure_client_dir(client_id)
    with open(_compare_json_path(client_id), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
# ---------------- 画面開始：顧客IDの確定 ----------------
st.title("🏠 物件比較｜希望適合度 × 偏差値（現住=50基準）")
st.caption("・顧客IDをURLに固定すると、そのお客様専用の下書きが自動保存／自動復元されます。")

# 顧客ID UI（最上段）
top_a, top_b, top_c, top_d = st.columns([2,2,2,2])
with top_a:
    client_id_query = _get_client_id_from_query()
    client_id_input = st.text_input("顧客ID（URLに固定推奨）", value=client_id_query or "", placeholder="例: C000123")

with top_b:
    if st.button("このIDでURL固定（?client=... を付与）", use_container_width=True):
        cid = (client_id_input or "").strip()
        if cid:
            st.query_params["client"] = cid
            st.success(f"URLを顧客ID `{cid}` で固定しました。以後このURLをお客様専用として共有してください。")
            st.rerun()

with top_c:
    autosave_default = True if client_id_query else False
    st.toggle("自動保存ON", value=st.session_state.get("__autosave__", autosave_default),
          help="変更検知で即保存（顧客ID必須）", key="__autosave__")
with top_d:
    st.markdown(
        f"**状態**：{'顧客別（ID固定）' if client_id_query else 'マスタ（共有）'}  ｜ 最終保存: {st.session_state.get('__last_saved__','—')}"
    )

# ---------------- 希望条件（②の成果物） ----------------
prefs = load_prefs(client_id_query)
weights = to_weights(prefs.get("importance", {}))



client_id_q = _get_client_id_from_query()

# ====== ① 現在の住まい（基準：偏差値50） — 顧客別 永続化 ======
st.header("① 現在の住まい（基準：偏差値50）")

# compare.json から current_home を読込
if client_id_q:
    _state_all = load_compare_state(client_id_q)
    _curhome = _state_all.get("current_home", {})
else:
    _state_all, _curhome = {}, {}

_defaults_curhome = {
    "housing_cost_m": 10.0,
    "walk_min": 20,
    "area_m2": 55.0,
    "floor": 3,
    "corner": "不明",
    "hall": "不明",
    "view": "開放",
    "facing_j": "南",
    "balcony_depth_m": 1.5,
    "commute_h": 60,
    "commute_w": 40,
    "line_count": 1,
    "parking": "機械式",
    "redevelopment": False,
    "station_free": "",
    "shop": "普通",
    "edu": "普通",
    "med": "普通",
    "sec": "普通",
    "dis": "普通",
    "park": "普通",
    "noise": "普通",
}

# セッション初期化（ID切替にも対応）
if ("curhome" not in st.session_state) or (st.session_state.get("curhome_cid") != client_id_q):
    base = {**_defaults_curhome, **_curhome}
    st.session_state["curhome"] = base
    st.session_state["curhome_cid"] = client_id_q
    st.session_state["__curhome_hash__"] = json.dumps(base, ensure_ascii=False, sort_keys=True)

cur = st.session_state["curhome"]

with st.container(border=True):
    c1,c2,c3,c4 = st.columns(4)
    with c1:
        cur["housing_cost_m"] = st.number_input("住居費（万円/月）", min_value=0.0, value=float(cur.get("housing_cost_m",10.0)), step=0.5, key="__cur_housing_cost_m")
        cur["walk_min"] = st.number_input("最寄駅 徒歩（分）", min_value=0, value=int(cur.get("walk_min",20)), step=1, key="__cur_walk_min")
        cur["area_m2"] = st.number_input("専有面積（㎡）", min_value=0.0, value=float(cur.get("area_m2",55.0)), step=0.5, key="__cur_area_m2")
        cur["floor"] = st.number_input("所在階（数値）", min_value=0, value=int(cur.get("floor",3)), step=1, key="__cur_floor")
    with c2:
        cur["corner"] = st.selectbox("角部屋", ["角","中住戸","不明"], index=["角","中住戸","不明"].index(cur.get("corner","不明")), key="__cur_corner")
        cur["hall"]   = st.selectbox("内廊下", ["有","無","不明"], index=["有","無","不明"].index(cur.get("hall","不明")), key="__cur_hall")
        cur["view"]   = st.selectbox("眺望", ["開放","普通","閉鎖的","不明"], index=["開放","普通","閉鎖的","不明"].index(cur.get("view","開放")), key="__cur_view")
        cur["facing_j"] = st.selectbox("バルコニー向き（日本語）", BALC_J, index=(BALC_J.index(cur.get("facing_j","南")) if cur.get("facing_j","南") in BALC_J else 4), key="__cur_facing_j")
    with c3:
        cur["balcony_depth_m"] = st.number_input("バルコニー奥行（m）", min_value=0.0, value=float(cur.get("balcony_depth_m",1.5)), step=0.1, key="__cur_balc_depth")
        cur["commute_h"] = st.number_input("ご主人様 通勤（分）", min_value=0, value=int(cur.get("commute_h",60)), step=5, key="__cur_comm_h")
        cur["commute_w"] = st.number_input("奥様 通勤（分）", min_value=0, value=int(cur.get("commute_w",40)), step=5, key="__cur_comm_w")
        cur["line_count"]= st.number_input("複数路線利用（本数）", min_value=0, value=int(cur.get("line_count",1)), step=1, key="__cur_linecnt")
    with c4:
        cur["parking"] = st.selectbox("駐車場形態", M["parking_types"], index=(M["parking_types"].index(cur.get("parking","機械式")) if cur.get("parking","機械式") in M["parking_types"] else 1), key="__cur_parking")
        cur["redevelopment"] = st.checkbox("再開発予定・特定都市再生緊急整備地域", value=bool(cur.get("redevelopment", False)), key="__cur_redev")
        cur["station_free"] = st.text_input("最寄駅（任意）", value=str(cur.get("station_free","")), key="__cur_station")

    # 周辺環境（保存対象）
    st.markdown("**周辺環境**")
    d1,d2,d3,d4,d5,d6,d7 = st.columns(7)
    with d1: cur["shop"]  = st.selectbox("商業施設", ["充実","良い","普通","弱い"], index=["充実","良い","普通","弱い"].index(cur.get("shop","普通")), key="__cur_shop")
    with d2: cur["edu"]   = st.selectbox("教育環境", ["充実","良い","普通","弱い"], index=["充実","良い","普通","弱い"].index(cur.get("edu","普通")), key="__cur_edu")
    with d3: cur["med"]   = st.selectbox("医療施設", ["充実","良い","普通","弱い"], index=["充実","良い","普通","弱い"].index(cur.get("med","普通")), key="__cur_med")
    with d4: cur["sec"]   = st.selectbox("治安", ["充実","良い","普通","弱い"], index=["充実","良い","普通","弱い"].index(cur.get("sec","普通")), key="__cur_sec")
    with d5: cur["dis"]   = st.selectbox("災害リスク", ["充実","良い","普通","弱い"], index=["充実","良い","普通","弱い"].index(cur.get("dis","普通")), key="__cur_dis")
    with d6: cur["park"]  = st.selectbox("公園・緑地", ["充実","良い","普通","弱い"], index=["充実","良い","普通","弱い"].index(cur.get("park","普通")), key="__cur_park")
    with d7: cur["noise"] = st.selectbox("騒音", ["充実","良い","普通","弱い"], index=["充実","良い","普通","弱い"].index(cur.get("noise","普通")), key="__cur_noise")

# —— 保存UI ——
csa1, csa2 = st.columns([1,2])
with csa1:
    if st.button("💾 現住を保存（この顧客）"):
        if client_id_q:
            _state_all["current_home"] = dict(cur)
            save_compare_state(client_id_q, _state_all)
            st.success("現住を保存しました。")
            st.session_state["__curhome_saved__"] = True
        else:
            st.warning("顧客IDが未設定です。URLに ?client= を付けてください。")

with csa2:
    st.toggle("自動保存ON（変更検知）", value=st.session_state.get("__curhome_autosave__", True), key="__curhome_autosave__")
# —— 変更検知 → 自動保存 ——
if client_id_q and st.session_state.get("__curhome_autosave__", True):
    _payload_now = json.dumps(cur, ensure_ascii=False, sort_keys=True)
    if st.session_state.get("__curhome_hash__") != _payload_now:
        _state_all["current_home"] = dict(cur)
        save_compare_state(client_id_q, _state_all)  # ← これで統一
        st.session_state["__curhome_hash__"] = _payload_now
        st.session_state["__last_saved__"] = datetime.datetime.now().strftime("%H:%M:%S")  # 任意：最終保存表示を更新
        st.toast("現住を自動保存しました。", icon="💾")
# ====== ブロック別適合度（現住は保存値から算出） ======
cur_blocks = {
    "price": 0.5,
    "location": 0.6*norm_less(int(cur.get("walk_min",20)),0,20) + 0.4*norm_less(min(int(cur.get("commute_h",60)), int(cur.get("commute_w",40))),0,90),
    "size_layout": norm_more(float(cur.get("area_m2",55.0)),40,90),
    "spec": 0.5,
    "management": 0.5,
}
cur_fit = to_fit_score(cur_blocks, weights)

# ====== 次セクション見出し（元の位置を維持） ======
st.header("② 基本の希望条件（採点ルール）")
with st.container(border=True):
    cc1,cc2,cc3 = st.columns(3)
    with cc1:
        st.markdown(f"**予算（万円）**： {prefs.get('budget_man') if prefs.get('budget_man') else '未設定'}")
        st.markdown(f"**築年数上限**： {prefs.get('age_limit_year') if prefs.get('age_limit_year') else '未設定'} 年まで")
    with cc2:
        st.markdown(f"**駅距離上限**： {prefs.get('dist_limit_min') if prefs.get('dist_limit_min') else '未設定'} 分")
        st.markdown(f"**バス便**： {prefs.get('bus_ok','不明')}")
    with cc3:
        st.markdown(f"**駐車場必須**： {'必須' if prefs.get('parking_must') else '任意'}")
        st.markdown(f"**物件種別**： {', '.join(prefs.get('types', [])) if prefs.get('types') else '未設定'}")
    st.caption("※ ラベル評価：◎=必須／○=推奨（70%充足で合格水準）／△・×＝軽微加点。重要度(1=最優先〜5)は重み化。")

# ========== 5物件の基本情報（顧客別・自動保存に対応） ==========
# props の初期化：顧客IDがあれば顧客別ファイルから復元。なければ旧DRAFTを参照。
if "props" not in st.session_state:
    client_id = _get_client_id_from_query()
    if client_id:
        loaded = load_compare_state(client_id)
        st.session_state.props = loaded.get("props", [])
        if not st.session_state.props:
            st.session_state.props = [
                {"name": f"物件{i+1}","type":"マンション","price_man":0.0,"year_built":0,"area_m2":0.0,
                 "kanri":0, "shuzen":0} for i in range(5)
            ]
    else:
        if os.path.exists(DRAFT_JSON):
            st.session_state.props = json.load(open(DRAFT_JSON, "r", encoding="utf-8")).get("props", [])
        else:
            st.session_state.props = [
                {"name": f"物件{i+1}","type":"マンション","price_man":0.0,"year_built":0,"area_m2":0.0,
                 "kanri":0, "shuzen":0} for i in range(5)
            ]

# 後方互換：保存に type が無い場合はデフォルトで付与
for p in st.session_state.props:
    if "type" not in p:
        p["type"] = "マンション"

props: List[Dict[str,Any]] = st.session_state.props

st.header("③ 5物件の基本情報（顧客別の下書き保存対応）")
with st.container(border=True):

    def _to_int(s):
        try:
            return int(str(s).replace(",", "").strip())
        except:
            return 0
    def _to_float(s):
        try:
            return float(str(s).replace(",", "").strip())
        except:
            return 0.0
    def _blank(v):
        if v in (None, "", 0, 0.0):
            return ""
        if isinstance(v, float) and v.is_integer():
            return str(int(v))
        return str(v)

    cols = st.columns([1.1,1,1,1,1,1,1,1])
    for i,h in enumerate(["名称","種別","価格（万円）","築：西暦","築表示","面積（㎡）","管理費（円/月）","修繕積立（円/月）"]):
        cols[i].markdown(f"**{h}**")

    for idx in range(5):
        c0,cT,c1,c2,c3,c4,c5,c6 = st.columns([1.1,0.9,1,1,1,1,1,1], gap="small")

        name_in   = c0.text_input("名称", value=props[idx].get("name", f"物件{idx+1}"), key=f"name{idx}")
        # 種別（一覧でも切替可）
        props[idx]["type"] = cT.selectbox("種別", ["マンション","戸建て"], index=0 if props[idx].get("type","マンション")=="マンション" else 1, key=f"type_list_{idx}")

        price_in  = c1.text_input("価格（万円）", value=_blank(props[idx].get("price_man", "")), key=f"p{idx}")
        ybuilt_in = c2.text_input("築：西暦", value=_blank(props[idx].get("year_built", "")), key=f"y{idx}")
        area_in   = c4.text_input("面積（㎡）", value=_blank(props[idx].get("area_m2", "")), key=f"a{idx}")
        kanri_in  = c5.text_input("管理費（円/月）", value=_blank(props[idx].get("kanri", "")), key=f"k{idx}")
        shuzen_in = c6.text_input("修繕積立（円/月）", value=_blank(props[idx].get("shuzen", "")), key=f"s{idx}")

        ybuilt_int = _to_int(ybuilt_in)
        c3.write(build_age_text(ybuilt_int) if ybuilt_int else "—")

        props[idx]["name"]       = name_in or f"物件{idx+1}"
        props[idx]["price_man"]  = _to_int(price_in)
        props[idx]["year_built"] = ybuilt_int
        props[idx]["area_m2"]    = _to_float(area_in)
        props[idx]["kanri"]      = _to_int(kanri_in)
        props[idx]["shuzen"]     = _to_int(shuzen_in)

    b1,b2,b3,b4 = st.columns(4)
    with b1:
        if st.button("💾 下書き保存（このページ）", use_container_width=True):
            cid = _get_client_id_from_query()
            if cid:
                save_compare_state(cid, {"props": props})
                st.session_state["__last_saved__"] = datetime.datetime.now().strftime("%H:%M:%S")
                st.success(f"顧客 `{cid}` として保存しました。")
            else:
                # 顧客ID未設定時は旧DRAFTへ（共有）※注意喚起
                json.dump({"props": props}, open(DRAFT_JSON,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
                st.session_state["__last_saved__"] = datetime.datetime.now().strftime("%H:%M:%S")
                st.warning("顧客IDが未設定のため共有下書きに保存しました（他のお客様と混在する可能性があります）。")
    with b2:
        if st.button("♻ 読み込み（このページ）", use_container_width=True):
            cid = _get_client_id_from_query()
            if cid:
                loaded = load_compare_state(cid)
                st.session_state.props = loaded.get("props", props)
                # 後方互換で type を補完
                for p in st.session_state.props:
                    if "type" not in p:
                        p["type"] = "マンション"
                st.success(f"顧客 `{cid}` の下書きを読み込みました。")
            else:
                if os.path.exists(DRAFT_JSON):
                    st.session_state.props = json.load(open(DRAFT_JSON,"r",encoding="utf-8")).get("props", props)
                    for p in st.session_state.props:
                        if "type" not in p:
                            p["type"] = "マンション"
                    st.warning("顧客ID未設定：共有下書きを読み込みました。")
                else:
                    st.info("共有下書きは存在しません。")
            st.rerun()
    with b3:
        if st.button("🗑 クリア（このページ）", use_container_width=True):
            st.session_state.props = [
                {"name": f"物件{i+1}","type":"マンション","price_man":0.0,"year_built":0,"area_m2":0.0,"kanri":0,"shuzen":0}
                for i in range(5)
            ]
            st.success("このページの入力をクリアしました。必要なら保存してください。")
            st.rerun()
    with b4:
        st.caption("※ 顧客ID固定＋自動保存ONで安全。手動保存は保険。")

# ========== 各物件の詳細（タブ） ==========
st.header("④ 各物件の詳細入力（タブ切替）")
tabs = st.tabs([p["name"] for p in props])

def labels_from_prefs(kind: str) -> Dict[str,str]:
    return prefs.get(f"labels_{kind}", {})

for i, tab in enumerate(tabs):
    with tab:
        p = props[i]
        st.subheader(f"{p['name']}：詳細")

        # 物件種別（マンション / 戸建て）— タブ内でも切替可能
        p["type"] = st.radio(
            f"物件{i+1}の種別",
            ["マンション", "戸建て"],
            index=0 if p.get("type","マンション")=="マンション" else 1,
            key=f"type{i}"
        )

        with st.container(border=True):
            cA,cB,cC,cD = st.columns(4)

            # A列：価格・面積・坪単価
            with cA:
                price_man = st.number_input(
                    "売出価格（万円）", min_value=0, step=1, format="%d",
                    value=int(p.get("price_man", 0)), key=f"dp{i}"
                )
                area_label = "専有面積（㎡）" if p.get("type","マンション")=="マンション" else "延床面積（㎡）"
                area_m2 = st.number_input(
                    area_label, min_value=0.0, step=0.01, format="%.2f",
                    value=float(p.get("area_m2", 0.0)), key=f"da{i}"
                )
                st.markdown(f"**坪単価（万/坪・自動）**：{auto_tsubo_price(float(price_man), float(area_m2)):.1f}")

            # B列：築年・所在階（戸建ては階数ではなく “階数(任意)” として保持）
            with cB:
                year_built = st.number_input(
                    "築年（西暦）", min_value=0, step=1, format="%d",
                    value=int(p.get("year_built", 0)), key=f"dy{i}"
                )
                st.caption(build_age_text(year_built) if year_built else "—")
                floor_label = "所在階" if p.get("type","マンション")=="マンション" else "階数（任意）"
                floor = st.number_input(
                    floor_label, min_value=0, step=1, format="%d",
                    value=int(p.get("floor", 0)), key=f"fl{i}"
                )

            # C列：管理費・修繕積立金（戸建ては通常0でOK）
            with cC:
                kanri = st.number_input(
                    "管理費（円/月）", min_value=0, step=100, format="%d",
                    value=int(p.get("kanri", 0)), key=f"dk{i}"
                )
                shuzen = st.number_input(
                    "修繕積立金（円/月）", min_value=0, step=100, format="%d",
                    value=int(p.get("shuzen", 0)), key=f"ds{i}"
                )

            # D列：向き・バルコニー奥行（戸建てでも任意入力可）
            with cD:
                facing_j = st.selectbox(
                    "バルコニー向き",
                    BALC_J,
                    index=(BALC_J.index(p.get("facing_j", "南"))
                           if p.get("facing_j") in BALC_J else 4),
                    key=f"fj{i}"
                )
                balc_d = st.number_input(
                    "バルコニー奥行（m）", min_value=0.0, step=0.1, format="%.2f",
                    value=float(p.get("balcony_depth", 1.5)), key=f"bd{i}"
                )

            # 値の反映
            p.update(dict(
                price_man=int(price_man),
                area_m2=float(area_m2),
                year_built=int(year_built),
                kanri=int(kanri),
                shuzen=int(shuzen),
                facing_j=facing_j,
                balcony_depth=float(balc_d),
                floor=int(floor),
            ))
            p["tsubo_price"] = auto_tsubo_price(float(price_man), float(area_m2))

        # —— 立地は共通 ——
        st.subheader("立地（資産性）")
        with st.container(border=True):
            p["nearest_station"] = st.text_input(
                "最寄駅（駅名・路線等）",
                value=p.get("nearest_station", ""),
                key=f"ns{i}"
            )
            c1,c2,c3,c4 = st.columns(4)
            with c1:
                p["dist_station"] = st.number_input("最寄駅 徒歩（分）", min_value=0, value=int(p.get("dist_station",10)), step=1, key=f"dst{i}")
            with c2:
                p["access_work"] = st.number_input("職場アクセス（分）", min_value=0, value=int(p.get("access_work",30)), step=5, key=f"awk{i}")
            with c3:
                p["line_count"] = st.number_input("複数路線利用（本）", min_value=0, value=int(p.get("line_count",1)), step=1, key=f"lc{i}")
            with c4:
                p["redevelopment_bonus"] = st.checkbox("再開発予定・特定都市再生緊急整備地域（資産価値1.5倍）",
                                                       value=bool(p.get("redevelopment_bonus", False)), key=f"rd{i}")
            p["shop"]    = st.selectbox("商業施設（スーパー・コンビニ・ドラッグストア）", ["充実","良い","普通","弱い"], index={"充実":0,"良い":1,"普通":2,"弱い":3}.get(p.get("shop","普通"),2), key=f"shop{i}")
            p["edu"]     = st.selectbox("教育環境（保育園・幼稚園・小中学校・学区）", ["充実","良い","普通","弱い"], index={"充実":0,"良い":1,"普通":2,"弱い":3}.get(p.get("edu","普通"),2), key=f"edu{i}")
            p["medical"] = st.selectbox("医療施設（総合病院やクリニックの近さ）", ["充実","良い","普通","弱い"], index={"充実":0,"良い":1,"普通":2,"弱い":3}.get(p.get("medical","普通"),2), key=f"med{i}")
            p["security"]= st.selectbox("治安（夜間の人通り・街灯）", ["充実","良い","普通","弱い"], index={"充実":0,"良い":1,"普通":2,"弱い":3}.get(p.get("security","普通"),2), key=f"sec{i}")
            p["disaster"]= st.selectbox("災害リスク（洪水・液状化・ハザードマップ）", ["充実","良い","普通","弱い"], index={"充実":0,"良い":1,"普通":2,"弱い":3}.get(p.get("disaster","普通"),2), key=f"dis{i}")
            p["park"]    = st.selectbox("公園・緑地など子育て環境", ["充実","良い","普通","弱い"], index={"充実":0,"良い":1,"普通":2,"弱い":3}.get(p.get("park","普通"),2), key=f"park{i}")
            p["noise"]   = st.selectbox("騒音（線路・幹線道路・繁華街）", ["充実","良い","普通","弱い"], index={"充実":0,"良い":1,"普通":2,"弱い":3}.get(p.get("noise","普通"),2), key=f"noi{i}")

        # —— 種別別 UI（マンション / 戸建て） ——
        if p.get("type","マンション") == "マンション":
            st.subheader("スペック（専有部分）")
            with st.container(border=True):
                spec_presence: Dict[str,bool] = {}
                for cat, items in M["spec_categories"].items():
                    with st.expander(f""):
                        cols = st.columns(3)
                        for jdx, feat in enumerate(items):
                            col = cols[jdx % 3]
                            k = f"spec_{i}_{cat}_{jdx}"
                            val = col.checkbox(feat, value=bool(p.get("spec",{}).get(cat,{}).get(feat, False)), key=k)
                            p.setdefault("spec", {}).setdefault(cat, {})[feat] = val
                            spec_presence[feat] = val

            st.subheader("管理・共用部・その他")
            with st.container(border=True):
                cpk, cpt, cpt2 = st.columns([1,1,1])
                with cpk:
                    p["parking_type"] = st.selectbox("駐車場形態", M["parking_types"],
                                                     index=M["parking_types"].index(p.get("parking_type","機械式")) if p.get("parking_type") in M["parking_types"] else 1,
                                                     key=f"pt{i}")
                with cpt:
                    p["elev_num"] = st.number_input("エレベーター台数（基数）", min_value=0, value=int(p.get("elev_num",1)), step=1, key=f"el{i}")
                with cpt2:
                    p["pet_ok"] = st.selectbox("ペット飼育可否", ["可","不可","不明"],
                                               index={"可":0,"不可":1,"不明":2}.get(p.get("pet_ok","不明"),2), key=f"pet{i}")
                mg_presence: Dict[str,bool] = {}
                cols = st.columns(3)
                for m_idx, feat in enumerate(M["mgmt_shared_etc"]):
                    col = cols[m_idx % 3]
                    k = f"mg_{i}_{m_idx}"
                    val = col.checkbox(feat, value=bool(p.get("mgmt",{}).get(feat, False)), key=k)
                    p.setdefault("mgmt", {})[feat] = val
                    mg_presence[feat] = val
        else:
            # —— 戸建て UI ——（管理系は無し）
            st.subheader("建物（構造・性能）")
            with st.container(border=True):
                c1,c2,c3,c4,c5 = st.columns(5)
                with c1:
                    p["quake"] = st.selectbox("耐震性", ["高い","普通","低い","不明"], index={"高い":0,"普通":1,"低い":2,"不明":3}.get(p.get("quake","普通"),1), key=f"qk{i}")
                with c2:
                    p["insulation"] = st.selectbox("断熱・気密", ["高い","普通","低い","不明"], index={"高い":0,"普通":1,"低い":2,"不明":3}.get(p.get("insulation","普通"),1), key=f"in{i}")
                with c3:
                    p["deterioration"] = st.selectbox("劣化対策（長期優良等）", ["高い","普通","低い","不明"], index={"高い":0,"普通":1,"低い":2,"不明":3}.get(p.get("deterioration","普通"),1), key=f"dt{i}")
                with c4:
                    p["defectfree"] = st.selectbox("白蟻・雨漏り等の瑕疵", ["良好","普通","不良","不明"], index={"良好":0,"普通":1,"不良":2,"不明":3}.get(p.get("defectfree","普通"),1), key=f"df{i}")
                with c5:
                    p["envelope"] = st.selectbox("屋根・外壁の状態", ["良好","普通","不良","不明"], index={"良好":0,"普通":1,"不良":2,"不明":3}.get(p.get("envelope","普通"),1), key=f"env{i}")

            st.subheader("間取り・収納・家事動線")
            with st.container(border=True):
                c1,c2,c3 = st.columns(3)
                with c1:
                    p["flow"] = st.selectbox("家事動線", ["良い","普通","弱い","不明"], index={"良い":0,"普通":1,"弱い":2,"不明":3}.get(p.get("flow","普通"),1), key=f"flw{i}")
                with c2:
                    p["storage"] = st.selectbox("収納量（WIC/SIC/パントリー）", ["多い","普通","少ない","不明"], index={"多い":0,"普通":1,"少ない":2,"不明":3}.get(p.get("storage","普通"),1), key=f"str{i}")
                with c3:
                    p["light_wind"] = st.selectbox("日当たり・通風", ["良い","普通","悪い","不明"], index={"良い":0,"普通":1,"悪い":2,"不明":3}.get(p.get("light_wind","普通"),1), key=f"lw{i}")

            st.subheader("敷地・法規・外構")
            with st.container(border=True):
                c1,c2,c3,c4 = st.columns(4)
                with c1:
                    p["road"] = st.selectbox("接道状況（幅員等）", ["良好","普通","不良","不明"], index={"良好":0,"普通":1,"不良":2,"不明":3}.get(p.get("road","普通"),1), key=f"rdh{i}")
                with c2:
                    p["parking_spaces"] = st.number_input("駐車スペース（台数）", min_value=0, value=int(p.get("parking_spaces",1)), step=1, key=f"pkg{i}")
                with c3:
                    p["site_retaining"] = st.selectbox("高低差・擁壁・排水", ["適切","普通","不適切","不明"], index={"適切":0,"普通":1,"不適切":2,"不明":3}.get(p.get("site_retaining","普通"),1), key=f"ret{i}")
                with c4:
                    p["zoning_ok"] = st.selectbox("用途地域/建ぺい・容積の適合", ["合致","普通","不一致","不明"], index={"合致":0,"普通":1,"不一致":2,"不明":3}.get(p.get("zoning_ok","普通"),1), key=f"zn{i}")
                p["border"] = st.selectbox("越境/筆界トラブル", ["無し","不明","有り"], index={"無し":0,"不明":1,"有り":2}.get(p.get("border","不明"),1), key=f"bdc{i}")

            st.subheader("設備・配管")
            with st.container(border=True):
                c1,c2,c3,c4 = st.columns(4)
                with c1:
                    p["water"] = st.selectbox("水回り（キッチン/浴室/洗面/トイレ）", ["良好","普通","不良","不明"], index={"良好":0,"普通":1,"不良":2,"不明":3}.get(p.get("water","普通"),1), key=f"wt{i}")
                with c2:
                    p["pipes"] = st.selectbox("給排水配管の状態", ["良好","普通","不良","不明"], index={"良好":0,"普通":1,"不良":2,"不明":3}.get(p.get("pipes","普通"),1), key=f"pp{i}")
                with c3:
                    p["power_gas"] = st.selectbox("電気容量・ガス種別", ["十分","普通","不足","不明"], index={"十分":0,"普通":1,"不足":2,"不明":3}.get(p.get("power_gas","普通"),1), key=f"pg{i}")
                with c4:
                    p["renovation"] = st.selectbox("リフォーム履歴/必要工事の明確さ", ["明確","普通","不明"], index={"明確":0,"普通":1,"不明":2}.get(p.get("renovation","普通"),1), key=f"rv{i}")

        # —— 内見チェック（採点非連動） ——
        st.subheader("内見時チェックリスト（採点非連動）")
        with st.container(border=True):
            p.setdefault("visit_check", {})
            # 種別に応じて項目分岐
            if p.get("type","マンション") == "マンション":
                check_items = {
                    "リフォーム": [
                        "バスルーム全部","バスルーム一部","キッチン全","キッチン一部",
                        "洗面台","トイレ","給湯器","エアコン",
                        "クロス","フローリング","建具","間取り変更",
                        "外壁","屋根","太陽光蓄電池"
                    ],
                    "マンション管理": [
                        "管理人　常勤","エントランス・共用廊下の清掃状態","掲示板の状況（管理組合の情報）",
                        "エレベーターの老朽化","ゴミ置き場やメールボックスの衛生状態","駐輪場・駐車場の使いやすさ"
                    ],
                }
            else:
                check_items = {
                    "リフォーム": [
                        "バスルーム全部","バスルーム一部","キッチン全","キッチン一部",
                        "洗面台","トイレ","給湯器","エアコン",
                        "クロス","フローリング","建具","間取り変更",
                        "外壁","屋根","太陽光蓄電池"
                    ],
                    "敷地・外構": [
                        "境界確認","越境の有無","擁壁クラック","排水経路・集水状況","前面道路の交通量"
                    ]
                }
            for cat, items in check_items.items():
                with st.expander(f"", expanded=False):
                    cols = st.columns(3)
                    for j, label in enumerate(items):
                        col = cols[j % 3]
                        key = f"vc_{i}_{cat}_{j}"
                        current = bool(p.get("visit_check", {}).get(cat, {}).get(label, False))
                        val = col.checkbox(label, value=current, key=key)
                        p.setdefault("visit_check", {}).setdefault(cat, {})[label] = val

        # ======== ブロック別適合度（種別で分岐） ========
        labels_spec = labels_from_prefs("spec")
        labels_mgmt = labels_from_prefs("mgmt")

        b_price = score_price_block(p.get("price_man",0.0), p.get("tsubo_price",0.0), prefs)
        b_loc   = score_location_block(p, prefs)
        b_size  = score_size_layout_block(p.get("area_m2",0.0), "", prefs)

        if p.get("type","マンション") == "マンション":
            # マンション
            spec_presence = {}
            for cat, items in M["spec_categories"].items():
                for feat in items:
                    spec_presence[feat] = bool(p.get("spec",{}).get(cat,{}).get(feat, False))
            mg_presence = {}
            for feat in M["mgmt_shared_etc"]:
                mg_presence[feat] = bool(p.get("mgmt",{}).get(feat, False))

            b_spec  = score_spec_block(spec_presence, labels_spec)
            b_mgmt  = score_mgmt_block(mg_presence, labels_mgmt, p.get("parking_type","なし/不明"), bool(prefs.get("parking_must", False)))
        else:
            # 戸建て
            b_spec = score_house_spec(p)
            b_mgmt = score_house_management_like(p)

        blocks = {"price":b_price, "location":b_loc, "size_layout":b_size, "spec":b_spec, "management":b_mgmt}
        fit_cand = to_fit_score(blocks, weights)

        abs_score = to_hensachi_abs(fit_cand)
        rel_score = to_hensachi_rel(fit_cand, cur_fit)

        st.success(f"適合度：**{abs_score:.1f} 点**（希望充足率ベース）｜偏差値（現住=50）：**{rel_score:.1f}**")
        with st.expander("採点内訳（ブロック別）"):
            st.write({k: round(v,3) for k,v in blocks.items()})
            st.caption(f"重要度重み：{weights}")

# ========== 比較表 ==========
st.header("⑤ 比較サマリー")
rows = []
for p in props:
    tsubo = auto_tsubo_price(float(p.get("price_man",0)), float(p.get("area_m2",0)))
    # スコア再計算（表用）
    if p.get("type","マンション") == "マンション":
        sp_map, mg_map = {}, {}
        for cat, items in M["spec_categories"].items():
            for jdx, feat in enumerate(items):
                sp_map[feat] = bool(p.get("spec",{}).get(cat,{}).get(feat, False))
        for feat in M["mgmt_shared_etc"]:
            mg_map[feat] = bool(p.get("mgmt",{}).get(feat, False))
        b_spec = score_spec_block(sp_map, prefs.get("labels_spec",{}))
        b_mgmt = score_mgmt_block(mg_map, prefs.get("labels_mgmt",{}), p.get("parking_type","なし/不明"), bool(prefs.get("parking_must", False)))
    else:
        b_spec = score_house_spec(p)
        b_mgmt = score_house_management_like(p)

    b_price = score_price_block(p.get("price_man",0.0), tsubo, prefs)
    b_loc   = score_location_block(p, prefs)
    b_size  = score_size_layout_block(p.get("area_m2",0.0), "", prefs)
    fit     = to_fit_score({"price":b_price,"location":b_loc,"size_layout":b_size,"spec":b_spec,"management":b_mgmt}, to_weights(prefs.get("importance", {})))

    rows.append({
        "物件名": p["name"],
        "種別": p.get("type","マンション"),
        "価格(万円)": p.get("price_man",0),
        "面積(㎡)": p.get("area_m2",0),
        "築": build_age_text(int(p.get("year_built",0))) if p.get("year_built") else "—",
        "駅徒歩(分)": p.get("dist_station", None),
        "通勤(分)": p.get("access_work", None),
        "坪単価(万/坪)": round(tsubo,1),
        "適合度(0-100)": round(to_hensachi_abs(fit),1),
        "偏差値(現住=50)": round(to_hensachi_rel(fit, cur_fit),1),
        "再開発": "有" if p.get("redevelopment_bonus") else "無",
        "宅配ボックス": ("—" if p.get("type","マンション")=="戸建て" else ("有" if p.get("mgmt",{}).get("宅配ボックス", False) else "無"))
    })
st.dataframe(rows, use_container_width=True)
st.caption("※ 適合度=希望充足率を0–100に線形マップ。偏差値は現住=50の差分表現（現住適合度を基準化）。")

# ========== 自動保存（変更検知で即保存） ==========
client_id_final = _get_client_id_from_query()
if client_id_final and st.session_state.get("__autosave__", False):
    cur_state = {"props": props}
    cur_hash = _hash_dict(cur_state)
    if st.session_state.get("__last_hash__") != cur_hash:
        save_compare_state(client_id_final, cur_state)
        st.session_state["__last_hash__"] = cur_hash
        st.session_state["__last_saved__"] = datetime.datetime.now().strftime("%H:%M:%S")
        st.toast(f"自動保存しました（顧客: {client_id_final}）", icon="💾")
elif not client_id_final:
    st.info("顧客IDが未設定です。上部の『このIDでURL固定』で専用URLを発行すると、自動保存され入力が消えません。")