# client_portal.py
# 顧客専用ページ（/?client=ID で表示）
# ※ app.py等から client_portal.render(client_id="...") で呼び出し可能に修正
# ※ Supabase未設定/未インストールでも起動は継続（保存は無効化）

from __future__ import annotations
import os
from datetime import datetime
from typing import Any, Dict, Optional

import streamlit as st

# ---- Supabase の安全インポート（失敗してもアプリは起動） ----
# requirements.txt は `supabase>=2.6,<3.0` を使用想定（v2系）
try:
    from supabase import create_client, Client  # type: ignore
except Exception:
    create_client = None  # type: ignore
    Client = None         # type: ignore

# --------------------------------
# 共通ユーティリティ
# --------------------------------
def _get_secret(name: str, default: str = "") -> str:
    # st.secrets が未設定でも落ちない
    try:
        return st.secrets.get(name, os.getenv(name, default))
    except Exception:
        return os.getenv(name, default)

def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

# --------------------------------
# 設定値（secrets 優先）
# --------------------------------
SUPABASE_URL      = _get_secret("SUPABASE_URL", "")
SUPABASE_ANON_KEY = _get_secret("SUPABASE_ANON_KEY", "")
SUPABASE_SCHEMA   = _get_secret("SUPABASE_SCHEMA", "public")

TABLE_PROFILES = _get_secret("SUPABASE_TABLE_PROFILES", "client_profiles")
TABLE_RECORDS  = _get_secret("SUPABASE_TABLE_RECORDS",  "client_portal_records")
TABLE_EVENTS   = _get_secret("SUPABASE_TABLE_EVENTS",   "client_portal_events")

BASE_URL = _get_secret("BASE_URL", "")

# --------------------------------
# Supabase クライアント（安全版）
# --------------------------------
@st.cache_resource(show_spinner=False)
def get_sb() -> Optional["Client"]:
    if create_client is None:
        return None
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return None
    try:
        return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    except Exception:
        return None

SB = get_sb()

def sb_available() -> bool:
    return SB is not None

def share_url_for(cid: str) -> str:
    base = (BASE_URL or "/").rstrip("/")
    if base.startswith("http"):
        return f"{base}/?client={cid}"
    # BASE_URL 未設定時は相対
    return f"/?client={cid}"

# --------------------------------
# DB I/O ヘルパ（SB無しでも例外にしない）
# --------------------------------
def db_upsert_profile(client_id: str, payload: Dict[str, Any]) -> bool:
    if not sb_available():
        st.warning("（情報）Supabase未設定のため保存は無効です。")
        return False
    data = {"client_id": client_id, "profile": payload, "updated_at": now_iso()}
    try:
        SB.table(TABLE_PROFILES).upsert(data, on_conflict="client_id").execute()
        return True
    except Exception as e:
        st.error(f"プロフィール保存に失敗: {e}")
        return False

def db_get_profile(client_id: str) -> Dict[str, Any]:
    if not sb_available():
        return {}
    try:
        res = SB.table(TABLE_PROFILES).select("*").eq("client_id", client_id).limit(1).execute()
        if getattr(res, "data", None):
            row = res.data[0]
            return row.get("profile") or {}
        return {}
    except Exception as e:
        st.error(f"プロフィール読み込み失敗: {e}")
        return {}

def db_insert_record(client_id: str, record_type: str, payload: Dict[str, Any]) -> bool:
    if not sb_available():
        st.warning("（情報）Supabase未設定のため保存は無効です。")
        return False
    data = {
        "client_id": client_id,
        "record_type": record_type,  # "mortgage_proposal" / "property_note" / "free_memo" 等
        "payload": payload,
        "created_at": now_iso(),
    }
    try:
        SB.table(TABLE_RECORDS).insert(data).execute()
        return True
    except Exception as e:
        st.error(f"レコード保存に失敗: {e}")
        return False

def db_log_event(client_id: str, action: str, detail: Dict[str, Any] | None = None) -> None:
    if not sb_available():
        return
    data = {"client_id": client_id, "action": action, "detail": (detail or {}), "created_at": now_iso()}
    try:
        SB.table(TABLE_EVENTS).insert(data).execute()
    except Exception:
        pass

