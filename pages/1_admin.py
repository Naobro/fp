# pages/1_admin.py  — 管理画面（新規発行・一覧・検索・即アクセス・削除）
import streamlit as st
import json, secrets, string, sqlite3
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from contextlib import contextmanager

# 画面設定
st.set_page_config(page_title="管理：お客様ページ 管理", layout="wide")

# 共有URL（本番URLを secrets で上書き可）
BASE_URL = st.secrets.get("BASE_URL", "https://naokifp.streamlit.app/client_portal")

# データベース設定
DB_PATH = "clients.db"

# 定数
CLIENT_ID_LENGTH = 6
IDEMPOTENCY_KEY_LENGTH = 16

# -------------------------------
# データベース管理
# -------------------------------
@contextmanager
def get_db():
    """データベース接続のコンテキストマネージャー"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 辞書形式でアクセス可能
    try:
        yield conn
    finally:
        conn.close()

def _has_column(conn: sqlite3.Connection, table: str, col: str) -> bool:
    """指定されたテーブルに指定されたカラムが存在するかチェックする"""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"] == col for r in rows)

def ensure_schema():
    """
    テーブル作成＋不足カラムの追加（安全な移行）。
    - idempotency_key: 重複作成防止の一意キー
    - created_at_utc : 作成時刻（UTC保存）
    既にカラムがある/インデックスがある環境でも落ちないように try/except で保護。
    """
    with get_db() as conn:
        # 既存環境を壊さない最低限の定義（IF NOT EXISTS）
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                client_id TEXT PRIMARY KEY,
                created_at TEXT, -- 互換性のために残すが、created_at_utc を優先
                name TEXT,
                phone TEXT,
                email TEXT,
                memo TEXT,
                data TEXT NOT NULL
            )
        """)

        # 追加カラムは存在チェック＋try/except（古いSQLiteでも安全）
        if not _has_column(conn, "clients", "idempotency_key"):
            try:
                conn.execute("ALTER TABLE clients ADD COLUMN idempotency_key TEXT")
            except sqlite3.OperationalError:
                pass  # 既にある等は無視

        if not _has_column(conn, "clients", "created_at_utc"):
            try:
                conn.execute("ALTER TABLE clients ADD COLUMN created_at_utc TEXT")
            except sqlite3.OperationalError:
                pass

        # 一意インデックス（NULLは重複許容になる仕様）
        try:
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_clients_idem ON clients(idempotency_key)")
        except sqlite3.OperationalError:
            pass

        # 既存行の created_at_utc を補完（created_at があれば流用、無ければ現在UTC）
        try:
            conn.execute("""
                UPDATE clients
                   SET created_at_utc = COALESCE(
                        created_at_utc,
                        created_at,
                        strftime('%Y-%m-%dT%H:%M:%SZ')  -- 現在UTC
                   )
                 WHERE created_at_utc IS NULL
            """)
        except sqlite3.OperationalError:
            pass

        conn.commit()

# 起動時にスキーマを保証
ensure_schema()

