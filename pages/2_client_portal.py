# fp/pages/2_client_portal.py
# -*- coding: utf-8 -*-
"""
【このページの方針】
- 起動時に DB を初期化しない（init_db() を自動では呼ばない）
- admin.py と同じ DB 関数・スキーマを使用（互換性100%）
- 書き込み時のみ Lazy でスキーマ作成（読み取りは作らない）
- 管理UIに「手動でDB初期化」ボタンを用意（押した時だけ CREATE TABLE IF NOT EXISTS）
"""
import os, json, tempfile, secrets, string, io
import sqlite3
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

import streamlit as st
from fpdf import FPDF

# ==== PDF用 日本語フォント（NotoSansJP） ====
from urllib import request as _urlreq
import tempfile as _tmp
from pathlib import Path as _Path

# =========================================================
# set_page_config は最初に
# =========================================================
st.set_page_config(page_title="理想の住まいへのロードマップ", layout="wide")

# =========================================================
# データベース（admin.pyと完全互換）
# =========================================================
DB_PATH = "clients.db"

@contextmanager
def get_db():
    """データベース接続（admin.pyと同形）"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """データベース初期化（admin.pyと同形：IF NOT EXISTS）"""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                client_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                name TEXT,
                phone TEXT,
                email TEXT,
                memo TEXT,
                data TEXT NOT NULL  -- JSON文字列として全データを保存
            )
        """)
        conn.commit()

# ★ここでは init_db() を呼ばない（＝起動時自動初期化しない）

# --- スキーマ存在チェック（読み取りでは作らない） ---
def _table_exists(conn, table_name: str) -> bool:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table_name,))
    return cur.fetchone() is not None

def _ensure_schema_if_writable(conn):
    """書き込み時のみテーブル作成（読み取りでは呼ばない）"""
    if not _table_exists(conn, "clients"):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                client_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                name TEXT,
                phone TEXT,
                email TEXT,
                memo TEXT,
                data TEXT NOT NULL
            )
        """)
        conn.commit()

def save_client(client_id: str, payload: dict):
    """クライアント保存（admin同名）。書き込み時のみスキーマ用意。"""
    meta = payload.get("meta", {})
    with get_db() as conn:
        _ensure_schema_if_writable(conn)
        conn.execute("""
            INSERT OR REPLACE INTO clients 
            (client_id, created_at, name, phone, email, memo, data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            client_id,
            meta.get("created_at", datetime.now().isoformat()),
            meta.get("name"),
            meta.get("phone"),
            meta.get("email"),
            meta.get("memo"),
            json.dumps(payload, ensure_ascii=False)
        ))
        conn.commit()

def load_client(client_id: str) -> dict | None:
    """特定顧客読み込み（テーブル無ければ作らない＝None）"""
    with get_db() as conn:
        if not _table_exists(conn, "clients"):
            return None
        row = conn.execute("SELECT data FROM clients WHERE client_id = ?", (client_id,)).fetchone()
        if not row:
            return None
        try:
            return json.loads(row["data"])
        except Exception:
            return None

def load_all_clients():
    """全顧客メタ一覧（テーブル無ければ空配列）"""
    with get_db() as conn:
        if not _table_exists(conn, "clients"):
            return []
        rows = conn.execute("""
            SELECT client_id, created_at, name, phone, email, memo, data
            FROM clients
            ORDER BY created_at DESC
        """).fetchall()
        items = []
        for row in rows:
            try:
                created = datetime.fromisoformat(row["created_at"]) if row["created_at"] else None
            except Exception:
                created = None
            items.append({
                "id": row["client_id"],
                "name": row["name"] or "(無名)",
                "created": created,
                "phone": row["phone"],
                "email": row["email"],
                "memo": row["memo"],
                "raw": json.loads(row["data"]) if row["data"] else {}
            })
        return items

def delete_client(client_id: str) -> bool:
    """削除（テーブル無ければ何もしない/False）"""
    try:
        with get_db() as conn:
            if not _table_exists(conn, "clients"):
                return False
            cur = conn.execute("DELETE FROM clients WHERE client_id = ?", (client_id,))
            conn.commit()
            return cur.rowcount > 0
    except Exception:
        return False

# =========================================================
# 0) 新旧クエリAPI 互換ヘルパ + client自動発行
# =========================================================
def _get_query_param(name: str, default=None):
    """st.query_params と experimental_* の両対応で取得"""
    try:
        v = st.query_params.get(name, default)
        if isinstance(v, list):
            return v[0] if v else default
        return v if v not in [None, ""] else default
    except Exception:
        qp = st.experimental_get_query_params()
        v = qp.get(name, [default])
        return v[0] if isinstance(v, list) else v

def _set_query_param(name: str, value):
    """st.query_params と experimental_* の両対応で設定"""
    try:
        st.query_params[name] = value
    except Exception:
        now = st.experimental_get_query_params()
        now[name] = value
        st.experimental_set_query_params(**now)

def _gen_client_id(n: int = 6) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "c-" + "".join(secrets.choice(alphabet) for _ in range(n))

# =========================================================
# 1) クライアントID確定 & セッション分離
# =========================================================
client_id = _get_query_param("client", None)
if not client_id:
    client_id = _gen_client_id()
    _set_query_param("client", client_id)

if st.session_state.get("_active_client") != client_id:
    st.session_state.clear()
    st.session_state["_active_client"] = client_id

def ns(key: str) -> str:
    return f"{client_id}::{key}"

