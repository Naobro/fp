import streamlit as st
import json
from pathlib import Path

st.set_page_config(page_title="理想の住まいへのロードマップ", layout="wide")

DATA_DIR = Path("data/clients")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# -------- ユーティリティ --------
def load_client(cid: str):
    f = DATA_DIR / f"{cid}.json"
    if not f.exists():
        return None
    return json.loads(f.read_text(encoding="utf-8"))

def save_client(cid: str, data: dict):
    f = DATA_DIR / f"{cid}.json"
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# 偏差値変換（暫定）：カテゴリー平均(1〜5)→ 50基準
def to_hensachi(avg_1to5: float) -> float:
    # 3.0 を 50、1.0→30、5.0→70 とする直線近似（まずはシンプルに）
    return round(50 + (avg_1to5 - 3.0) * 10, 1)

# 価格スコア（暫定）
def score_price(price_m: float, budget_m: float) -> float:
    if price_m is None or budget_m is None:
        return 3.0
    delta = price_m - budget_m  # +ならオーバー
    if delta <= -1000:  # 1000万円以上安い
        return 5.0
    if -1000 < delta <= -200:
        return 4.0
    if -200 < delta <= 0:
        return 3.5
    if 0 < delta <= 500:
        return 3.0
    if 500 < delta <= 1000:
        return 2.5
    return 2.0

# 立地スコア（暫定）徒歩&通勤
def score_location(walk_min, h_commute, w_commute):
    pts = []
    def s_walk(m):
        if m is None: return 3.0
        if m <= 5: return 5.0
        if m <=10: return 4.0
        if m <=15: return 3.0
        if m <=20: return 2.5
        return 2.0
    def s_comm(m):
        if m is None: return 3.0
        if m <=20: return 5.0
        if m <=35: return 4.0
        if m <=50: return 3.0
        if m <=65: return 2.5
        return 2.0
    pts.append(s_walk(walk_min))
    pts.append(s_comm(h_commute))
    pts.append(s_comm(w_commute))
    return sum(pts)/len(pts)

# 広さ・間取り（暫定）：面積と階数・角部屋など
def score_size_layout(area_m2, base_area_m2, floor, base_floor, corner, base_corner):
    pts = []
    # 面積：基準より広いほど加点
    if area_m2 and base_area_m2:
        ratio = area_m2 / base_area_m2
        if ratio >= 1.3: pts.append(5.0)
        elif ratio >= 1.15: pts.append(4.0)
        elif ratio >= 1.0: pts.append(3.5)
        elif ratio >= 0.9: pts.append(3.0)
        else: pts.append(2.5)
    else:
        pts.append(3.0)
    # 階
    if floor is not None and base_floor is not None:
        df = floor - base_floor
        if df >= +6: pts.append(4.5)
        elif df >= +3: pts.append(4.0)
        elif df >= 0: pts.append(3.5)
        elif df >= -2: pts.append(3.0)
        else: pts.append(2.5)
    else:
        pts.append(3.0)
    # 角部屋
    if corner is None or base_corner is None:
        pts.append(3.0)
    else:
        if corner and not base_corner: pts.append(4.0)
        elif corner == base_corner: pts.append(3.5)
        else: pts.append(3.0)
    return sum(pts)/len(pts)

# スペック一致率（◎=必須, ○=希望, △=どちらでも, ×=不要）
MAP_WISH = {"must":2.0, "want":1.0, "neutral":0.0, "no_need":0.0}
def score_spec(spec_wish: dict, spec_has: dict) -> float:
    if not spec_wish: return 3.0
    total_weight = 0.0
    got = 0.0
    for key, wish in spec_wish.items():
        w = MAP_WISH.get(wish, 0.0)
        total_weight += w
        if w == 0.0:
            # △/×は中立扱い
            continue
        has = bool(spec_has.get(key))
        if has:
            got += w
    if total_weight == 0.0:
        return 3.0
    ratio = got / total_weight
    # 取得率→1〜5
    if ratio >= 0.85: return 5.0
    if ratio >= 0.65: return 4.0
    if ratio >= 0.45: return 3.5
    if ratio >= 0.25: return 3.0
    return 2.5

# 管理・その他（暫定）：24hゴミ・セキュリティ・EV台数 等の簡易点
def score_management(features: dict) -> float:
    pts = 0.0; n = 0
    for k in ["garbage_24h","security_staffed","auto_lock","cctv","ev_count_ok"]:
        if k in features:
            n += 1
            pts += 1.0 if features[k] else 0.5  # ある=1.0, ない=0.5（中立寄せ）
    if n == 0: return 3.0
    # 0.5〜1.0 → 2.5〜5.0換算
    avg = pts/n  # 0.5〜1
    return 2.5 + (avg-0.5)*(5.0-2.5)/(1.0-0.5)

# -------- ここから画面 --------
st.title("理想の住まいへのロードマップ")