# --------------------------------
# 計算系（元利均等）
# --------------------------------
def monthly_payment_yen(principal_yen: int, annual_rate_percent: float, years: int) -> int:
    if years <= 0:
        return 0
    if annual_rate_percent <= 0:
        return int(round(principal_yen / (years * 12)))
    r = annual_rate_percent / 100 / 12
    n = years * 12
    a = principal_yen * (r * (1 + r) ** n) / ((1 + r) ** n - 1)
    return int(round(a))

# --------------------------------
# 各タブ UI
# --------------------------------
def _tab_profile(client_id: str) -> None:
    st.subheader("👤 基本プロフィール")
    loaded = db_get_profile(client_id)

    c1, c2, c3 = st.columns(3)
    with c1:
        name  = st.text_input("お名前", value=loaded.get("name", ""))
        phone = st.text_input("電話番号", value=loaded.get("phone", ""))
    with c2:
        email  = st.text_input("メール", value=loaded.get("email", ""))
        family = st.text_input("家族構成（例：夫婦+子1）", value=loaded.get("family", ""))
    with c3:
        budget_max_m = st.number_input("ご予算上限（万円）", min_value=0, step=10, value=int(loaded.get("budget_max_m", 0)))
        area_min_m2  = st.number_input("希望専有面積下限（㎡）", min_value=0, step=1, value=int(loaded.get("area_min_m2", 0)))

    memo = st.text_area("メモ（希望条件や注意点）", value=loaded.get("memo", ""), height=100)

    if st.button("プロフィールを保存する", type="primary"):
        payload = {
            "name": name,
            "phone": phone,
            "email": email,
            "family": family,
            "budget_max_m": int(budget_max_m) if budget_max_m else 0,
            "area_min_m2": int(area_min_m2) if area_min_m2 else 0,
            "memo": memo,
        }
        ok = db_upsert_profile(client_id, payload)
        if ok:
            db_log_event(client_id, "save_profile", {"keys": list(payload.keys())})
            st.toast("プロフィールを保存しました ✅")

def _tab_mortgage(client_id: str) -> None:
    st.subheader("🏦 住宅ローン提案（元利均等）")
    with st.form("mortgage_form"):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            price_m = st.number_input("物件価格（万円）", min_value=0, step=10, value=6000)
            down_m  = st.number_input("頭金（万円）", min_value=0, step=10, value=0)
        with c2:
            fees_m  = st.number_input("諸費用（万円）", min_value=0, step=10, value=300)
            years   = st.number_input("返済期間（年）", min_value=1, max_value=45, step=1, value=35)
        with c3:
            rate    = st.number_input("適用金利（年利%）", min_value=0.0, step=0.01, value=0.59)
            bonus_y = st.number_input("ボーナス加算（円/回）", min_value=0, step=10000, value=0)
        with c4:
            other   = st.text_input("補足（金融機関・特約等）", value="")

        submitted = st.form_submit_button("この条件で試算する", type="primary")

    if submitted:
        borrow_m = max(0, int(price_m) - int(down_m)) + int(fees_m)
        principal_yen = borrow_m * 10000
        monthly = monthly_payment_yen(principal_yen, float(rate), int(years))
        total_monthly = monthly  # ボーナス分は別計上

        st.success("試算結果")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("借入額（万円）", f"{borrow_m:,}")
        with c2:
            st.metric("月々返済（円）", f"{total_monthly:,}")
        with c3:
            st.metric("ボーナス（円/回）", f"{int(bonus_y):,}")
        with c4:
            st.metric("年利（%）", f"{float(rate):.3f}")

        payload = {
            "price_m": int(price_m),
            "down_m": int(down_m),
            "fees_m": int(fees_m),
            "borrow_m": int(borrow_m),
            "years": int(years),
            "rate_percent": float(rate),
            "bonus_per_time_yen": int(bonus_y),
            "monthly_yen": int(total_monthly),
            "note": other,
            "calculated_at": now_iso(),
        }
        if db_insert_record(client_id, "mortgage_proposal", payload):
            db_log_event(client_id, "save_mortgage", {"borrow_m": borrow_m, "monthly": total_monthly})
            st.toast("Supabase に保存しました ✅")

