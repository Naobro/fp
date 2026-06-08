# pages/1_admin.py - 家族構成による動的表示対応版
import streamlit as st
import json, secrets, string, io
from datetime import datetime

st.set_page_config(page_title="管理：お客様ページ 管理", layout="wide")

from auth import check_admin
check_admin()

BASE_URL = st.secrets.get("BASE_URL", "https://naokifp.streamlit.app/")

def share_url_for(cid: str) -> str:
    base = (BASE_URL or "/").rstrip("/")
    if base.startswith("http"):
        return f"{base}/?client={cid}"
    return f"{base}?client={cid}"

from client_portal import get_sb
SB = get_sb()
TABLE_NAME = "client_profiles"

class KVStore:
    def __init__(self):
        self.sb = SB

    def get(self, key: str) -> dict | None:
        if not self.sb:
            return None
        res = (
            self.sb.table(TABLE_NAME)
            .select("*")
            .eq("client_id", key)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    def set(self, key: str, value: dict) -> None:
        if not self.sb or not isinstance(value, dict):
            return

        meta_src = value.get("meta") if isinstance(value.get("meta"), dict) else {}
        name = value.get("name") or meta_src.get("name")
        if not name or str(name).strip() == "":
            name = "(未入力)"

        src_meta = dict(meta_src)
        src_meta["client_id"] = key
        src_meta["name"] = name
        src_meta["created_at"] = src_meta.get("created_at") or datetime.now().isoformat()

        def safe_json(d: dict) -> dict:
            clean = {}
            for k, v in d.items():
                try:
                    json.dumps(v)
                    clean[k] = v
                except Exception:
                    continue
            return clean

        clean_meta = safe_json(src_meta)
        clean_profile = safe_json(value.get("profile") if isinstance(value.get("profile"), dict) else {})

        record = {
            "client_id": key,
            "name": name,
            "meta": clean_meta,
            "profile": clean_profile,
            "updated_at": datetime.now().isoformat(),
        }

        try:
            self.sb.table(TABLE_NAME).upsert(record, on_conflict="client_id").execute()
        except Exception as e:
            st.error(f"Supabase upsert 失敗: {e}")
            raise

    def delete(self, key: str) -> bool:
        if not self.sb:
            return False
        try:
            self.sb.table(TABLE_NAME).delete().eq("client_id", key).execute()
            return True
        except Exception as e:
            st.error(f"削除失敗: {e}")
            return False

    def all(self) -> dict:
        if not self.sb:
            return {}
        res = self.sb.table(TABLE_NAME).select("*").execute()
        return {r["client_id"]: r for r in (res.data or [])}

    def count(self) -> int:
        return len(self.all())

    def snapshot_bytes(self) -> bytes:
        buf = io.StringIO()
        json.dump({"clients": self.all()}, buf, ensure_ascii=False, indent=2)
        return buf.getvalue().encode("utf-8")

@st.cache_resource(show_spinner=False)
def get_kv() -> KVStore:
    return KVStore()

KV = get_kv()

def gen_id(n: int = 6) -> str:
    return "c-" + "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(n))

def save_client(client_id: str, payload: dict):
    meta = payload.get("meta", {})
    name = meta.get("name") or payload.get("name")
    meta["name"] = name
    meta["client_id"] = client_id
    meta["created_at"] = meta.get("created_at") or datetime.now().isoformat()
    payload["meta"] = meta
    payload["name"] = name
    KV.set(client_id, payload)
    st.toast(f"💾 {name} 様を保存しました", icon="✅")

def load_all_clients() -> list[dict]:
    raw = KV.all()
    out = []
    for cid, payload in raw.items():
        meta = payload.get("meta", {})
        try:
            created = datetime.fromisoformat(meta.get("created_at")) if meta.get("created_at") else None
        except Exception:
            created = None

        out.append({
            "id": cid,
            "name": meta.get("name") or "(無名)",
            "created": created,
            "customer_type": meta.get("customer_type", ""),
            "furigana": meta.get("furigana", ""),
            "phone": meta.get("phone", ""),
            "email": meta.get("email", ""),
            "current_station": meta.get("current_station", ""),
            "current_layout": meta.get("current_layout", ""),
            "current_rent": meta.get("current_rent", ""),
            "family_structure": meta.get("family_structure", ""),
            "wife_working": meta.get("wife_working", ""),
            "workplace": meta.get("workplace", ""),
            "workplace_station": meta.get("workplace_station", ""),
            "annual_income": meta.get("annual_income", ""),
            "own_funds": meta.get("own_funds", ""),
            "spouse_workplace": meta.get("spouse_workplace", ""),
            "spouse_workplace_station": meta.get("spouse_workplace_station", ""),
            "spouse_annual_income": meta.get("spouse_annual_income", ""),
            "household_annual_income": meta.get("household_annual_income", ""),
            "budget": meta.get("budget", ""),
            "desired_area": meta.get("desired_area", ""),
            "desired_spec": meta.get("desired_spec", ""),
            "memo": meta.get("memo", ""),
            "line_user_id": meta.get("line_user_id", ""),
            "line_name": meta.get("line_name", ""),
        })
    out.sort(key=lambda x: x["created"] or datetime.fromtimestamp(0), reverse=True)
    return out

def delete_client(client_id: str) -> bool:
    return KV.delete(client_id)

# ------------------------------------
# 新規発行フォーム（動的表示対応）
# ------------------------------------
st.header("🆕 お客様ページの新規発行")

st.markdown("#### STEP 1｜顧客区分")
customer_type = st.radio(
    "ご相談内容",
    ["購入", "売却", "その他"],
    horizontal=True
)

st.markdown("#### STEP 2｜基本情報（全員共通）")
c1, c2 = st.columns(2)
with c1:
    name = st.text_input("名前")
    furigana = st.text_input("フリガナ")
with c2:
    phone = st.text_input("電話番号")
    email = st.text_input("メールアドレス")

st.divider()

st.markdown("#### STEP 3｜現在の状況（全員共通）")
c3, c4 = st.columns(2)
with c3:
    current_station = st.text_input("現在の最寄駅")
    current_layout = st.text_input("現在の間取り")
    current_rent = st.text_input("現在の家賃")
    
    # ✅ 家族構成を選択肢に変更
    family_structure = st.selectbox(
        "家族構成",
        ["単身", "DINKS", "ご夫婦＋お子さん1人", "ご夫婦＋お子さん2人", "それ以外"]
    )

with c4:
    workplace = st.text_input("ご主人様 勤務先（会社名）")
    workplace_station = st.text_input("ご主人様 勤務先最寄駅")
    annual_income = st.text_input("ご主人様 年収")
    own_funds = st.text_input("自己資金")

# ✅ 家族構成が「単身」以外の場合の動的表示
wife_working = "いいえ"
spouse_workplace = ""
spouse_workplace_station = ""
spouse_annual_income = ""
household_annual_income = ""

if family_structure != "単身":
    st.markdown("#### STEP 3.5｜奥様の情報")
    wife_working = st.radio("奥様は働いていますか？", ["いいえ", "はい"], horizontal=True)
    
    # ✅ 奥様が働いている場合のみ詳細入力欄を表示
    if wife_working == "はい":
        st.info("💑 奥様の勤務先情報をご入力ください")
        cw1, cw2 = st.columns(2)
        with cw1:
            spouse_workplace = st.text_input("奥様 勤務先（会社名）")
            spouse_workplace_station = st.text_input("奥様 勤務先最寄駅")
        with cw2:
            spouse_annual_income = st.text_input("奥様 年収")
            household_annual_income = st.text_input("世帯年収（合計）")

st.divider()

# 区分別の詳細項目
budget = desired_area = desired_spec = ""
property_address = property_type = property_area = property_age = ""
remaining_debt = sell_reason = sell_timing = other_details = ""

if customer_type == "購入":
    st.markdown("#### STEP 4｜購入希望条件")
    c5, c6 = st.columns(2)
    with c5:
        budget = st.text_input("予算")
    with c6:
        desired_area = st.text_input("希望エリア")
    desired_spec = st.text_area("希望スペック（広さ・築年数・駅距離など自由記入）", height=100)

elif customer_type == "売却":
    st.markdown("#### STEP 4｜売却物件詳細")
    c7, c8 = st.columns(2)
    with c7:
        property_address = st.text_input("売却物件の住所")
        property_type = st.selectbox("物件種別", ["", "マンション", "戸建て", "土地", "その他"])
        property_area = st.text_input("広さ・面積")
    with c8:
        property_age = st.text_input("築年数")
        remaining_debt = st.text_input("住宅ローン残債")
        sell_timing = st.text_input("売却希望時期")
    sell_reason = st.text_area("売却理由・その他ご事情", height=100)

else:
    st.markdown("#### STEP 4｜ご相談内容詳細")
    other_details = st.text_area("相談内容（自由記入）", height=120)

st.divider()
memo = st.text_area("管理メモ（任意）", height=80)

# 保存ボタン
if st.button("新規作成", type="primary"):
    if not name.strip():
        st.error("お客様名を入力してください。")
    else:
        client_id = gen_id()

        base_meta = {
            "client_id": client_id,
            "created_at": datetime.now().isoformat(),
            "customer_type": customer_type,
            "name": name,
            "furigana": furigana,
            "phone": phone,
            "email": email,
            "current_station": current_station,
            "current_layout": current_layout,
            "current_rent": current_rent,
            "family_structure": family_structure,
            "wife_working": wife_working,
            "workplace": workplace,
            "workplace_station": workplace_station,
            "annual_income": annual_income,
            "own_funds": own_funds,
            "spouse_workplace": spouse_workplace,
            "spouse_workplace_station": spouse_workplace_station,
            "spouse_annual_income": spouse_annual_income,
            "household_annual_income": household_annual_income,
            "memo": memo,
            "line_user_id": "",
            "line_name": "",
        }

        if customer_type == "購入":
            base_meta.update({"budget": budget, "desired_area": desired_area, "desired_spec": desired_spec})
        elif customer_type == "売却":
            base_meta.update({"property_address": property_address, "property_type": property_type, "property_area": property_area, "property_age": property_age, "remaining_debt": remaining_debt, "sell_reason": sell_reason, "sell_timing": sell_timing})
        else:
            base_meta["other_details"] = other_details

        payload = {"meta": base_meta, "baseline": {}, "prefs": {}, "listings": []}
        save_client(client_id, payload)
        url = share_url_for(client_id)
        st.success("お客様用URLを発行しました。下のリンクを共有してください。")
        st.code(url, language="text")
        st.link_button("➡️ このままお客様ページを開く（新規タブ）", url, type="primary")

st.divider()

# ------------------------------------
# 一覧・検索・削除（家族構成対応表示）
# ------------------------------------
st.header("📋 お客様ページ 一覧")

clients = load_all_clients()
total = len(clients)
c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    q = st.text_input("検索（お客様名／ID）", value="")
with c2:
    sort_key = st.selectbox("並び順", ["作成が新しい順", "作成が古い順", "名前（A→Z）", "名前（Z→A）"])
with c3:
    st.metric("登録件数", total)

if q:
    q_lower = q.strip().lower()
    clients = [c for c in clients if q_lower in (c["name"] or "").lower() or q_lower in c["id"].lower()]

if sort_key == "作成が新しい順":
    clients.sort(key=lambda x: x["created"] or datetime.fromtimestamp(0), reverse=True)
elif sort_key == "作成が古い順":
    clients.sort(key=lambda x: x["created"] or datetime.fromtimestamp(0))
elif sort_key == "名前（A→Z）":
    clients.sort(key=lambda x: x["name"].lower())
else:
    clients.sort(key=lambda x: x["name"].lower(), reverse=True)

if not clients:
    st.info("該当データはありません。")
else:
    for c in clients:
        url = share_url_for(c["id"])

        with st.container(border=True):
            cols = st.columns([4, 4, 1])
            with cols[0]:
                source_badge = "📱 LINE" if c.get("line_user_id") else "✏️ 手動"
                
                # 家族構成バッジの追加
                family = c.get("family_structure", "")
                family_badge = f"　👨‍👩‍👧‍👦 {family}" if family else ""
                
                st.markdown(f"### {c['name']}　`{source_badge}`{family_badge}")
                
                furigana_info = f"（{c['furigana']}）" if c.get('furigana') else ""
                customer_type_badge = c.get('customer_type', '')
                created_str = c['created'].strftime('%Y-%m-%d %H:%M') if c['created'] else '-'
                
                st.caption(f"ID: {c['id']} • {customer_type_badge} • {furigana_info}")
                st.caption(f"作成: {created_str}")

            with cols[1]:
                st.caption("共有URL")
                st.code(url, language="text")
                st.link_button("🔗 お客様ページを開く", url, type="primary")

            with cols[2]:
                if st.button("🗑️", key=f"del-{c['id']}", help="削除"):
                    if delete_client(c["id"]):
                        st.success("削除しました")
                        st.rerun()

            # ✅ 詳細情報表示（家族構成に応じた表示）
            with st.expander("📋 詳細情報を表示"):
                d1, d2, d3 = st.columns(3)

                with d1:
                    st.markdown("**📞 連絡先情報**")
                    st.write(f"• 電話番号: {c.get('phone') or '未入力'}")
                    st.write(f"• メールアドレス: {c.get('email') or '未入力'}")
                    
                    st.markdown("**🏠 現在の状況**")
                    st.write(f"• 家族構成: {c.get('family_structure') or '未入力'}")
                    st.write(f"• 現在の最寄駅: {c.get('current_station') or '未入力'}")
                    st.write(f"• 現在の間取り: {c.get('current_layout') or '未入力'}")
                    st.write(f"• 現在の家賃: {c.get('current_rent') or '未入力'}")

                with d2:
                    st.markdown("**💼 ご主人様の勤務先情報**")
                    st.write(f"• 勤務先: {c.get('workplace') or '未入力'}")
                    st.write(f"• 勤務先最寄駅: {c.get('workplace_station') or '未入力'}")
                    st.write(f"• 年収: {c.get('annual_income') or '未入力'}")
                    st.write(f"• 自己資金: {c.get('own_funds') or '未入力'}")

                    # ✅ 家族構成による奥様情報の表示判定
                    family = c.get("family_structure", "").strip()
                    is_single = family == "単身"
                    spouse_info_exists = any([
                        c.get("spouse_workplace"),
                        c.get("spouse_workplace_station"),
                        c.get("spouse_annual_income"),
                        c.get("household_annual_income")
                    ])

                    if not is_single and spouse_info_exists:
                        st.divider()
                        st.markdown("**💑 奥様の勤務先情報**")
                        st.write(f"• 勤務先: {c.get('spouse_workplace') or '未入力'}")
                        st.write(f"• 勤務先最寄駅: {c.get('spouse_workplace_station') or '未入力'}")
                        st.write(f"• 年収: {c.get('spouse_annual_income') or '未入力'}")
                        st.write(f"• 世帯年収（合計）: {c.get('household_annual_income') or '未入力'}")

                with d3:
                    st.markdown("**🏡 購入希望条件**")
                    st.write(f"• 予算: {c.get('budget') or '未入力'}")
                    st.write(f"• 希望エリア: {c.get('desired_area') or '未入力'}")

                if c.get('desired_spec'):
                    st.markdown("**📝 希望スペック詳細**")
                    st.info(c['desired_spec'])

                if c.get('memo'):
                    st.markdown("**📋 管理メモ**")
                    st.warning(c['memo'])

                if c.get('line_user_id'):
                    st.markdown("**📱 LINE連携情報**")
                    st.caption(f"LINE表示名: {c.get('line_name', '未取得')}")

st.divider()

# ------------------------------------
# データベース管理
# ------------------------------------
with st.expander("🔧 データベース管理（デバッグ用）"):
    st.caption("データベース状態確認・バックアップ")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 DB統計表示"):
            st.write(f"総レコード数: {KV.count()}")
    with col2:
        if st.button("📥 DBバックアップ作成"):
            st.download_button("バックアップをダウンロード", KV.snapshot_bytes(), 
                             file_name=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 
                             mime="application/json")

from auth import admin_send_ui
admin_send_ui()
