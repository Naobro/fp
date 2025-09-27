# pages/compare.py
# -*- coding: utf-8 -*-

import streamlit as st
import json, os, datetime, hashlib, sqlite3
from typing import Dict, Any, List, Tuple
from contextlib import contextmanager

# ---------------- グローバル設定 ----------------
st.set_page_config(page_title="物件比較｜希望適合度×偏差値（顧客別自動保存）", layout="wide")

# 既存ファイル互換（ローカル fallback の維持）
DATA_DIR    = "data"
CLIENTS_DIR = os.path.join(DATA_DIR, "clients")
MASTER_JSON = os.path.join(DATA_DIR, "master_options.json")
DRAFT_JSON  = os.path.join(DATA_DIR, "properties_draft.json")   # 顧客ID未設定時のみ使用
PREF_JSON   = os.path.join(DATA_DIR, "client_prefs.json")       # ②側の従来ファイル（共通）。顧客別があれば優先。

os.makedirs(DATA_DIR, exist_ok=True)

# ---------------- SQLite 設定（admin/2_client_portal と整合） ----------------
DB_PATH = "clients.db"

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def _table_exists(conn, name: str) -> bool:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (name,))
    return cur.fetchone() is not None

def init_db():
    """手動用：IF NOT EXISTS で compare_states を作るだけ。起動時は呼ばない。"""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS compare_states (
                client_id TEXT PRIMARY KEY,
                updated_at TEXT NOT NULL,
                state TEXT NOT NULL
            )
        """)
        conn.commit()

def _ensure_schema_if_writable(conn):
    """書き込みのときだけテーブルを用意。読み込みでは作らない。"""
    if not _table_exists(conn, "compare_states"):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS compare_states (
                client_id TEXT PRIMARY KEY,
                updated_at TEXT NOT NULL,
                state TEXT NOT NULL
            )
        """)
        conn.commit()

# ---------------- 初期マスター（無ければ生成：ファイル互換） ----------------
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
if not os.path.exists(MASTER_JSON):
    with open(MASTER_JSON, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_MASTER, f, ensure_ascii=False, indent=2)