# -------------------------------
# 共通ユーティリティ
# -------------------------------
def utc_now_iso() -> str:
    """UTCのISO8601（末尾Z）"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def to_jst_str(utc_iso: str) -> str:
    """UTC(ISO) → JST 文字列"""
    if not utc_iso:
        return "-"
    try:
        # Z 付き・オフセット付きの両方に対応
        if utc_iso.endswith("Z"):
            dt = datetime.strptime(utc_iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        else:
            # ISOフォーマットだがタイムゾーン情報がない場合はUTCと仮定
            dt = datetime.fromisoformat(utc_iso)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        # datetime.strptime や fromisoformat のフォーマットエラー
        return f"Invalid date format: {utc_iso}"
    except Exception as e:
        # その他の予期せぬエラー
        return f"Error converting date: {e} ({utc_iso})"

def gen_id(n: int = CLIENT_ID_LENGTH) -> str:
    """クライアントID生成"""
    alphabet = string.ascii_lowercase + string.digits
    return "c-" + "".join(secrets.choice(alphabet) for _ in range(n))

def save_client(client_id: str, payload: dict, idempotency_key: str) -> bool:
    """
    クライアント保存。重複防止のため idempotency_key を UNIQUE で使用。
    既に同じキーで挿入済みなら NO-OP（失敗ではない）。
    """
    meta = payload.get("meta", {})
    with get_db() as conn:
        # SQLite 3.24+ で有効（Streamlit Cloudは対応）
        # created_at (ローカル時刻) は互換性のために残すが、created_at_utc を主に使用
        conn.execute("""
            INSERT INTO clients
                (client_id, idempotency_key, created_at_utc, created_at, name, phone, email, memo, data)
            VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(idempotency_key) DO NOTHING
        """, (
            client_id,
            idempotency_key,
            meta.get("created_at_utc"),
            meta.get("created_at"),  # 互換のため残す
            meta.get("name"),
            meta.get("phone"),
            meta.get("email"),
            meta.get("memo"),
            json.dumps(payload, ensure_ascii=False)
        ))
        conn.commit()
        # 直近1行が本当に挿入されたかを判定（既存キーなら 0 件）
        ch = conn.execute("SELECT COUNT(*) AS c FROM clients WHERE idempotency_key = ?", (idempotency_key,)).fetchone()
        return ch and ch["c"] == 1

def load_client(client_id: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT data FROM clients WHERE client_id = ?", (client_id,)).fetchone()
        return json.loads(row["data"]) if row and row["data"] else None

def load_all_clients():
    """全クライアント（JST表示のために created_at_utc を読む）"""
    items = []
    with get_db() as conn:
        rows = conn.execute("""
            SELECT client_id, created_at_utc, name, phone, email, memo, data
              FROM clients
          ORDER BY created_at_utc DESC, rowid DESC
        """).fetchall()
        for r in rows:
            items.append({
                "id": r["client_id"],
                "name": r["name"] or "(無名)",
                "created_utc": r["created_at_utc"],
                "created_jst": to_jst_str(r["created_at_utc"]),
                "phone": r["phone"],
                "email": r["email"],
                "memo": r["memo"],
                "raw": json.loads(r["data"]) if r["data"] else {}
            })
    return items

def delete_client(client_id: str) -> bool:
    try:
        with get_db() as conn:
            cur = conn.execute("DELETE FROM clients WHERE client_id = ?", (client_id,))
            conn.commit()
            return cur.rowcount > 0
    except sqlite3.OperationalError as e:
        st.error(f"データベースエラーが発生しました: {e}")
        return False
    except Exception as e:
        st.error(f"予期せぬエラーが発生しました: {e}")
        return False

def share_url_for(cid: str) -> str:
    base = BASE_URL.rstrip("/")
    return f"{base}?client={cid}"

# -------------------------------
# 新規発行（PINなし）
# -------------------------------
st.header("お客様ページの新規発行（PINなし）")

# 1クリック多重実行ガード（idempotency 用キー）
if "__create_idem__" not in st.session_state:
    st.session_state["__create_idem__"] = None

with st.form("new_client"):
    c1, c2 = st.columns(2)
    with c1:
        name  = st.text_input("お客様名")
    with c2:
        phone = st.text_input("電話番号（任意）")
        email = st.text_input("メール（任意）")
        memo  = st.text_area("管理メモ（任意）", height=80)
    submitted = st.form_submit_button("新規作成", type="primary")

if submitted:
    # 必須チェック（空欄や空白のみは拒否）
    name_clean = (name or "").strip()
    if not name_clean:
        st.error("お客様名は必須です。空欄では作成できません。")
        st.session_state["__create_idem__"] = None # 再試行のためにキーをリセット
        st.stop() # Streamlit アプリの実行を停止

    # 余計な空白を正規化
    name_clean = " ".join(name_clean.split())

    # 初回クリック時にのみ idempotency_key を採番して保持
    idem = st.session_state.get("__create_idem__")
    if not idem:
        idem = secrets.token_hex(IDEMPOTENCY_KEY_LENGTH)  # 一意キー
        st.session_state["__create_idem__"] = idem

    client_id = gen_id()
    payload = {
        "meta": {
            "client_id": client_id,
            "created_at_utc": utc_now_iso(),
            "created_at": datetime.now().isoformat(),  # 互換のため残す
            "name": name_clean,
            "phone": (phone or "").strip(),
            "email": (email or "").strip(),
            "memo": memo or "",
        },
        "baseline": {
            "housing_cost_m": None,
            "walk_min": None,
            "area_m2": None,
            "floor": None,
            "corner": None,
            "inner_corridor": None,
            "balcony_type": None,
            "balcony_aspect": None,
            "view": None,
            "husband_commute_min": None,
            "wife_commute_min": None,
            "spec_current": {}
        },
        "prefs": {
            "importance": {"price": 3, "location": 3, "size_layout": 3, "spec": 3, "management": 3},
            "budget_max_m": None,
            "min_floor": None,
            "min_floor_tolerance": 0,
            "spec_wish": {}
        },
        "listings": []
    }

    # ★ 重要：idempotency_key を渡して保存（多重作成を防ぐ）
    ok = save_client(client_id, payload, idempotency_key=idem)

    url = share_url_for(client_id)
    if ok:
        st.success("お客様用URLを発行しました。下のリンクを共有してください。")
        st.code(url, language="text")
        # st.link_button("➡️ このままお客様ページを開く（新規タブ）", url, type="primary") # key引数は不要
        st.link_button("➡️ このままお客様ページを開く（新規タブ）", url, type="primary")
    else:
        # 直前のリラン等で重複呼び出されたケース（DBには既に存在）
        st.info("同じ操作がすでに登録済みです（重複作成は行っていません）。")
        st.code(url, language="text")
        # st.link_button("➡️ お客様ページを開く（新規タブ）", url, type="primary") # key引数は不要
        st.link_button("➡️ お客様ページを開く（新規タブ）", url, type="primary")

    # 次の新規作成のためにキーをリセットするボタンを出す
    if st.button("＋ もう一件登録する"):
        st.session_state["__create_idem__"] = None
        st.rerun()

st.divider()

# -------------------------------
# 一覧・検索・即アクセス・削除
# -------------------------------
st.header("お客様ページ 一覧")

clients = load_all_clients()
total = len(clients)

c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    q = st.text_input("検索（お客様名／ID 含む）", value="")
with c2:
    sort_key = st.selectbox("並び順", ["作成が新しい順", "作成が古い順", "名前（A→Z）", "名前（Z→A）"])
with c3:
    st.metric("登録件数", total)

# フィルタ
if q:
    q_lower = q.strip().lower()
    clients = [c for c in clients if q_lower in (c["name"] or "").lower() or q_lower in (c["id"] or "").lower()]

# ソート（created_jst を文字列比較しても日付順になるようフォーマット済み）
def jst_sort_key(c):  # YYYY-mm-dd HH:MM なので文字列順≒時刻順
    return c["created_jst"] or ""

if sort_key == "作成が新しい順":
    clients.sort(key=jst_sort_key, reverse=True)
elif sort_key == "作成が古い順":
    clients.sort(key=jst_sort_key)
elif sort_key == "名前（A→Z）":
    clients.sort(key=lambda x: (x["name"] or "").lower())
else:
    clients.sort(key=lambda x: (x["name"] or "").lower(), reverse=True)

# 一括削除UI
st.subheader("一括削除")
left, right = st.columns([3, 2])
with left:
    ids_for_delete = st.multiselect(
        "削除したいお客様を選択",
        options=[f'{c["name"]}（{c["id"]}）' for c in clients],
        key="bulk_delete_select"
    )
with right:
    st.warning("この操作は取り消せません。慎重に実行してください。")
    confirm_text = st.text_input('最終確認：DELETE と入力で実行', value="", key="bulk_delete_confirm")
    do_bulk = st.button("選択を削除する", type="secondary")

if do_bulk:
    if confirm_text.strip() != "DELETE":
        st.error("削除を実行するには、確認欄に DELETE と入力してください。")
    else:
        deleted = 0
        pick_ids = []
        for label in ids_for_delete:
            if "（" in label and "）" in label:
                cid = label.split("（")[-1].split("）")[0]
            else:
                cid = label # ラベル形式が異なる場合も考慮（念のため）
            pick_ids.append(cid)
        
        if not pick_ids:
            st.info("削除対象が選択されていません。")
        else:
            for cid in pick_ids:
                if delete_client(cid):
                    deleted += 1
            if deleted > 0:
                st.success(f"{deleted} 件削除しました。")
                st.rerun()
            else:
                st.info("削除対象が見つからなかったか、すでに削除されています。")

st.divider()

# 行表示（即アクセス＋個別削除）
st.subheader("一覧")

if not clients:
    st.info("該当データはありません。")
else:
    for c in clients:
        url = share_url_for(c["id"])
        cols = st.columns([3, 2, 2, 3, 1])
        with cols[0]:
            st.write(f"**{c['name']}**")
            st.caption(f"ID: {c['id']}")
        with cols[1]:
            st.caption("作成日時（JST）")
            st.write(c["created_jst"])
        with cols[2]:
            st.caption("共有URL")
            # urlが有効かチェックして表示
            if url:
                st.code(url, language="text")
            else:
                st.caption("URL生成エラー") # urlがNoneの場合

        with cols[3]:
            st.caption("操作")
            # DEBUG: st.write(f"DEBUG: url='{url}', client_id='{c['id']}'")
            if url: # url が None や空文字列でないことを確認
                # st.link_button は key 引数を受け付けないため削除
                st.link_button("開く（新規タブ）", url, type="primary")
            else:
                st.warning("無効なURLです") # urlがNoneの場合
        with cols[4]:
            # 個別削除ボタンの確認フロー
            delete_confirmed = st.session_state.get(f"confirm_delete_{c['id']}", False)
            if not delete_confirmed:
                if st.button("🗑️", key=f"del_prompt-{c['id']}"):
                    st.session_state[f"confirm_delete_{c['id']}"] = True
                    st.rerun() # 確認表示のために再描画
            else:
                st.warning(f"本当に {c['name']} を削除しますか？")
                confirm_col1, confirm_col2 = st.columns(2)
                with confirm_col1:
                    if st.button("はい、削除する", key=f"del_yes-{c['id']}"):
                        if delete_client(c["id"]):
                            st.success("削除しました")
                            del st.session_state[f"confirm_delete_{c['id']}"] # 状態をリセット
                            st.rerun()
                        else:
                            st.error("削除に失敗しました")
                with confirm_col2:
                    if st.button("キャンセル", key=f"del_no-{c['id']}"):
                        del st.session_state[f"confirm_delete_{c['id']}"] # 状態をリセット
                        st.rerun()
        st.markdown("---") # 区切り線で各行を見やすくする

# -------------------------------
# データベース管理ユーティリティ（デバッグ用）
# -------------------------------
with st.expander("🔧 データベース管理（デバッグ用）"):
    st.caption("データベースの状態確認・メンテナンス用")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("DB統計表示"):
            with get_db() as conn:
                count = conn.execute("SELECT COUNT(*) as cnt FROM clients").fetchone()["cnt"]
                oldest_row = conn.execute("SELECT MIN(created_at_utc) as oldest FROM clients").fetchone()
                newest_row = conn.execute("SELECT MAX(created_at_utc) as newest FROM clients").fetchone()
                
                oldest = oldest_row["oldest"] if oldest_row else "N/A"
                newest = newest_row["newest"] if newest_row else "N/A"

                st.write(f"総レコード数: {count}")
                st.write(f"最古(UTC): {oldest}")
                st.write(f"最新(UTC): {newest}")
    with col2:
        if st.button("DBバックアップ作成"):
            backup_data = []
            with get_db() as conn:
                rows = conn.execute("SELECT * FROM clients").fetchall()
                for row in rows:
                    backup_data.append(dict(row))
            backup_json = json.dumps(backup_data, ensure_ascii=False, indent=2)
            st.download_button(
                "📥 バックアップダウンロード",
                backup_json,
                file_name=f"clients_backup_{datetime.now(ZoneInfo('Asia/Tokyo')).strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    with col3:
        if st.button("⚠️ DB全削除（危険）"):
            st.warning("この操作は全データを削除します！実行前に必ずバックアップを取ってください。")
            confirm_delete_all = st.text_input('本当に削除するには "DELETE ALL" と入力', key="confirm_delete_all_input") # keyを変更
            if confirm_delete_all == "DELETE ALL":
                if st.button("全データを削除", type="danger", key="confirm_delete_all_button"): # keyを変更
                    with get_db() as conn:
                        conn.execute("DELETE FROM clients")
                        conn.commit()
                        st.success("全データを削除しました。")
                        st.rerun()