# =========================================================
# PDF用フォント（NotoSansJP）
# =========================================================
_REG_NAME = "NotoSansJP-Regular.ttf"
_BLD_NAME = "NotoSansJP-Bold.ttf"
_RAW_REG = "https://raw.githubusercontent.com/Naobro/fp/main/fonts/NotoSansJP-Regular.ttf"
_RAW_BLD = "https://raw.githubusercontent.com/Naobro/fp/main/fonts/NotoSansJP-Bold.ttf"

def _ensure_jp_fonts() -> Path:
    candidates = [
        Path(__file__).resolve().parent / "fonts",
        Path.cwd() / "fonts",
        Path("/mount/src/fp/fonts"),
        Path("/app/fonts"),
    ]
    for d in candidates:
        reg = d / _REG_NAME
        bld = d / _BLD_NAME
        if reg.exists() and bld.exists():
            return d.resolve()
    for d in candidates:
        reg = d / _REG_NAME
        bld = d / _BLD_NAME
        if reg.exists():
            d.mkdir(parents=True, exist_ok=True)
            if not bld.exists():
                bld.write_bytes(reg.read_bytes())
            return d.resolve()
        if bld.exists():
            d.mkdir(parents=True, exist_ok=True)
            if not reg.exists():
                reg.write_bytes(bld.read_bytes())
            return d.resolve()
    tmpdir = Path(_tmp.mkdtemp(prefix="fonts_"))
    _urlreq.urlretrieve(_RAW_REG, str(tmpdir / _REG_NAME))
    try:
        _urlreq.urlretrieve(_RAW_BLD, str(tmpdir / _BLD_NAME))
    except Exception:
        (tmpdir / _BLD_NAME).write_bytes((tmpdir / _REG_NAME).read_bytes())
    return tmpdir.resolve()

# --- バルコニー方位ユーティリティ ---
def _load_master_balcony_pairs():
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
    return "S"