def load_master() -> Dict[str, Any]:
    with open(MASTER_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

M = load_master()
BALC_J = [j for j,_ in M["balcony_facings"]]

# ---------------- 顧客IDユーティリティ ----------------
def _get_client_id_from_query() -> str | None:
    try:
        v = st.query_params.get("client", None)
        if isinstance(v, list):
            v = v[0] if v else None
        return (str(v).strip() or None) if v is not None else None
    except Exception:
        qp = st.experimental_get_query_params()
        v = qp.get("client", [None])
        v = v[0] if isinstance(v, list) else v
        return (str(v).strip() or None) if v else None

def _set_client_query(cid: str):
    try:
        st.query_params["client"] = cid
    except Exception:
        qp = st.experimental_get_query_params()
        qp["client"] = cid
        st.experimental_set_query_params(**qp)

def _client_dir(cid: str) -> str:
    return os.path.join(CLIENTS_DIR, cid)

def _ensure_client_dir(cid: str):
    os.makedirs(_client_dir(cid), exist_ok=True)

def _compare_json_path(cid: str) -> str:
    return os.path.join(_client_dir(cid), "compare.json")

def _client_pref_path(cid: str) -> str:
    return os.path.join(_client_dir(cid), "client_prefs.json")

# ---------------- ハッシュ（変更検知） ----------------
def _hash_dict(d: Dict[str, Any]) -> str:
    try:
        s = json.dumps(d, ensure_ascii=False, sort_keys=True)
    except Exception:
        s = json.dumps(d.get("props", {}), ensure_ascii=False, sort_keys=True)
    return hashlib.md5(s.encode("utf-8")).hexdigest()

# ---------------- 希望条件の読込（②の成果物） ----------------
def load_prefs(client_id: str | None) -> Dict[str, Any]:
    if client_id:
        pth = _client_pref_path(client_id)
        if os.path.exists(pth):
            try:
                return json.load(open(pth, "r", encoding="utf-8"))
            except Exception:
                pass
    if os.path.exists(PREF_JSON):
        try:
            return json.load(open(PREF_JSON, "r", encoding="utf-8"))
        except Exception:
            pass
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

# ---------------- DB I/O（SQLite優先、ローカルJSONにフォールバック） ----------------
def load_compare_state(client_id: str) -> Dict[str, Any]:
    # 1) SQLite：テーブルが無ければ読み込みは何もしない
    with get_db() as conn:
        if _table_exists(conn, "compare_states"):
            row = conn.execute("SELECT state FROM compare_states WHERE client_id = ?", (client_id,)).fetchone()
            if row and row["state"]:
                try:
                    return json.loads(row["state"])
                except Exception:
                    pass
    # 2) ファイル
    pth = _compare_json_path(client_id)
    if os.path.exists(pth):
        try:
            with open(pth, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_compare_state(client_id: str, state: Dict[str, Any]):
    # 1) SQLite：書き込み時のみスキーマを保証
    try:
        with get_db() as conn:
            _ensure_schema_if_writable(conn)
            conn.execute("""
                INSERT OR REPLACE INTO compare_states (client_id, updated_at, state)
                VALUES (?, ?, ?)
            """, (client_id, datetime.datetime.now().isoformat(), json.dumps(state, ensure_ascii=False)))
            conn.commit()
            return
    except Exception as e:
        st.warning(f"DB保存失敗（ローカルへフォールバック）：{e}")

    # 2) ファイル
    _ensure_client_dir(client_id)
    with open(_compare_json_path(client_id), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def delete_compare_state(client_id: str) -> bool:
    """手動削除用。明示操作以外で消さない方針。"""
    ok_db = False
    try:
        with get_db() as conn:
            if _table_exists(conn, "compare_states"):
                cur = conn.execute("DELETE FROM compare_states WHERE client_id = ?", (client_id,))
                conn.commit()
                ok_db = cur.rowcount > 0
    except Exception:
        ok_db = False
    # JSON も消しておく（残っていても良いならコメントアウト可）
    ok_file = False
    pth = _compare_json_path(client_id)
    if os.path.exists(pth):
        try:
            os.remove(pth); ok_file = True
        except Exception:
            ok_file = False
    return ok_db or ok_file

# ---------------- 採点ユーティリティ ----------------
def auto_tsubo_price(price_man: float, area_m2: float) -> float:
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
    imp = int(imp or 5)
    return float(6 - min(max(imp,1),5))

def feature_label_score(present: bool, label: str) -> float:
    if label == "◎":   return 1.0 if present else 0.0
    if label == "○":   return 1.0 if present else 0.0
    if label == "△":   return 0.6
    if label == "×":   return 0.7 if not present else 0.4
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
        base *= 0.6
    return base, scores

def score_price_block(price_man: float, tsubo_price: float, prefs: Dict[str,Any]) -> float:
    b = prefs.get("budget_man")
    if not b: return 0.5
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

# ——（戸建て）——
def _grade_to_score(v: str) -> float:
    if isinstance(v, bool): return 1.0 if v else 0.0
    if v in ["高い","良い","十分","適切","合致","良好","可"]: return 1.0
    if v in ["普通","不明"]: return 0.6
    if v in ["低い","不足","不適切","不一致","不良","不可"]: return 0.3
    return 0.6

def score_house_spec(p: Dict[str,Any]) -> float:
    exterior_wall = p.get("exterior_wall", p.get("envelope", "普通"))
    roof_state    = p.get("roof_state",    p.get("envelope", "普通"))
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
    road_raw = str(p.get("road", "不明"))
    if road_raw == "良好": road_label = "良い"
    elif road_raw == "不良": road_label = "低い"
    elif road_raw in ["普通", "不明"]: road_label = road_raw
    else: road_label = "不明"
    parts = [
        _grade_to_score(road_label),
        _grade_to_score(p.get("garbage_spot", "普通")),
        _grade_to_score(p.get("utility_pole", "普通")),
        _grade_to_score(p.get("car_parking_ease", "普通")),
        _grade_to_score(p.get("site_retaining", "普通")),
    ]
    return sum(parts) / len(parts)

# ========== 内見チェックリスト用スコア関数 ==========
def score_inspection_block(checks: Dict[str, Any]) -> float:
    if not checks:
        return 0.5
    score_map = {"良好": 1.0, "普通": 0.6, "要補修": 0.3, "不明": 0.5}
    vals = []
    for sec, items in checks.items():
        for feat, state in items.items():
            vals.append(score_map.get(state, 0.5))
    return sum(vals) / len(vals) if vals else 0.5

def to_weights(importance: Dict[str,int]) -> Dict[str,float]:
    raw = {
        "price":       imp_to_weight(importance.get("price",3)),
        "location":    imp_to_weight(importance.get("location",3)),
        "size_layout": imp_to_weight(importance.get("size_layout",3)),
        "spec":        imp_to_weight(importance.get("spec",3)),
        "management":  imp_to_weight(importance.get("management",3)),
        # inspection を追加
        "inspection":  imp_to_weight(importance.get("inspection",3)),
    }
    s = sum(raw.values()) or 1.0
    return {k: v/s for k,v in raw.items()}

def to_fit_score(blocks: Dict[str,float], weights: Dict[str,float]) -> float:
    return sum(blocks[k]*weights.get(k,0) for k in blocks)

def to_hensachi_abs(fit: float) -> float:
    return 50.0 + 50.0*max(0.0, min(1.0, fit))

def to_hensachi_rel(fit_cand: float, fit_current: float) -> float:
    return 50.0 + 50.0*(fit_cand - fit_current)

# ---------------- 画面開始：顧客IDの確定 ----------------
st.title("🏠 物件比較｜希望適合度 × 偏差値（現住=50基準）")
st.caption("・顧客IDをURLに固定すると、そのお客様専用の下書きが自動保存／自動復元されます。")

# 顧客ID UI（最上段）
top_a, top_b, top_c, top_d = st.columns([2,2,2,2])
with top_a:
    client_id_query = _get_client_id_from_query()
    client_id_input = st.text_input("顧客ID（URLに固定推奨）", value=client_id_query or "", placeholder="例: c-abc123")

with top_b:
    if st.button("このIDでURL固定（?client=... を付与）", use_container_width=True):
        cid = (client_id_input or "").strip()
        if cid:
            _set_client_query(cid)
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

# compare_state から current_home を読込
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
    "shop": "普通", "edu": "普通", "med": "普通",
    "sec": "普通", "dis": "普通", "park": "普通", "noise": "普通",
}

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
        save_compare_state(client_id_q, _state_all)
        st.session_state["__curhome_hash__"] = _payload_now
        st.session_state["__last_saved__"] = datetime.datetime.now().strftime("%H:%M:%S")
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

# ====== ② 基本の希望条件（採点ルール） ======
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

for p in st.session_state.props:
    if "type" not in p:
        p["type"] = "マンション"

props: List[Dict[str,Any]] = st.session_state.props

def _default_prop(i: int) -> Dict[str, Any]:
    return {"name": f"物件{i+1}","type":"マンション","price_man":0.0,"year_built":0,"area_m2":0.0,"kanri":0,"shuzen":0}

if not isinstance(props, list): props = []
if len(props) < 5: props += [_default_prop(i) for i in range(len(props), 5)]
elif len(props) > 5: props = props[:5]

for i, p in enumerate(props):
    p.setdefault("name", f"物件{i+1}")
    p.setdefault("type", "マンション")
    p.setdefault("price_man", 0.0)
    p.setdefault("year_built", 0)
    p.setdefault("area_m2", 0.0)
    p.setdefault("kanri", 0)
    p.setdefault("shuzen", 0)

st.session_state.props = props

st.header("③ 5物件の基本情報（顧客別の下書き保存対応）")
with st.container(border=True):

    def _to_int(s):
        try: return int(str(s).replace(",", "").strip())
        except Exception: return 0

    def _to_float(s):
        try: return float(str(s).replace(",", "").strip())
        except Exception: return 0.0

    def _blank(v):
        if v in (None, "", 0, 0.0): return ""
        if isinstance(v, float) and v.is_integer(): return str(int(v))
        return str(v)

    cols = st.columns([1.1,1,1,1,1,1,1,1])
    for i, h in enumerate(["名称","種別","価格（万円）","築：西暦","築表示","面積（㎡）","管理費（円/月）","修繕積立（円/月）"]):
        cols[i].markdown(f"**{h}**")

    for idx in range(5):
        c0,cT,c1,c2,c3,c4,c5,c6 = st.columns([1.1,0.9,1,1,1,1,1,1], gap="small")

        name_in = c0.text_input("名称", value=props[idx].get("name", f"物件{idx+1}"), key=f"name{idx}")

        props[idx]["type"] = cT.selectbox("種別", ["マンション","戸建て"], index=0 if props[idx].get("type","マンション")=="マンション" else 1, key=f"type_list_{idx}")
        is_mansion = (props[idx]["type"] == "マンション")

        price_in = c1.text_input("価格（万円）", value=_blank(props[idx].get("price_man","")), key=f"p{idx}")

        if is_mansion:
            ybuilt_in = c2.text_input("築：西暦", value=_blank(props[idx].get("year_built","")), key=f"y{idx}")
            ybuilt_int = _to_int(ybuilt_in)
            c3.write(build_age_text(ybuilt_int) if ybuilt_int else "—")
            area_in   = c4.text_input("面積（㎡）", value=_blank(props[idx].get("area_m2","")), key=f"a{idx}")
            kanri_in  = c5.text_input("管理費（円/月）", value=_blank(props[idx].get("kanri","")), key=f"k{idx}")
            shuzen_in = c6.text_input("修繕積立（円/月）", value=_blank(props[idx].get("shuzen","")), key=f"s{idx}")

            props[idx]["year_built"] = ybuilt_int
            props[idx]["new_build"]  = False
            props[idx]["area_m2"]    = _to_float(area_in)
            props[idx]["land_m2"]    = _to_float(props[idx].get("land_m2", 0))
            props[idx]["kanri"]      = _to_int(kanri_in)
            props[idx]["shuzen"]     = _to_int(shuzen_in)

        else:
            new_build = c2.checkbox("新築", value=bool(props[idx].get("new_build", False)), key=f"new{idx}")
            ybuilt_in = c3.text_input("築：西暦（任意）", value=_blank(props[idx].get("year_built","")), key=f"yh{idx}", disabled=new_build)
            floors_in = c4.text_input("階数（数値）", value=_blank(props[idx].get("floors","")), key=f"floors{idx}")
            b_area_in = c5.text_input("建物面積（㎡）", value=_blank(props[idx].get("area_m2","")), key=f"ba{idx}")
            l_area_in = c6.text_input("土地面積（㎡）", value=_blank(props[idx].get("land_m2","")), key=f"la{idx}")

            props[idx]["new_build"]  = bool(new_build)
            props[idx]["year_built"] = (0 if new_build else _to_int(ybuilt_in))
            props[idx]["floors"]     = _to_int(floors_in)
            props[idx]["area_m2"]    = _to_float(b_area_in)
            props[idx]["land_m2"]    = _to_float(l_area_in)
            props[idx]["kanri"]      = 0
            props[idx]["shuzen"]     = 0

        props[idx]["name"]      = name_in or f"物件{idx+1}"
        props[idx]["price_man"] = _to_int(price_in)

    b1,b2,b3,b4 = st.columns(4)
    with b1:
        if st.button("💾 下書き保存（このページ）", use_container_width=True):
            cid = _get_client_id_from_query()
            if cid:
                save_compare_state(cid, {"props": props})
                st.session_state["__last_saved__"] = datetime.datetime.now().strftime("%H:%M:%S")
                st.success(f"顧客 `{cid}` として保存しました。")
            else:
                json.dump({"props": props}, open(DRAFT_JSON,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
                st.session_state["__last_saved__"] = datetime.datetime.now().strftime("%H:%M:%S")
                st.warning("顧客IDが未設定のため共有下書きに保存しました（他のお客様と混在の可能性）。")

    with b2:
        if st.button("♻ 読み込み（このページ）", use_container_width=True):
            cid = _get_client_id_from_query()
            if cid:
                loaded = load_compare_state(cid)
                st.session_state.props = loaded.get("props", props)
                for p in st.session_state.props:
                    if "type" not in p: p["type"] = "マンション"
                st.success(f"顧客 `{cid}` の下書きを読み込みました。")
            else:
                if os.path.exists(DRAFT_JSON):
                    st.session_state.props = json.load(open(DRAFT_JSON,"r",encoding="utf-8")).get("props", props)
                    for p in st.session_state.props:
                        if "type" not in p: p["type"] = "マンション"
                    st.warning("顧客ID未設定：共有下書きを読み込みました。")
                else:
                    st.info("共有下書きは存在しません。")
            st.rerun()

    with b3:
        if st.button("🗑 クリア（このページ）", use_container_width=True):
            st.session_state.props = [{"name": f"物件{i+1}","type":"マンション","price_man":0.0,"year_built":0,"area_m2":0.0,"kanri":0,"shuzen":0} for i in range(5)]
            st.success("このページの入力をクリアしました。必要なら保存してください。")
            st.rerun()

    with b4:
        st.caption("※ 顧客ID固定＋自動保存ONで安全。手動保存は保険。")

# ④ 各物件の詳細入力（タブ切替）
st.header("④ 各物件の詳細入力（タブ切替）")
tabs = st.tabs([p["name"] for p in props])

def _safe_int(x, default=0):
    try: return int(x)
    except Exception: return default

def _safe_float(x, default=0.0):
    try: return float(x)
    except Exception: return default

for i, tab in enumerate(tabs):
    with tab:
        p = props[i]
        st.subheader(f"{p['name']}：詳細")

        p["type"] = st.radio(f"物件{i+1}の種別", ["マンション", "戸建て"], index=0 if p.get("type","マンション")=="マンション" else 1, key=f"type{i}", horizontal=True)

        if p["type"] == "マンション":
            with st.container(border=True):
                cA,cB,cC,cD = st.columns(4)
                with cA:
                    price_man = st.number_input("売出価格（万円）", min_value=0, step=1, format="%d", value=int(p.get("price_man", 0)), key=f"m_dp{i}")
                    area_m2 = st.number_input("専有面積（㎡）", min_value=0.0, step=0.01, format="%.2f", value=float(p.get("area_m2", 0.0)), key=f"m_da{i}")
                    st.markdown(f"**坪単価（万/坪・自動）**：{auto_tsubo_price(float(price_man), float(area_m2)):.1f}")
                with cB:
                    year_built = st.number_input("築年（西暦）", min_value=0, step=1, format="%d", value=int(p.get("year_built", 0)), key=f"m_dy{i}")
                    st.caption(build_age_text(year_built) if year_built else "—")
                    floor = st.number_input("所在階", min_value=0, step=1, format="%d", value=int(p.get("floor", 0)), key=f"m_fl{i}")
                with cC:
                    kanri = st.number_input("管理費（円/月）", min_value=0, step=100, format="%d", value=int(p.get("kanri", 0)), key=f"m_dk{i}")
                    shuzen = st.number_input("修繕積立金（円/月）", min_value=0, step=100, format="%d", value=int(p.get("shuzen", 0)), key=f"m_ds{i}")
                with cD:
                    facing_j = st.selectbox("バルコニー向き", BALC_J, index=(BALC_J.index(p.get("facing_j", "南")) if p.get("facing_j") in BALC_J else 4), key=f"m_fj{i}")
                    balc_d = st.number_input("バルコニー奥行（m）", min_value=0.0, step=0.1, format="%.2f", value=float(p.get("balcony_depth", 1.5)), key=f"m_bd{i}")
                p.update(dict(price_man=int(price_man), area_m2=float(area_m2), year_built=int(year_built), floor=int(floor),
                              kanri=int(kanri), shuzen=int(shuzen), facing_j=facing_j, balcony_depth=float(balc_d),
                              new_build=False, land_m2=_safe_float(p.get("land_m2", 0.0))))
                p["tsubo_price"] = auto_tsubo_price(float(price_man), float(area_m2))

            st.subheader("スペック（専有部分）")
            with st.container(border=True):
                for cat, items in M["spec_categories"].items():
                    with st.expander(cat):
                        cols = st.columns(3)
                        for jdx, feat in enumerate(items):
                            col = cols[jdx % 3]
                            k = f"spec_{i}_{cat}_{jdx}"
                            val = col.checkbox(feat, value=bool(p.get("spec",{}).get(cat,{}).get(feat, False)), key=k)
                            p.setdefault("spec", {}).setdefault(cat, {})[feat] = val

            st.subheader("管理・共用部・その他")
            with st.container(border=True):
                cpk, cpt, cpt2 = st.columns([1,1,1])
                with cpk:
                    p["parking_type"] = st.selectbox("駐車場形態", M["parking_types"],
                        index=(M["parking_types"].index(p.get("parking_type","機械式")) if p.get("parking_type") in M["parking_types"] else 1), key=f"m_pt{i}")
                with cpt:
                    p["elev_num"] = st.number_input("エレベーター台数（基数）", min_value=0, value=int(p.get("elev_num",1)), step=1, key=f"m_el{i}")
                with cpt2:
                    p["pet_ok"] = st.selectbox("ペット飼育可否", ["可","不可","不明"], index={"可":0,"不可":1,"不明":2}.get(p.get("pet_ok","不明"),2), key=f"m_pet{i}")
                cols = st.columns(3)
                for m_idx, feat in enumerate(M["mgmt_shared_etc"]):
                    col = cols[m_idx % 3]
                    k = f"mg_{i}_{m_idx}"
                    val = col.checkbox(feat, value=bool(p.get("mgmt",{}).get(feat, False)), key=k)
                    p.setdefault("mgmt", {})[feat] = val

        else:
            st.subheader("基本情報")
            with st.container(border=True):
                cA, cB, cC = st.columns(3)
                with cA:
                    price_man = st.number_input("売出価格（万円）", min_value=0, step=1, format="%d", value=int(p.get("price_man", 0)), key=f"h_price{i}")
                    land_area_m2 = st.number_input("土地面積（㎡）", min_value=0.0, step=0.01, format="%.2f", value=float(p.get("land_area_m2", p.get("land_m2", 0.0))), key=f"h_lot{i}")
                    floor_area_m2 = st.number_input("建物面積（㎡）", min_value=0.0, step=0.01, format="%.2f", value=float(p.get("floor_area_m2", p.get("area_m2", 0.0))), key=f"h_bld{i}")
                    tsubo_house = auto_tsubo_price(float(price_man), float(floor_area_m2))
                    st.caption(f"坪単価（万/坪・自動｜建物面積ベース）：{tsubo_house:.1f}")
                with cB:
                    yn = st.radio("築年の扱い", ["新築", "既存（西暦入力）"], index=(0 if bool(p.get("new_build", False)) else 1), horizontal=True, key=f"h_newold{i}")
                    if yn == "新築":
                        new_build = True; yb = 0; st.caption("表示：新築")
                    else:
                        new_build = False
                        yb = st.number_input("築年（西暦）", min_value=0, step=1, format="%d", value=int(p.get("year_built") or 0), key=f"h_y{i}")
                        st.caption(build_age_text(int(yb)) if yb else "—")
                    stories = st.number_input("何階建", min_value=0, step=1, format="%d", value=int(p.get("stories", p.get("floors_total", p.get("floor", 0)))), key=f"h_sto{i}")
                with cC:
                    p["nearest_station"] = st.text_input("最寄駅（任意）", value=p.get("nearest_station", ""), key=f"h_ns{i}")

            p.update(dict(price_man=int(price_man), land_area_m2=float(land_area_m2), floor_area_m2=float(floor_area_m2),
                          year_built=int(yb), new_build=bool(new_build), stories=int(stories)))
            p["area_m2"] = float(p["floor_area_m2"])
            p["land_m2"] = float(p["land_area_m2"])
            p["tsubo_price"] = tsubo_house
            p["kanri"] = 0; p["shuzen"] = 0

            st.subheader("建物（構造・性能）")
            with st.container(border=True):
                c1,c2,c3 = st.columns(3)
                with c1:
                    p["structure"] = st.selectbox("構造", ["木造","鉄骨造","RC","SRC","その他"], index={"木造":0,"鉄骨造":1,"RC":2,"SRC":3,"その他":4}.get(p.get("structure","木造"),0), key=f"h_struct{i}")
                    p["energy_grade"] = st.selectbox("省エネ性能", ["なし","省エネ","ZEH","長期優良"], index={"なし":0,"省エネ":1,"ZEH":2,"長期優良":3}.get(p.get("energy_grade","なし"),0), key=f"h_energy{i}")
                with c2:
                    p["quake"] = st.selectbox("耐震性", ["高い","普通","低い","不明"], index={"高い":0,"普通":1,"低い":2,"不明":3}.get(p.get("quake","不明"),3), key=f"h_quake{i}")
                    p["insulation"] = st.selectbox("断熱・気密", ["高い","普通","低い","不明"], index={"高い":0,"普通":1,"低い":2,"不明":3}.get(p.get("insulation","不明"),3), key=f"h_insul{i}")
                with c3:
                    p["deterioration"] = st.selectbox("劣化対策", ["高い","普通","低い","不明"], index={"高い":0,"普通":1,"低い":2,"不明":3}.get(p.get("deterioration","不明"),3), key=f"h_det{i}")
                    p["envelope"] = st.selectbox("屋根・外壁の状態", ["良い","普通","悪い","不明"], index={"良い":0,"普通":1,"悪い":2,"不明":3}.get(p.get("envelope","不明"),3), key=f"h_env{i}")
                p["defectfree"] = st.selectbox("瑕疵（白蟻・雨漏り等）", ["良好","普通","不良","不明"], index={"良好":0,"普通":1,"不良":2,"不明":3}.get(p.get("defectfree","不明"),3), key=f"h_def{i}")

            st.subheader("敷地・法規・外構")
            with st.container(border=True):
                c1,c2,c3 = st.columns(3)
                with c1:
                    p["road_dir"] = st.multiselect("接道（方位）", ["北","東","南","西"], default=p.get("road_dir", p.get("road_dirs", [])), key=f"h_dirs{i}")
                    p["road_width_class"] = st.selectbox("接道（幅員）", ["4m未満","4m","6m以上","不明"],
                        index={"4m未満":0,"4m":1,"6m以上":2,"不明":3}.get(p.get("road_width_class", p.get("road_width","不明")),3), key=f"h_rw{i}")
                    p["road_type"] = st.selectbox("前面道路", ["公道","私道","不明"], index={"公道":0,"私道":1,"不明":2}.get(p.get("road_type","不明"),2), key=f"h_rt{i}")
                with c2:
                    p["setback_required"] = st.selectbox("セットバック", ["不要","要","不明"], index={"不要":0,"要":1,"不明":2}.get(p.get("setback_required","不明"),2), key=f"h_sb{i}")
                    p["land_shape"] = st.selectbox("土地型", ["整形地","敷地延長","変形地","不明"], index={"整形地":0,"敷地延長":1,"変形地":2,"不明":3}.get(p.get("land_shape","不明"),3), key=f"h_shape{i}")
                    p["parking_spaces"] = st.number_input("駐車スペース（台数）", min_value=0, step=1, value=int(p.get("parking_spaces",1)), key=f"h_pkg{i}")
                with c3:
                    p["car_parking_ease"] = st.selectbox("車庫入れのしやすさ", ["良い","普通","難"], index={"良い":0,"普通":1,"難":2}.get(p.get("car_parking_ease","普通"),1), key=f"h_cpe{i}")
                    p["site_retaining"] = st.selectbox("高低差・擁壁・排水", ["適切","普通","不適切","不明"], index={"適切":0,"普通":1,"不適切":2,"不明":3}.get(p.get("site_retaining","不明"),3), key=f"h_ret{i}")
                    p["garbage_spot"] = st.selectbox("ゴミ置き場の清潔さ", ["良い","普通","悪い","不明"], index={"良い":0,"普通":1,"悪い":2,"不明":3}.get(p.get("garbage_spot","不明"),3), key=f"h_gar{i}")
                    p["utility_pole"] = st.selectbox("電柱の位置", ["良い","普通","悪い","不明"], index={"良い":0,"普通":1,"悪い":2,"不明":3}.get(p.get("utility_pole","不明"),3), key=f"h_up{i}")

            st.subheader("設備・配管・エネルギー")
            with st.container(border=True):
                c1,c2,c3 = st.columns(3)
                with c1:
                    p["water"] = st.selectbox("水回りの状態", ["良好","普通","不良","不明"], index={"良好":0,"普通":1,"不良":2,"不明":3}.get(p.get("water","不明"),3), key=f"h_water{i}")
                    p["pipes"] = st.selectbox("給排水配管の状態", ["良好","普通","不良","不明"], index={"良好":0,"普通":1,"不良":2,"不明":3}.get(p.get("pipes","不明"),3), key=f"h_pipes{i}")
                with c2:
                    p["power_ampere"] = st.number_input("電気容量（A）", min_value=0, step=10, value=int(p.get("power_ampere", 0)), key=f"h_amp{i}")
                    p["gas_type"] = st.selectbox("ガス種別", ["都市ガス","プロパン","なし","不明"], index={"都市ガス":0,"プロパン":1,"なし":2,"不明":3}.get(p.get("gas_type","不明"),3), key=f"h_gas{i}")
                with c3:
                    p["all_electric"] = st.checkbox("オール電化", value=bool(p.get("all_electric", False)), key=f"h_ae{i}")
                    p["pv"] = st.checkbox("太陽光", value=bool(p.get("pv", False)), key=f"h_pv{i}")
                    p["storage_battery"] = st.checkbox("蓄電池", value=bool(p.get("storage_battery", False)), key=f"h_sbatt{i}")
                p["water_heater_note"] = st.text_input("給湯器年式・種別（任意）", value=p.get("water_heater_note",""), key=f"h_wh{i}")

            st.subheader("境界関係")
            with st.container(border=True):
                c1,c2,c3 = st.columns(3)
                with c1:
                    p.setdefault("boundary", {})
                    p["boundary"]["checked"] = st.selectbox("境界確認", ["済","未","不明"], index={"済":0,"未":1,"不明":2}.get(p["boundary"].get("checked","不明"),2), key=f"h_bconf{i}")
                    p["boundary"]["encroachment"] = st.selectbox("越境の有無", ["無し","有り","不明"], index={"無し":0,"有り":1,"不明":2}.get(p["boundary"].get("encroachment","不明"),2), key=f"h_benc{i}")
                with c2:
                    p["boundary"]["dispute"] = st.selectbox("筆界トラブル", ["無し","有り","不明"], index={"無し":0,"有り":1,"不明":2}.get(p["boundary"].get("dispute","不明"),2), key=f"h_bdis{i}")
                    p["border"] = p["boundary"]["dispute"]
                    p["boundary"]["markers"] = st.selectbox("境界標の有無", ["有","無","不明"], index={"有":0,"無":1,"不明":2}.get(p["boundary"].get("markers","不明"),2), key=f"h_bmark{i}")
                with c3:
                    p["boundary"]["survey_doc"] = st.selectbox("測量図の有無", ["有","無","不明"], index={"有":0,"無":1,"不明":2}.get(p["boundary"].get("survey_doc","不明"),2), key=f"h_bsur{i}")
                    p["boundary"]["private_road_share"] = st.selectbox("私道持分", ["有","無","不明"], index={"有":0,"無":1,"不明":2}.get(p["boundary"].get("private_road_share","不明"),2), key=f"h_bprs{i}")

        st.subheader("立地（資産性）")
        with st.container(border=True):
            p["nearest_station"] = st.text_input("最寄駅（駅名・路線等）", value=p.get("nearest_station", ""), key=f"ns{i}")
            c1,c2,c3,c4 = st.columns(4)
            with c1: p["dist_station"] = st.number_input("最寄駅 徒歩（分）", min_value=0, value=int(p.get("dist_station",10)), step=1, key=f"dst{i}")
            with c2: p["access_work"] = st.number_input("職場アクセス（分）", min_value=0, value=int(p.get("access_work",30)), step=5, key=f"awk{i}")
            with c3: p["line_count"] = st.number_input("複数路線利用（本）", min_value=0, value=int(p.get("line_count",1)), step=1, key=f"lc{i}")
            with c4: p["redevelopment_bonus"] = st.checkbox("再開発予定・特定都市再生緊急整備地域（資産価値1.5倍）", value=bool(p.get("redevelopment_bonus", False)), key=f"rd{i}")
            p["shop"]    = st.selectbox("商業施設（スーパー・コンビニ・ドラッグストア）", ["充実","良い","普通","弱い"], index={"充実":0,"良い":1,"普通":2,"弱い":3}.get(p.get("shop","普通"),2), key=f"shop{i}")
            p["edu"]     = st.selectbox("教育環境（保育園・幼稚園・小中学校・学区）", ["充実","良い","普通","弱い"], index={"充実":0,"良い":1,"普通":2,"弱い":3}.get(p.get("edu","普通"),2), key=f"edu{i}")
            p["medical"] = st.selectbox("医療施設（総合病院やクリニックの近さ）", ["充実","良い","普通","弱い"], index={"充実":0,"良い":1,"普通":2,"弱い":3}.get(p.get("medical","普通"),2), key=f"med{i}")
            p["security"]= st.selectbox("治安（夜間の人通り・街灯）", ["充実","良い","普通","弱い"], index={"充実":0,"良い":1,"普通":2,"弱い":3}.get(p.get("security","普通"),2), key=f"sec{i}")
            p["disaster"]= st.selectbox("災害リスク（洪水・液状化・ハザードマップ）", ["充実","良い","普通","弱い"], index={"充実":0,"良い":1,"普通":2,"弱い":3}.get(p.get("disaster","普通"),2), key=f"dis{i}")
            p["park"]    = st.selectbox("公園・緑地など子育て環境", ["充実","良い","普通","弱い"], index={"充実":0,"良い":1,"普通":2,"弱い":3}.get(p.get("park","普通"),2), key=f"park{i}")
            p["noise"]   = st.selectbox("騒音（線路・幹線道路・繁華街）", ["充実","良い","普通","弱い"], index={"充実":0,"良い":1,"普通":2,"弱い":3}.get(p.get("noise","普通"),2), key=f"noi{i}")
                    # === 内見チェックリスト ===
        st.subheader("内見チェックリスト")
        with st.container(border=True):
            if "inspection" not in p:
                p["inspection"] = {}
            sec_cols = st.columns(3)
            sections = {
                "外装・外構": ["外壁", "屋根", "バルコニー", "擁壁・境界"],
                "内装": ["床", "壁・天井", "建具", "家事動線", "収納"],
                "水回り": ["キッチン", "浴室", "洗面", "トイレ"],
                "設備": ["給排水管", "電気・照明", "換気・空調", "太陽光・蓄電池"],
            }
            for s_idx, (sec, feats) in enumerate(sections.items()):
                with sec_cols[s_idx % 3]:
                    with st.expander(sec):
                        for feat in feats:
                            k = f"ins_{i}_{sec}_{feat}"
                            val = st.selectbox(
                                feat,
                                ["良好", "普通", "要補修", "不明"],
                                index={"良好":0,"普通":1,"要補修":2,"不明":3}.get(
                                    p["inspection"].get(sec, {}).get(feat, "不明"), 3),
                                key=k
                            )
                            p["inspection"].setdefault(sec, {})[feat] = val

# ========== 比較表 ==========
st.header("⑤ 比較サマリー")
rows = []
for p in props:
    tsubo = auto_tsubo_price(float(p.get("price_man",0)), float(p.get("area_m2",0)))
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
        # 内見チェックリスト（inspection）のスコア
    b_insp = score_inspection_block(p.get("inspection", {}))

    # 適合度スコア計算（inspection を含む）
    fit = to_fit_score(
        {
            "price": b_price,
            "location": b_loc,
            "size_layout": b_size,
            "spec": b_spec,
            "management": b_mgmt,
            "inspection": b_insp,
        },
        to_weights(prefs.get("importance", {}))
    )

    rows.append({
        "物件名": p["name"],
        "種別": p.get("type","マンション"),
        "価格(万円)": p.get("price_man",0),
        "面積(㎡)": p.get("area_m2",0),
        "築": ("新築" if p.get("new_build") else (build_age_text(int(p.get("year_built",0)) if str(p.get("year_built","")).isdigit() else 0) if p.get("year_built") else "—")),
        "駅徒歩(分)": p.get("dist_station", None),
        "通勤(分)": p.get("access_work", None),
        "坪単価(万/坪)": round(tsubo,1),
        "内見スコア": round(b_insp*100,1),  # ★追加表示
        "適合度(0-100)": round(to_hensachi_abs(fit),1),
        "偏差値(現住=50)": round(to_hensachi_rel(fit, cur_fit),1),
    })

# 表示時に物件名を広めに表示する設定
st.dataframe(rows, use_container_width=True, column_config={
    "物件名": st.column_config.TextColumn("物件名", width="large")
})
st.caption("※ 適合度=希望充足率を0–100に線形マップ。偏差値は現住=50の差分表現（現住適合度を基準化）。")
# ========== 自動保存（変更検知で即保存） ==========
client_id_final = _get_client_id_from_query()
if client_id_final and st.session_state.get("__autosave__", False):
    prev = load_compare_state(client_id_final)
    prev["props"] = props
    if "curhome" in st.session_state:
        prev["current_home"] = st.session_state["curhome"]
    cur_hash = _hash_dict(prev)
    if st.session_state.get("__last_hash__") != cur_hash:
        save_compare_state(client_id_final, prev)
        st.session_state["__last_hash__"] = cur_hash
        st.session_state["__last_saved__"] = datetime.datetime.now().strftime("%H:%M:%S")
        st.toast(f"自動保存しました（顧客: {client_id_final}）", icon="💾")
elif not client_id_final:
    st.info("顧客IDが未設定です。上部の『このIDでURL固定』で専用URLを発行すると、自動保存され入力が消えません。")

# ========== DBユーティリティ（手動のみ） ==========
with st.expander("🔧 データベース操作（手動のみ｜自動では初期化しません）", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🛠️ 手動で compare_states を作成/確認（IF NOT EXISTS）"):
            init_db()
            st.success("compare_states を作成/確認しました（既存データは保持）。")
    with col2:
        cid = _get_client_id_from_query()
        if st.button("🗑 この顧客の比較データを削除（手動）", disabled=not bool(cid)):
            if not cid:
                st.warning("顧客IDが未設定です。")
            else:
                ok = delete_compare_state(cid)
                if ok:
                    st.success(f"顧客 `{cid}` の比較データを削除しました。")
                else:
                    st.info("削除対象が見つかりませんでした（テーブル未作成 or レコード未登録）。")