# --- URLパラメータ取得（PINは任意） ---
q = st.query_params
cid = q.get("client", [""])[0] if isinstance(q.get("client"), list) else q.get("client", "")
pin = q.get("pin", [""])[0] if isinstance(q.get("pin"), list) else q.get("pin", "")

if not cid:
    st.warning("URLに `?client=...` を付けてアクセスしてください。")
    st.stop()

data = load_client(cid)
if not data:
    st.error("クライアントIDが見つかりません。管理画面で発行してください。")
    st.stop()

# PIN が付いてきた場合だけチェック（無ければスキップ）
if pin and pin != data["meta"].get("pin"):
    st.error("PINが一致しません。URLをご確認ください。")
    st.stop()

st.success(f"{data['meta'].get('name','お客様')} 専用ページ（ID: {cid}）")

# ---- ステップ1：現住まい（基準＝偏差値50） ----
st.header("ステップ1：現住まい（基準）")
b = data["baseline"]

with st.form("baseline"):
    c1,c2,c3,c4 = st.columns(4)
    with c1:
        b["housing_cost_m"] = st.number_input("住居費（万円/月）", 0, 200, value=int(b["housing_cost_m"] or 10))
        b["walk_min"]       = st.number_input("最寄駅 徒歩（分）", 0, 60, value=int(b["walk_min"] or 10))
    with c2:
        b["area_m2"]        = st.number_input("専有面積（㎡）", 0, 300, value=int(b["area_m2"] or 60))
        b["floor"]          = st.number_input("所在階（数値）", 0, 70, value=int(b["floor"] or 3))
    with c3:
        b["corner"]         = st.selectbox("角部屋", ["不明","いいえ","はい"], index=0 if b["corner"] is None else (2 if b["corner"] else 1))
        b["inner_corridor"] = st.selectbox("内廊下", ["不明","いいえ","はい"], index=0 if b["inner_corridor"] is None else (2 if b["inner_corridor"] else 1))
    with c4:
        b["balcony_type"]   = st.selectbox("バルコニー種別", ["未設定","standard","wide","roof","garden"], index=["未設定","standard","wide","roof","garden"].index(b["balcony_type"] or "未設定"))
        b["balcony_aspect"] = st.selectbox("向き", ["未設定","N","E","S","W"], index=["未設定","N","E","S","W"].index(b["balcony_aspect"] or "未設定"))
    c5,c6 = st.columns(2)
    with c5:
        b["view"] = st.selectbox("眺望", ["未設定","開放","一部遮り","正面に遮り"], index=["未設定","開放","一部遮り","正面に遮り"].index(b["view"] or "未設定"))
    with c6:
        b["husband_commute_min"] = st.number_input("ご主人様 通勤（分）", 0, 180, value=int(b["husband_commute_min"] or 30))
        b["wife_commute_min"]    = st.number_input("奥様 通勤（分）", 0, 180, value=int(b["wife_commute_min"] or 40))
    # 現在スペック（必要になったら増やせます）
    st.caption("現住まいの設備（分かる範囲で）")
    specs = [
        "disposer","dishwasher","water_filter","ih_or_gas","bath_dryer","bath_1tsubo","vent_24h",
        "floor_heating","all_rooms_storage","wic","sic","alcove","trunk","slop_sink","insulation","soundproof"
    ]
    cols = st.columns(4)
    for i, key in enumerate(specs):
        with cols[i%4]:
            val = st.selectbox(f"・{key}", ["不明","無","有"], index={"不明":0,"無":1,"有":2}.get("不明" if b["spec_current"].get(key) is None else ("有" if b["spec_current"].get(key) else "無")))
            b["spec_current"][key] = (True if val=="有" else (False if val=="無" else None))
    if st.form_submit_button("保存"):
        save_client(cid, data)
        st.success("現住まい（基準）を保存しました。")

st.divider()

# ---- ステップ2：希望条件 ----
st.header("ステップ2：希望条件（重要度／◎○△×）")
p = data["prefs"]

c1,c2,c3,c4,c5 = st.columns(5)
with c1: p["importance"]["price"] = st.selectbox("重要：価格", [1,2,3,4,5], index=p["importance"]["price"]-1)
with c2: p["importance"]["location"] = st.selectbox("重要：立地", [1,2,3,4,5], index=p["importance"]["location"]-1)
with c3: p["importance"]["size_layout"] = st.selectbox("重要：広さ・間取り", [1,2,3,4,5], index=p["importance"]["size_layout"]-1)
with c4: p["importance"]["spec"] = st.selectbox("重要：スペック", [1,2,3,4,5], index=p["importance"]["spec"]-1)
with c5: p["importance"]["management"] = st.selectbox("重要：管理・その他", [1,2,3,4,5], index=p["importance"]["management"]-1)

