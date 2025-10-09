import streamlit as st
import uuid
import urllib.parse
from datetime import datetime
from typing import Dict

try:
    from supabase import create_client, Client
except Exception:
    create_client = None
    Client = None


# ---------------- Supabase接続 ----------------
import streamlit as st
from supabase import create_client, Client

def get_sb() -> Client | None:
    """Supabaseクライアントを生成して返す"""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_SERVICE_KEY"]
        if not url or not key:
            return None
        return create_client(url, key)
    except Exception as e:
        st.error(f"Supabase接続失敗: {e}")
        return None

SB = get_sb()

# ----------- 外部リンク保存を profile 内に格納する -----------
def upsert_links(client_id: str, links: list[Dict[str, str]]):
    if SB is None:
        return

    existing = (
        SB.table("client_profiles")
        .select("profile")
        .eq("client_id", client_id)
        .limit(1)
        .execute()
    )

    if existing.data and isinstance(existing.data[0].get("profile"), dict):
        profile = existing.data[0]["profile"]
    else:
        profile = {}

    profile["extra_links"] = links

    data = {
        "client_id": client_id,
        "profile": profile,
        "updated_at": datetime.now().isoformat(),
    }

    SB.table("client_profiles").upsert(data, on_conflict="client_id").execute()


def get_links(client_id: str) -> list[Dict[str, str]]:
    if SB is None:
        return []
    res = (
        SB.table("client_profiles")
        .select("profile")
        .eq("client_id", client_id)
        .limit(1)
        .execute()
    )
    if res.data:
        profile = res.data[0].get("profile") or {}
        return profile.get("extra_links", [])
    return []


# ---------------- URL生成 ----------------
APP_BASE = "https://naokifp.streamlit.app"
PAGES = {
    "ヒアリング": "/hearing",
    "住宅ローン提案": "/mortgageplan",
    "物件比較": "/compare",
    "諸費用": "/諸費用",
    "必要書類チェックリスト": "/checklists",
    "ライフプランニング": "/ライフプラン",
    "購入と賃貸比較": "/予算",
    "修繕積立金妥当性": "/修繕積立金_収益性",
    "家賃補助と購入": "/家賃補助",
    "社宅と購入": "/社宅シミュレーション",
    "購入時期シミュレーション": "/購入時期",
}


def short_code() -> str:
    return "c-" + uuid.uuid4().hex[:6]


def get_client_code() -> str:
    q = st.query_params
    code = q.get("client")
    if isinstance(code, list):
        code = code[0] if code else None
    if not code:
        code = short_code()
        st.query_params.update({"client": code})
    return str(code)


def build_url(path: str, cid: str) -> str:
    safe_path = urllib.parse.quote(path, safe="/")
    return f"{APP_BASE}{safe_path}?client={urllib.parse.quote(cid)}"


def main(client_id: str | None = None):
    st.set_page_config(page_title="クライアント専用ポータル", layout="wide")

    if not client_id:
        client_id = get_client_code()

    # --- クライアント名の取得 ---
    client_name = None
    if SB is not None:
        try:
            res = (
                SB.table("client_profiles")
                .select("name, profile")
                .eq("client_id", client_id)
                .limit(1)
                .execute()
            )
            if res.data:
                row = res.data[0]
                # 1) name カラムに値がある場合
                if row.get("name"):
                    client_name = row["name"]
                # 2) profile 内に name が入っている場合
                elif isinstance(row.get("profile"), dict) and row["profile"].get("name"):
                    client_name = row["profile"]["name"]
        except Exception as e:
            st.error(f"クライアント情報取得エラー: {e}")

    # --- タイトル表示 ---
    if client_name:
        st.title(f"👤 {client_name} 様 専用ページ")
    else:
        st.title("👤 クライアント専用ページ")

    st.info(f"クライアントID: **{client_id}**")

    # --- 固定リンク ---
    st.subheader("📋 固定リンク")
    for title, path in PAGES.items():
        url = build_url(path, client_id)
        st.markdown(f"- [{title}]({url})")

    st.divider()

    # --- 外部リンク管理 ---
    st.subheader("🔗 外部リンク（管理者用）")
    links = get_links(client_id)

    for i, link in enumerate(links):
        col1, col2, col3 = st.columns([3, 6, 2])
        with col1:
            t = st.text_input(f"タイトル {i+1}", link.get("title", ""), key=f"title_{i}")
        with col2:
            u = st.text_input(f"URL {i+1}", link.get("url", ""), key=f"url_{i}")
        with col3:
            if st.button("削除", key=f"del_{i}"):
                links.pop(i)
                upsert_links(client_id, links)
                st.rerun()
        link["title"], link["url"] = t, u

    with st.form("new_link", clear_on_submit=True):
        nt = st.text_input("新しいリンク名")
        nu = st.text_input("新しいURL")
        add = st.form_submit_button("追加")
        if add and nt and nu:
            links.append({"title": nt, "url": nu})
            upsert_links(client_id, links)
            st.rerun()

    if st.button("💾 保存"):
        upsert_links(client_id, links)
        st.success("保存しました")
if __name__ == "__main__":
    main()


# ============ 共通DBユーティリティ ============

def now_iso():
    """現在時刻を ISO8601 文字列で返す"""
    import datetime

    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def db_insert_record(client_id: str, table: str, payload: dict) -> bool:
    """SupabaseにレコードをINSERT"""
    try:
        res = SB.table(table).insert({**payload, "client_id": client_id}).execute()
        return True if res.data else False
    except Exception as e:
        st.error(f"DB保存エラー: {e}")
        return False


def db_log_event(client_id: str, event: str, payload: dict) -> None:
    """操作ログを記録"""
    try:
        SB.table("event_logs").insert(
            {
                "client_id": client_id,
                "event": event,
                "payload": payload,
                "created_at": now_iso(),
            }
        ).execute()
    except Exception as e:
        st.warning(f"ログ保存失敗: {e}")