def _tab_property(client_id: str) -> None:
    st.subheader("🏢 検討物件メモ")
    with st.form("prop_form"):
        c1, c2, c3 = st.columns([3, 2, 2])
        with c1:
            title = st.text_input("物件名 / 号室 等", value="")
            url   = st.text_input("物件URL（任意）", value="")
        with c2:
            price_m = st.number_input("価格（万円）", min_value=0, step=10, value=0)
            size_m2 = st.number_input("専有面積（㎡）", min_value=0, step=1, value=0)
        with c3:
            floor = st.number_input("階数", min_value=0, step=1, value=0)
            walk  = st.number_input("駅徒歩（分）", min_value=0, step=1, value=0)

        note = st.text_area("メモ（良い点・気になる点・管理/修繕/眺望など）", height=120)
        ok = st.form_submit_button("この物件メモを保存", type="primary")

    if ok:
        payload = {
            "title": title,
            "url": url,
            "price_m": int(price_m),
            "size_m2": int(size_m2),
            "floor": int(floor),
            "walk_min": int(walk),
            "note": note,
            "saved_at": now_iso(),
        }
        if db_insert_record(client_id, "property_note", payload):
            db_log_event(client_id, "save_property_note", {"title": title})
            st.toast("保存しました ✅")

def _tab_misc(client_id: str) -> None:
    st.subheader("📝 自由メモ / 添付（メタ情報）")
    memo = st.text_area("打合せメモ・要望など", height=160)
    tag  = st.text_input("タグ（カンマ区切り・任意）", value="")
    if st.button("メモを保存", type="primary"):
        payload = {
            "memo": memo,
            "tags": [t.strip() for t in tag.split(",") if t.strip()],
            "saved_at": now_iso(),
        }
        if db_insert_record(client_id, "free_memo", payload):
            db_log_event(client_id, "save_free_memo", {"len": len(memo)})
            st.toast("保存しました ✅")

# --------------------------------
# 公開API：render() ＝ app.py から呼べる
# --------------------------------
def render(client_id: Optional[str] = None) -> None:
    """app.py などから client_portal.render(client_id=...) で呼び出し可能"""
    st.set_page_config(page_title="お客様ページ（顧客専用）", layout="wide")

    # client_id が渡されていなければ、クエリから取得
    if not client_id:
        try:
            # Streamlit 1.30+ 互換
            q = st.query_params
            cid = q.get("client")
        except Exception:
            # 古いバージョン互換
            q = st.experimental_get_query_params()
            cid = q.get("client", [None])[0] if isinstance(q.get("client"), list) else q.get("client")
        client_id = cid

    st.title("お客様専用ページ")
    st.caption("このページの入力・提案は **Supabase（外部DB）** に保存されます。")

    if not client_id:
        st.warning("URL に `?client=ID` を付けるか、管理画面（1_admin.py）から発行したリンクでアクセスしてください。")
        return

    st.info(f"クライアントID：**{client_id}**  |  共有URL：{share_url_for(client_id)}")

    if sb_available():
        db_log_event(client_id, "open", {"user_agent": st.session_state.get("_browser", "")})
    else:
        st.error("Supabase 未設定のため保存できません。`SUPABASE_URL` / `SUPABASE_ANON_KEY` を設定してください。")

    tabs = st.tabs(["👤 プロフィール", "🏦 住宅ローン提案", "🏢 物件メモ", "📝 自由メモ"])
    with tabs[0]:
        _tab_profile(client_id)
    with tabs[1]:
        _tab_mortgage(client_id)
    with tabs[2]:
        _tab_property(client_id)
    with tabs[3]:
        _tab_misc(client_id)

    st.divider()
    st.caption(f"Schema: `{SUPABASE_SCHEMA}`  Tables: `{TABLE_PROFILES}`, `{TABLE_RECORDS}`, `{TABLE_EVENTS}`")

# --------------------------------
# 直接実行時（ローカル動作確認用）
# --------------------------------
if __name__ == "__main__":
    render()