cc1,cc2,cc3 = st.columns(3)
with cc1: p["budget_max_m"] = st.number_input("予算上限（万円）", 0, 50000, value=int(p["budget_max_m"] or 8000))
with cc2: p["min_floor"] = st.number_input("最低希望階数（何階以上）", 0, 70, value=int(p["min_floor"] or 0))
with cc3: p["min_floor_tolerance"] = st.number_input("許容幅（例：-2なら2階低くても可）", -10, 10, value=int(p["min_floor_tolerance"] or 0))

st.caption("スペック選好（◎=must / ○=want / △=neutral / ×=no_need）")
wish_choices = {"◎ 必要":"must","○ あったほうがよい":"want","△ どちらでもよい":"neutral","× なくてよい":"no_need"}
spec_keys = [
    "disposer","dishwasher","water_filter","ih_or_gas","bath_dryer","bath_1tsubo","vent_24h",
    "floor_heating","all_rooms_storage","wic","sic","alcove","trunk","slop_sink","insulation","soundproof",
    "concierge","delivery_box","guest_room","lounge_kids","gym_pool","parking_good","bicycle_good",
    "garbage_24h","seismic_isolation","auto_lock","cctv","security_staffed","ev_count_ok","pet_ok","entrance_design_good"
]
cols = st.columns(4)
for i, key in enumerate(spec_keys):
    with cols[i%4]:
        current = p["spec_wish"].get(key, "neutral")
        label = [k for k,v in wish_choices.items() if v==current][0] if current in wish_choices.values() else "△ どちらでもよい"
        sel = st.selectbox(f"・{key}", list(wish_choices.keys()), index=list(wish_choices.keys()).index(label))
        p["spec_wish"][key] = wish_choices[sel]

if st.button("希望条件を保存"):
    save_client(cid, data)
    st.success("希望条件を保存しました。")

st.divider()

# ---- ステップ3：物件入力→偏差値 ----
st.header("ステップ3：物件チェック（偏差値表示）")
with st.form("listing"):
    name = st.text_input("物件名＋部屋番号/階（例：東京マスタープレイス 12F）")
    price_m = st.number_input("価格（万円）", 0, 50000, 0)
    walk = st.number_input("最寄 徒歩（分）", 0, 60, 10)
    hcm  = st.number_input("ご主人様 通勤（分）", 0, 180, int(b["husband_commute_min"] or 30))
    wcm  = st.number_input("奥様 通勤（分）", 0, 180, int(b["wife_commute_min"] or 40))
    area = st.number_input("専有面積（㎡）", 0, 300, int(b["area_m2"] or 60))
    floor = st.number_input("所在階（数値）", 0, 70, int(b["floor"] or 3))
    corner = st.selectbox("角部屋", ["不明","いいえ","はい"], index=0)
    # スペック（主要のみ）
    st.caption("主要スペック（内見時にチェック）")
    has = {}
    mini = ["disposer","dishwasher","bath_dryer","floor_heating","wic","sic","concierge","delivery_box","guest_room","garbage_24h","auto_lock","cctv","security_staffed","ev_count_ok","pet_ok"]
    cols2 = st.columns(4)
    for i, key in enumerate(mini):
        with cols2[i%4]:
            has[key] = st.checkbox(key)

    run = st.form_submit_button("スコア計算")

if run:
    imp = p["importance"]
    # 各カテゴリー 1〜5
    s_price = score_price(price_m, p["budget_max_m"])
    s_loc   = score_location(walk, hcm, wcm)
    s_size  = score_size_layout(area, b["area_m2"], floor, b["floor"], True if corner=="はい" else (False if corner=="いいえ" else None), b["corner"])
    s_spec  = score_spec(p["spec_wish"], has)
    s_mgmt  = score_management({
        "garbage_24h": has.get("garbage_24h"),
        "security_staffed": has.get("security_staffed"),
        "auto_lock": has.get("auto_lock"),
        "cctv": has.get("cctv"),
        "ev_count_ok": has.get("ev_count_ok"),
    })

    # 重み付け平均（1〜5）
    wsum = imp["price"]+imp["location"]+imp["size_layout"]+imp["spec"]+imp["management"]
    avg = (
        s_price*imp["price"] +
        s_loc*imp["location"] +
        s_size*imp["size_layout"] +
        s_spec*imp["spec"] +
        s_mgmt*imp["management"]
    ) / wsum

    hensachi = to_hensachi(avg)

    st.subheader("結果")
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    with c1: st.metric("価格", f"{s_price:.1f}/5")
    with c2: st.metric("立地", f"{s_loc:.1f}/5")
    with c3: st.metric("広さ・間取り", f"{s_size:.1f}/5")
    with c4: st.metric("スペック", f"{s_spec:.1f}/5")
    with c5: st.metric("管理・その他", f"{s_mgmt:.1f}/5")
    with c6: st.metric("総合偏差値", f"{hensachi}")

    st.caption("※ 偏差値は暫定ロジック：カテゴリー平均 3.0→偏差値 50 になるよう線形換算。今後チューニング可。")