# =========================
# 互換ユーティリティ
# =========================
def export_compare_prefs_min(cid: str, mode_label: str):
    _dir = _Path("data/clients") / cid
    _dir.mkdir(parents=True, exist_ok=True)
    types = ["マンション"] if mode_label == "マンション" else ["戸建て"]
    data = {"types": types}
    (_dir / "client_prefs.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def _blank_payload(cid: str) -> dict:
    return {
        "meta": {
            "client_id": cid,
            "created_at": datetime.now().isoformat(),
            "name": ""
        }
    }

def load_or_init_client(cid: str) -> dict:
    data = load_client(cid)
    if data:
        return data
    data = _blank_payload(cid)
    save_client(cid, data)  # ← 初回書込み時のみテーブル作成が走る
    return data

# ========= サニタイズ =========
def _coerce_int(val, default):
    return int(val) if isinstance(val, (int, float)) else default

def _coerce_float(val, default):
    try:
        return float(val) if isinstance(val, (int, float, str)) and str(val).strip() != "" else default
    except Exception:
        return default

# =========================
# 本体：クライアントデータロード
# =========================
payload = load_or_init_client(client_id)

# Baseline 補正
if "baseline" in payload and isinstance(payload["baseline"], dict):
    btmp = payload["baseline"]
    payload["baseline"] = {
        "housing_cost_m": _coerce_int(btmp.get("housing_cost_m"), 10),
        "walk_min":       _coerce_int(btmp.get("walk_min"), 10),
        "area_m2":        _coerce_int(btmp.get("area_m2"), 60),
        "floor":          _coerce_int(btmp.get("floor"), 3),
        "balcony_aspect": btmp.get("balcony_aspect") or "S",
        "view":           btmp.get("view") or "未設定",
        "husband_commute_min": _coerce_int(btmp.get("husband_commute_min"), 30),
        "wife_commute_min":    _coerce_int(btmp.get("wife_commute_min"), 40),
    }
else:
    payload["baseline"] = {
        "housing_cost_m": 10,
        "walk_min": 10,
        "area_m2": 60,
        "floor": 3,
        "balcony_aspect": "S",
        "view": "未設定",
        "husband_commute_min": 30,
        "wife_commute_min": 40,
    }

# =========================================================
# Header
# =========================================================
st.title("理想の住まいへのロードマップ")
header_name = payload.get("meta",{}).get("name") or "お客様"
st.success(f"{header_name} 専用ページ（ID: {client_id}）")

# === クライアントID切替 ===
c_left, c_right = st.columns([1,1])
with c_right:
    st.caption("クライアント切替")
    _new_id = st.text_input("client_id", value=client_id, key="__client_switcher")
    if st.button("このIDで切替", key="__client_switch_btn"):
        _new_id = (_new_id or "").strip()
        if _new_id and _new_id != client_id:
            _set_query_param("client", _new_id)
            st.session_state.clear()
            st.session_state["_active_client"] = _new_id
            st.rerun()

# === 管理：初期化・削除・バックアップ ===
with st.expander("管理（このIDの初期化・削除・バックアップ）", expanded=False):
    st.caption(f"現在の client_id: **{client_id}** ｜ 保存先: `{DB_PATH}`（SQLite）")

    c0, c1, c2, c3 = st.columns(4)

    # 手動初期化（押した時だけテーブル作成、既存データ不削除）
    with c0:
        if st.button("🛠️ 手動でDB初期化", key=ns("btn_manual_initdb")):
            init_db()
            st.success("clients テーブルを作成/確認しました（既存データは保持）。")

    with c1:
        if st.button("🧹 白紙で初期化（このID）", key=ns("btn_reset_blank")):
            payload = _blank_payload(client_id)
            save_client(client_id, payload)
            st.success("このIDを白紙データで作り直しました。")
            st.rerun()

    with c2:
        if st.button("🗑️ このIDをDBから削除", key=ns("btn_delete_client")):
            ok = delete_client(client_id)
            if ok:
                st.success("このIDのレコードをDBから削除しました。新しいIDに切替えます。")
                _set_query_param("client", _gen_client_id())
                st.session_state.clear()
                st.rerun()
            else:
                st.warning("テーブル未作成 or レコード未存在のため削除対象なし。")

    with c3:
        # 軽いバックアップ：このIDのJSON
        if st.button("🧪 このIDのJSONを表示", key=ns("show_this_json")):
            st.json(payload)

# ============================================
# ① ヒアリング（5W2H）＋ PDF出力
# ============================================
st.header("ヒアリング（5W2H）")

TO_EMAIL_DEFAULT = payload.get("hearing",{}).get("pdf_recipient","")
base_defaults = {
    "name": payload.get("meta",{}).get("name",""),
    "now_area": "", "now_years": 5, "is_owner": "賃貸",
    "now_rent": 10, "family": "",
    "self_fund_man": 0, "other_debt": "",
    "husband_company": "", "husband_service_years": 3, "husband_workplace": "",
    "husband_income": 0, "husband_holidays": "",
    "wife_company": "", "wife_service_years": 3, "wife_workplace": "",
    "wife_income": 0, "wife_holidays": "",
    "sat_point": "", "search_status": "", "why_buy": "", "task": "",
    "anxiety": "", "rent_vs_buy": "", "other_trouble": "", "effect": "",
    "forecast": "", "event_effect": "", "missed_timing": "", "ideal_life": "",
    "solve_feeling": "", "goal": "", "important": "",
    "must": "", "want": "", "ng": "", "other_agent": "", "why_terass": "",
    "housing_cost": 10,
    "husband_commute": "", "wife_commute": "",
    "sat_price": 3, "sat_location": 3, "sat_size": 3, "sat_age": 3, "sat_spec": 3,
    "dissat_free": "",
    "self_fund": "", "gift_support": "",
    "w_why": "", "w_when": "", "w_where": "", "w_who": "",
    "w_what": "", "w_how": "", "w_howmuch": "", "w_free": "",
    "prio_price": 3, "prio_location": 3, "prio_size_layout": 3, "prio_spec": 3, "prio_mgmt": 3,
    "spec_parking": False, "spec_bicycle": False, "spec_ev": False, "spec_pet": False,
    "spec_barrierfree": False, "spec_security": False,
    "spec_disaster": False, "spec_mgmt_good": False, "spec_fee_ok": False, "spec_free": "",
    "contact_pref": "", "share_method": "", "pdf_recipient": TO_EMAIL_DEFAULT,
}

if ns("hearing_data") not in st.session_state:
    st.session_state[ns("hearing_data")] = payload.get("hearing", base_defaults.copy())
else:
    for k, v in base_defaults.items():
        st.session_state[ns("hearing_data")].setdefault(k, v)
hearing = st.session_state[ns("hearing_data")]

with st.form("hearing_form", clear_on_submit=False):
    st.markdown("#### 基礎情報")
    c1, c2, c3 = st.columns(3)
    with c1:
        hearing["name"]      = st.text_input("お名前", value=hearing["name"], key=ns("h_name"))
        hearing["now_area"]  = st.text_input("現在の居住エリア・駅", value=hearing["now_area"], key=ns("h_now_area"))
    with c2:
        hearing["now_years"] = st.number_input("居住年数（年）", 0, 100, _coerce_int(hearing["now_years"], 0), key=ns("h_now_years"))
        hearing["is_owner"]  = st.selectbox("持ち家・賃貸", ["賃貸", "持ち家"], index=0 if hearing["is_owner"]=="賃貸" else 1, key=ns("h_is_owner"))
    with c3:
        hearing["housing_cost"] = st.number_input("住居費（万円/月）", 0, 200, _coerce_int(hearing["housing_cost"], 0), key=ns("h_housing_cost"))
    hearing["family"] = st.text_input("ご家族構成（人数・年齢・将来予定）", value=hearing["family"], key=ns("h_family"))

    st.divider()

    st.markdown("#### 家計・勤務")
    ca, cb, cc = st.columns(3)
    with ca:
        hearing["self_fund_man"] = st.number_input("自己資金（万円）", min_value=0, value=_coerce_int(hearing.get("self_fund_man",0), 0), step=50, key=ns("h_self_fund_man"))
        hearing["other_debt"]    = st.text_input("他社借入（任意・金額/残債など）", value=hearing.get("other_debt",""), key=ns("h_other_debt"))
    with cb:
        st.caption("ご主人様")
        hearing["husband_company"]       = st.text_input("勤続先（会社名など）", value=hearing.get("husband_company",""), key=ns("h_hus_company"))
        hearing["husband_service_years"] = st.number_input("勤続年数（年）", min_value=0, max_value=80, value=_coerce_int(hearing.get("husband_service_years",0),0), key=ns("h_hus_years"))
        hearing["husband_workplace"]     = st.text_input("勤務地（最寄りエリア）", value=hearing.get("husband_workplace",""), key=ns("h_hus_workplace"))
        hearing["husband_income"]        = st.number_input("年収（万円）", min_value=0, value=_coerce_int(hearing.get("husband_income",0),0), step=50, key=ns("h_hus_income"))
        hearing["husband_holidays"]      = st.text_input("休日（例：土日祝／シフト制）", value=hearing.get("husband_holidays",""), key=ns("h_hus_holidays"))
    with cc:
        st.caption("奥様")
        hearing["wife_company"]       = st.text_input("勤続先（会社名など）", value=hearing.get("wife_company",""), key=ns("h_wife_company"))
        hearing["wife_service_years"] = st.number_input("勤続年数（年）", min_value=0, max_value=80, value=_coerce_int(hearing.get("wife_service_years",0),0), key=ns("h_wife_years"))
        hearing["wife_workplace"]     = st.text_input("勤務地（最寄りエリア）", value=hearing.get("wife_workplace",""), key=ns("h_wife_workplace"))
        hearing["wife_income"]        = st.number_input("年収（万円）", min_value=0, value=_coerce_int(hearing.get("wife_income",0),0), step=50, key=ns("h_wife_income"))
        hearing["wife_holidays"]      = st.text_input("休日（例：土日祝／シフト制）", value=hearing.get("wife_holidays",""), key=ns("h_wife_holidays"))

    st.divider()

    st.markdown("#### 現在の住まい（満足・不満）")
    hearing["sat_point"] = st.text_area("現在の住宅の満足点（自由入力）", value=hearing["sat_point"], key=ns("h_sat_point"))
    sc1, sc2, sc3, sc4, sc5 = st.columns(5)
    with sc1: hearing["sat_price"]    = st.slider("満足度：価格", 1, 5, _coerce_int(hearing["sat_price"],3), key=ns("h_sat_price"))
    with sc2: hearing["sat_location"] = st.slider("満足度：立地", 1, 5, _coerce_int(hearing["sat_location"],3), key=ns("h_sat_location"))
    with sc3: hearing["sat_size"]     = st.slider("満足度：広さ", 1, 5, _coerce_int(hearing["sat_size"],3), key=ns("h_sat_size"))
    with sc4: hearing["sat_age"]      = st.slider("満足度：築年数", 1, 5, _coerce_int(hearing["sat_age"],3), key=ns("h_sat_age"))
    with sc5: hearing["sat_spec"]     = st.slider("満足度：スペック", 1, 5, _coerce_int(hearing["sat_spec"],3), key=ns("h_sat_spec"))
    sat_total = int(hearing["sat_price"]) + int(hearing["sat_location"]) + int(hearing["sat_size"]) + int(hearing["sat_age"]) + int(hearing["sat_spec"])
    st.caption(f"満足度合計：**{sat_total} / 25**")
    hearing["dissat_free"] = st.text_area("不満な点（自由入力）", value=hearing["dissat_free"], key=ns("h_dissat_free"))

    st.divider()

    st.markdown("#### 5W2H（購入計画）")
    c1, c2 = st.columns(2)
    with c1:
        hearing["w_why"]   = st.text_input("Why（なぜ）：購入理由", value=hearing["w_why"], key=ns("h_w_why"))
        hearing["w_when"]  = st.text_input("When（いつ）：購入／入居タイミング", value=hearing["w_when"], key=ns("h_w_when"))
        hearing["w_where"] = st.text_input("Where（どこで）：希望エリア・沿線", value=hearing["w_where"], key=ns("h_w_where"))
        hearing["w_who"]   = st.text_input("Who（誰が）：居住メンバー", value=hearing["w_who"], key=ns("h_w_who"))
    with c2:
        hearing["w_what"]     = st.text_input("What（何を）：種別・広さ・階数・設備", value=hearing["w_what"], key=ns("h_w_what"))
        hearing["w_how"]      = st.text_input("How（どう買う）：ローン・頭金", value=hearing["w_how"], key=ns("h_w_how"))
        hearing["w_howmuch"]  = st.text_input("How much（いくら）：総予算／月返済上限", value=hearing["w_howmuch"], key=ns("h_w_howmuch"))
        hearing["w_free"]     = st.text_area("補足（自由入力）", value=hearing["w_free"], key=ns("h_w_free"))

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        save_only = st.form_submit_button("💾 入力を上書き保存")
    with col_b:
        save_and_pdf = st.form_submit_button("📄 保存してPDF作成")

# 保存ハンドラ
if 'save_only' in locals() and save_only:
    payload["hearing"] = dict(hearing)
    payload.setdefault("meta", {}).update({"name": hearing.get("name","")})
    save_client(client_id, payload)
    st.session_state[ns("hearing_data")] = dict(payload["hearing"])
    st.success("ヒアリングを上書き保存しました。")
    st.rerun()

if 'save_and_pdf' in locals() and save_and_pdf:
    payload["hearing"] = dict(hearing)
    payload.setdefault("meta", {}).update({"name": hearing.get("name","")})
    save_client(client_id, payload)
    st.session_state[ns("hearing_data")] = dict(payload["hearing"])
    st.success("ヒアリング内容を保存しました。PDFを生成します。")

    # === フォント準備 ===
    font_dir = _ensure_jp_fonts()
    reg_path = font_dir / _REG_NAME
    bld_path = font_dir / _BLD_NAME

    # === PDF生成 ===
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.add_font("NotoSansJP", "", str(reg_path), uni=True)
    pdf.add_font("NotoSansJP", "B", str(bld_path), uni=True)

    def _page_w(pdf_obj):
        return pdf_obj.w - pdf_obj.l_margin - pdf_obj.r_margin

    def title(t):
        pdf.set_font("NotoSansJP", "B", 14)
        pdf.set_x(pdf.l_margin)
        pdf.cell(0, 9, t, 0, 1)

    def pair(label, val):
        w = _page_w(pdf)
        pdf.set_x(pdf.l_margin)
        pdf.set_font("NotoSansJP", "B", 11)
        pdf.multi_cell(w, 7, label)
        pdf.set_x(pdf.l_margin)
        pdf.set_font("NotoSansJP", "", 11)
        txt = str(val) if val not in [None, ""] else "（未入力）"
        pdf.multi_cell(w, 7, txt)
        pdf.ln(1)

    pdf.set_font("NotoSansJP", "B", 16)
    pdf.set_x(pdf.l_margin)
    pdf.cell(0, 10, "不動産ヒアリングシート", 0, 1, "C")
    pdf.set_font("NotoSansJP", "", 10)
    pdf.set_x(pdf.l_margin)
    pdf.cell(0, 6, f"作成日時：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, "R")
    pdf.ln(2)

    title("基本情報")
    pair("お名前", hearing["name"])
    pair("現在の居住エリア・駅", hearing["now_area"])
    pair("居住年数（年）", hearing["now_years"])
    pair("種別（賃貸/持ち家）", hearing["is_owner"])
    pair("住居費（万円/月）", hearing["housing_cost"])
    pair("ご家族構成", hearing["family"])

    title("現在の住まい（満足・不満）")
    pair("満足点", hearing["sat_point"])
    pair("満足度（価格/立地/広さ/築年数/スペック）",
         f"{hearing['sat_price']}/{hearing['sat_location']}/{hearing['sat_size']}/{hearing['sat_age']}/{hearing['sat_spec']}")
    pair("不満な点", hearing["dissat_free"])

    title("5W2H（購入計画）")
    pair("Why", hearing["w_why"])
    pair("When", hearing["w_when"])
    pair("Where", hearing["w_where"])
    pair("Who", hearing["w_who"])
    pair("What", hearing["w_what"])
    pair("How", hearing["w_how"])
    pair("How much", hearing["w_howmuch"])
    pair("補足", hearing["w_free"])

    title("重要度のトレードオフ")
    pair("価格 / 立地 / 広さ・間取り / スペック / 管理その他",
         f"{hearing['prio_price']}/{hearing['prio_location']}/{hearing['prio_size_layout']}/{hearing['prio_spec']}/{hearing['prio_mgmt']}")

    title("連絡・共有")
    pair("希望連絡手段・時間帯", hearing["contact_pref"])
    pair("資料共有", hearing["share_method"])
    pair("PDF送付先", hearing["pdf_recipient"])

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        pdf.output(tmp_file.name)
        pdf_bytes = Path(tmp_file.name).read_bytes()

    st.download_button(
        "📄 PDFをダウンロード",
        data=pdf_bytes,
        file_name="hearing_sheet.pdf",
        mime="application/pdf",
    )
st.divider()

# ============================================
# ② 現状把握（現在の住宅の基礎情報）
# ============================================
st.header("現状把握（現在の住宅の基礎情報）")

b = payload["baseline"]

with st.form("baseline_form"):
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        b["housing_cost_m"] = st.number_input("住居費（万円/月）", 0, 200, _coerce_int(b.get("housing_cost_m",10),10), key=ns("b_housing_cost_m"))
        b["walk_min"] = st.number_input("最寄駅 徒歩（分）", 0, 60, _coerce_int(b.get("walk_min",10),10), key=ns("b_walk_min"))
    with c2:
        b["area_m2"] = st.number_input("専有面積（㎡）", 0, 300, _coerce_int(b.get("area_m2",60),60), key=ns("b_area_m2"))
        b["floor"] = st.number_input("所在階（数値）", 0, 70, _coerce_int(b.get("floor",3),3), key=ns("b_floor"))
    with c3:
        opts = [d for d,_ in _load_master_balcony_pairs()]
        cur_disp = _code_to_disp(b.get("balcony_aspect","S"))
        b_disp = st.selectbox("バルコニー向き", opts, index=opts.index(cur_disp) if cur_disp in opts else 4, key=ns("b_balcony"))
    with c4:
        b["view"] = st.selectbox("眺望", ["未設定","開放","一部遮り","正面に遮り"],
                                 index=["未設定","開放","一部遮り","正面に遮り"].index(b.get("view","未設定")), key=ns("b_view"))

    submitted_baseline = st.form_submit_button("💾 現状把握を上書き保存")

if submitted_baseline:
    b["balcony_aspect"] = _disp_to_code(b_disp)
    payload["baseline"] = dict(b)
    save_client(client_id, payload)
    st.success("現状把握を上書き保存しました。")
    st.rerun()

st.divider()

# ============================================
# ③ 現在の住居スコアリング
# ============================================
st.header("現在の住居スコアリング")

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
        # 管理・共用
        "c_box": False, "c_parking": "なし", "c_gomi24": False,
        "c_seismic": False, "c_security": False,
        "c_design_level": "普通",
        "c_ev_count": 0, "c_pet_ok": False,
    }
cur = payload["current_home"]

with st.expander("立地・環境", expanded=True):
    c1,c2,c3 = st.columns(3)
    with c1:
        cur["walk_min"] = st.number_input("最寄駅までの徒歩分数", 0, 60, _coerce_int(cur["walk_min"],10), key=ns("cur_walk_min"))
        cur["multi_lines"] = st.number_input("複数路線利用の可否（本数）", 0, 10, _coerce_int(cur["multi_lines"],1), key=ns("cur_multi_lines"))
        cur["access_min"] = st.number_input("職場までのアクセス時間（分）", 0, 180, _coerce_int(cur["access_min"],30), key=ns("cur_access_min"))
    with c2:
        cur["shop_level"] = st.selectbox("商業施設の充実度", ["充実","普通","乏しい"], index=["充実","普通","乏しい"].index(cur["shop_level"]), key=ns("cur_shop"))
        cur["edu_level"]  = st.selectbox("教育環境", ["良い","普通","弱い"], index=["良い","普通","弱い"].index(cur["edu_level"]), key=ns("cur_edu"))
        cur["med_level"]  = st.selectbox("医療施設の近さ", ["近い","普通","遠い"], index=["近い","普通","遠い"].index(cur["med_level"]), key=ns("cur_med"))
    with c3:
        cur["security_level"] = st.selectbox("治安", ["良い","普通","悪い"], index=["良い","普通","悪い"].index(cur["security_level"]), key=ns("cur_sec"))
        cur["hazard_level"]   = st.selectbox("災害リスク（ハザード）", ["低い","中","高"], index=["低い","中","高"].index(cur["hazard_level"]), key=ns("cur_hazard"))
        cur["park_level"]     = st.selectbox("公園・緑地（子育て環境）", ["充実","普通","乏しい"], index=["充実","普通","乏しい"].index(cur["park_level"]), key=ns("cur_park"))
        cur["noise_level"]    = st.selectbox("騒音", ["静か","普通","うるさい"], index=["静か","普通","うるさい"].index(cur["noise_level"]), key=ns("cur_noise"))

with st.expander("広さ・間取り", expanded=True):
    c1,c2,c3 = st.columns(3)
    with c1:
        cur["area_m2"] = st.number_input("専有面積（㎡）", 0.0, 300.0, _coerce_float(cur["area_m2"],60.0), key=ns("cur_area_m2"))
        cur["living_jyo"] = st.number_input("リビングの広さ（帖）", 0.0, 50.0, _coerce_float(cur["living_jyo"],12.0), key=ns("cur_living_jyo"))
        cur["layout_type"] = st.selectbox("間取りタイプ", ["田の字","ワイドスパン","センターイン","その他"], index=["田の字","ワイドスパン","センターイン","その他"].index(cur["layout_type"]), key=ns("cur_layout_type"))
    with c2:
        cur["storage_level"] = st.selectbox("収納量（WIC・SIC含む総合）", ["多い","普通","少ない"], index=["多い","普通","少ない"].index(cur["storage_level"]), key=ns("cur_storage_level"))
        cur["ceiling_level"] = st.selectbox("天井高", ["高い","普通","低い"], index=["高い","普通","低い"].index(cur["ceiling_level"]), key=ns("cur_ceiling_level"))
        opts2 = [d for d,_ in _load_master_balcony_pairs()]
        cur_disp2 = _code_to_disp(cur.get("balcony_aspect","S"))
        sel_disp2 = st.selectbox("バルコニー向き", opts2, index=opts2.index(cur_disp2) if cur_disp2 in opts2 else 4, key=ns("cur_balcony_aspect"))
        cur["balcony_aspect"] = _disp_to_code(sel_disp2)
    with c3:
        cur["balcony_depth_m"] = st.number_input("バルコニー奥行（m）", 0.0, 5.0, _coerce_float(cur.get("balcony_depth_m",1.5),1.5), step=0.1, key=ns("cur_balcony_depth_m"))
        cur["sun_wind_level"] = st.selectbox("採光・通風", ["良い","普通","悪い"], index=["良い","普通","悪い"].index(cur["sun_wind_level"]), key=ns("cur_sun_wind_level"))
        cur["hall_flow_level"] = st.selectbox("廊下幅・家事動線効率", ["良い","普通","悪い"], index=["良い","普通","悪い"].index(cur["hall_flow_level"]), key=ns("cur_hall_flow_level"))

with st.expander("専有部分スペック（ある/ない）", expanded=False):
    st.caption("【キッチン】")
    k1,k2,k3,k4,k5 = st.columns(5)
    with k1: cur["k_dishwasher"] = st.checkbox("食洗機", value=cur["k_dishwasher"], key=ns("cur_k_dishwasher"))
    with k2: cur["k_purifier"] = st.checkbox("浄水器／整水器", value=cur["k_purifier"], key=ns("cur_k_purifier"))
    with k3: cur["k_disposer"] = st.checkbox("ディスポーザー", value=cur["k_disposer"], key=ns("cur_k_disposer"))
    with k4: cur["k_highend_cooktop"] = st.checkbox("高機能コンロ（IH/高火力）", value=cur["k_highend_cooktop"], key=ns("cur_k_highend_cooktop"))
    with k5: cur["k_bi_oven"] = st.checkbox("ビルトインオーブン", value=cur["k_bi_oven"], key=ns("cur_k_bi_oven"))

    st.caption("【バスルーム】")
    b1,b2,b3,b4,b5 = st.columns(5)
    with b1: cur["b_dryer"] = st.checkbox("浴室暖房乾燥機", value=cur["b_dryer"], key=ns("cur_b_dryer"))
    with b2: cur["b_reheating"] = st.checkbox("追い焚き機能", value=cur["b_reheating"], key=ns("cur_b_reheating"))
    with b3: cur["b_mist_sauna"] = st.checkbox("ミストサウナ", value=cur["b_mist_sauna"], key=ns("cur_b_mist_sauna"))
    with b4: cur["b_tv"] = st.checkbox("浴室テレビ", value=cur["b_tv"], key=ns("cur_b_tv"))
    with b5: cur["b_window"] = st.checkbox("浴室に窓", value=cur["b_window"], key=ns("cur_b_window"))

    st.caption("【暖房・空調】")
    h1,h2 = st.columns(2)
    with h1: cur["h_floorheat"] = st.checkbox("床暖房", value=cur["h_floorheat"], key=ns("cur_h_floorheat"))
    with h2: cur["h_aircon_built"] = st.checkbox("エアコン（備付）", value=cur["h_aircon_built"], key=ns("cur_h_aircon_built"))

    st.caption("【窓・建具】")
    w1,w2,w3,w4 = st.columns(4)
    with w1: cur["w_multi"] = st.checkbox("複層ガラス", value=cur["w_multi"], key=ns("cur_w_multi"))
    with w2: cur["w_low_e"] = st.checkbox("Low-Eガラス", value=cur["w_low_e"], key=ns("cur_w_low_e"))
    with w3: cur["w_double_sash"] = st.checkbox("二重サッシ", value=cur["w_double_sash"], key=ns("cur_w_double_sash"))
    with w4: cur["w_premium_doors"] = st.checkbox("建具ハイグレード（鏡面等）", value=cur["w_premium_doors"], key=ns("cur_w_premium_doors"))

    st.caption("【収納】")
    s1,s2,s3,s4,s5 = st.columns(5)
    with s1: cur["s_allrooms"] = st.checkbox("全居室収納", value=cur["s_allrooms"], key=ns("cur_s_allrooms"))
    with s2: cur["s_wic"] = st.checkbox("WIC", value=cur["s_wic"], key=ns("cur_s_wic"))
    with s3: cur["s_sic"] = st.checkbox("SIC", value=cur["s_sic"], key=ns("cur_s_sic"))
    with s4: cur["s_pantry"] = st.checkbox("パントリー", value=cur["s_pantry"], key=ns("cur_s_pantry"))
    with s5: cur["s_linen"] = st.checkbox("リネン庫", value=cur["s_linen"], key=ns("cur_s_linen"))

    st.caption("【セキュリティ・通信】")
    t1,t2,t3 = st.columns(3)
    with t1: cur["sec_tvphone"] = st.checkbox("TVモニター付インターホン", value=cur["sec_tvphone"], key=ns("cur_sec_tvphone"))
    with t2: cur["sec_sensor"] = st.checkbox("玄関センサーライト", value=cur["sec_sensor"], key=ns("cur_sec_sensor"))
    with t3: cur["net_ftth"] = st.checkbox("光配線方式（各戸まで）", value=cur["net_ftth"], key=ns("cur_net_ftth"))

with st.expander("管理・共用部", expanded=False):
    m1,m2,m3,m4 = st.columns(4)
    with m1:
        cur["c_box"] = st.checkbox("宅配ボックス", value=cur["c_box"], key=ns("cur_c_box"))
        cur["c_parking"] = st.selectbox("駐車場形態", ["平置き","機械式","なし"], index=["平置き","機械式","なし"].index(cur["c_parking"]), key=ns("cur_c_parking"))
    with m2:
        cur["c_gomi24"] = st.checkbox("24時間ゴミ出し", value=cur["c_gomi24"], key=ns("cur_c_gomi24"))
        cur["c_seismic"] = st.checkbox("免震・制震構造", value=cur["c_seismic"], key=ns("cur_c_seismic"))
    with m3:
        cur["c_security"] = st.checkbox("オートロック等セキュリティ", value=cur["c_security"], key=ns("cur_c_security"))
        cur["c_design_level"] = st.selectbox("外観・エントランスのデザイン", ["良い","普通","弱い"], index=["良い","普通","弱い"].index(cur["c_design_level"]), key=ns("cur_c_design_level"))
    with m4:
        cur["c_ev_count"] = st.number_input("エレベーター台数（基数）", 0, 20, _coerce_int(cur["c_ev_count"],0), key=ns("cur_c_ev_count"))
        cur["c_pet_ok"] = st.checkbox("ペット飼育可", value=cur["c_pet_ok"], key=ns("cur_c_pet_ok"))

if st.button("💾 現状スコアリングを上書き保存", key=ns("save_curhome")):
    payload["current_home"] = dict(cur)
    save_client(client_id, payload)
    st.success("現状スコアリングを上書き保存しました。")
    st.rerun()

st.divider()

# ============================================
# ③.5 基本の希望条件（マスト）
# ============================================
st.header("基本の希望条件（マスト項目）")

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
        bp["budget_man"] = st.number_input("予算（万円）", min_value=0, value=_coerce_int(bp.get("budget_man") or 0, 0), step=100, key=ns("bp_budget"))
        bp["age_limit_year"] = st.number_input("築年数（〜年まで）", min_value=0, value=_coerce_int(bp.get("age_limit_year") or 0, 0), step=1, key=ns("bp_age_limit"))
        bp["dist_limit_min"] = st.number_input("駅までの距離（〜分）", min_value=0, value=_coerce_int(bp.get("dist_limit_min") or 0, 0), step=1, key=ns("bp_dist_limit"))
    with c2:
        bp["bus_ok"] = st.selectbox("バス便 可否", ["可","不可","不問"], index={"可":0,"不可":1,"不問":2}.get(bp.get("bus_ok","不問"),2), key=ns("bp_bus_ok"))
        bp["parking_must"] = st.checkbox("駐車場 必須", value=bool(bp.get("parking_must", False)), key=ns("bp_parking"))
        bp["types"] = st.multiselect("物件種別（複数選択可）", ["戸建","マンション","注文住宅（土地）","投資用","節税対策","リゾート"], default=bp.get("types", []), key=ns("bp_types"))
    with c3:
        bp["layout_free"] = st.text_input("間取り（記述）", value=bp.get("layout_free",""), key=ns("bp_layout_free"))
        bp["must_free"] = st.text_area("その他 MUST 条件（記述）", value=bp.get("must_free",""), height=90, key=ns("bp_must_free"))

    st.markdown("**エリア希望（第1〜第3）／自由記述**")
    a1,a2,a3,a4 = st.columns(4)
    with a1:
        bp["areas"]["line1"]    = st.text_input("第1：路線", value=bp["areas"].get("line1",""), key=ns("bp_line1"))
        bp["areas"]["ekifrom1"] = st.text_input("第1：駅（起点）", value=bp["areas"].get("ekifrom1",""), key=ns("bp_ekifrom1"))
        bp["areas"]["ekito1"]   = st.text_input("第1：駅（終点）", value=bp["areas"].get("ekito1",""), key=ns("bp_ekito1"))
    with a2:
        bp["areas"]["line2"]    = st.text_input("第2：路線", value=bp["areas"].get("line2",""), key=ns("bp_line2"))
        bp["areas"]["ekifrom2"] = st.text_input("第2：駅（起点）", value=bp["areas"].get("ekifrom2",""), key=ns("bp_ekifrom2"))
        bp["areas"]["ekito2"]   = st.text_input("第2：駅（終点）", value=bp["areas"].get("ekito2",""), key=ns("bp_ekito2"))
    with a3:
        bp["areas"]["line3"]    = st.text_input("第3：路線", value=bp["areas"].get("line3",""), key=ns("bp_line3"))
        bp["areas"]["ekifrom3"] = st.text_input("第3：駅（起点）", value=bp["areas"].get("ekifrom3",""), key=ns("bp_ekifrom3"))
        bp["areas"]["ekito3"]   = st.text_input("第3：駅（終点）", value=bp["areas"].get("ekito3",""), key=ns("bp_ekito3"))
    with a4:
        bp["areas"]["free"]     = st.text_area("（または）エリア自由記述", value=bp["areas"].get("free",""), height=90, key=ns("bp_area_free"))

    submitted_basic = st.form_submit_button("💾 基本の希望条件を上書き保存")

if submitted_basic:
    payload["basic_prefs"] = dict(bp)
    save_client(client_id, payload)
    st.success("基本の希望条件を上書き保存しました。")
    st.rerun()

# ========= 重要度（1=最優先〜5）重複なし UI =========
st.subheader("重要度のトレードオフ（1=最優先〜5）")
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

if ns("imp_state") not in st.session_state:
    st.session_state[ns("imp_state")] = _normalize_importance(bp.get("importance", {"price":1,"location":2,"size_layout":3,"spec":4,"management":5}))

def _available_for(cat_key: str):
    cur_all = dict(st.session_state[ns("imp_state")])
    cur_val = cur_all.get(cat_key)
    used_other = {v for k, v in cur_all.items() if k != cat_key}
    opts = [n for n in [1,2,3,4,5] if (n == cur_val) or (n not in used_other)]
    return opts, cur_val

def _on_change(cat_key: str, widget_key: str):
    new_val = st.session_state.get(widget_key, None)
    if new_val is None:
        return
    new_val = int(new_val)
    cur_all = dict(st.session_state[ns("imp_state")])
    old_self = cur_all.get(cat_key)
    for k in list(cur_all.keys()):
        if k != cat_key and cur_all[k] == new_val:
            occupied = set(cur_all.values()) - {old_self}
            free = [n for n in [1,2,3,4,5] if n not in occupied and n != new_val]
            cur_all[k] = free[0] if free else (6 - new_val)
    cur_all[cat_key] = new_val
    st.session_state[ns("imp_state")] = cur_all

def _fmt(n: int) -> str:
    return LABEL_MAP.get(n, f"{n}番")

row1 = st.columns(3); row2 = st.columns(2); rows = row1 + row2
for idx, (k, label) in enumerate(CATS):
    col = rows[idx]
    opts, curv = _available_for(k)
    key = ns(f"imp_{k}")
    col.selectbox(label, options=opts, index=opts.index(curv) if curv in opts else 0,
                  key=key, on_change=_on_change, args=(k, key,), format_func=_fmt,
                  help="各カテゴリに 1番〜5番 を重複なく割当て")

c1, c2 = st.columns(2)
with c1:
    if st.button("↺ リセット（1番→価格, 2番→立地 ...）", use_container_width=True, key=ns("imp_reset")):
        st.session_state[ns("imp_state")] = {k: i+1 for i,(k,_) in enumerate(CATS)}
        st.rerun()
with c2:
    if st.button("💾 重要度を上書き保存", type="primary", use_container_width=True, key=ns("imp_save")):
        bp["importance"] = dict(st.session_state[ns("imp_state")])
        payload["basic_prefs"] = bp
        save_client(client_id, payload)
        st.success("重要度を上書き保存しました。")
        st.rerun()

st.divider()

# ============================================
# ④ DBデバッグ / 一覧（任意）
# ============================================
st.header("データベース：一覧・デバッグ")

with st.expander("DB状態を表示", expanded=False):
    all_rows = load_all_clients()
    st.write(f"総件数：**{len(all_rows)}**")
    if all_rows:
        import pandas as pd
        df = pd.DataFrame(all_rows, columns=["id","created","name","phone","email","memo"])
        # 表示用に日付を文字列化
        df["created"] = df["created"].apply(lambda d: d.strftime("%Y-%m-%d %H:%M") if d else "")
        st.dataframe(df, use_container_width=True)

    # 参考：このIDのJSON確認は上の管理枠に配置済み