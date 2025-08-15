# -*- coding: utf-8 -*-
import json
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd

st.set_page_config(page_title="物件比較（1件ずつ保存→一覧）", layout="wide")

# ====== ここだけお客様ごとに変更 ======
CLIENT_ID = "c-XXXXXX"   # ← お客様IDに置換（例: c-b62z51）
# =====================================

DATA_DIR = Path("data/clients")
DATA_DIR.mkdir(parents=True, exist_ok=True)

def _client_file(cid: str) -> Path:
    return DATA_DIR / f"{cid}.json"

def load_client(cid: str):
    f = _client_file(cid)
    if not f.exists():
        return None
    return json.loads(f.read_text(encoding="utf-8"))

def save_client(cid: str, data: dict):
    _client_file(cid).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def to_hensachi(avg_1to5: float) -> float:
    # 1.0→30, 3.0→50, 5.0→70（線形）
    return round(50 + (avg_1to5 - 3.0) * 10, 1)

# 3段階→点数（良い/普通/悪い 等）
def map3(x, good="良い", mid="普通", bad="悪い"):
    if x == good or x in ["充実","近い","静か","低い"]:
        return 5.0
    if x == mid:
        return 3.0
    return 2.5

def bool_score(b):  # ある/ない
    return 5.0 if b else 2.5

def price_score(price_m):
    if price_m == 0: return 3.0
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

# ========= データ読込 =========
payload = load_client(CLIENT_ID)
if not payload:
    st.error("このお客様IDのデータが見つかりません。先に 2_client_portal.py で作成・保存してください。")
    st.stop()

name = payload.get("meta",{}).get("name") or "お客様"
st.title("物件比較（現住居＝偏差値50 基準）")
st.caption(f"{name}（ID: {CLIENT_ID}）")

# 重み（ヒアリング反映。無ければ3）
pri = payload.get("hearing", {})
W_PRICE     = int(pri.get("prio_price", 3))
W_LOCATION  = int(pri.get("prio_location", 3))
W_SIZE      = int(pri.get("prio_size_layout", 3))
W_SPEC      = int(pri.get("prio_spec", 3))
W_MGMT      = int(pri.get("prio_mgmt", 3))

st.info(f"重み：価格{W_PRICE} / 立地{W_LOCATION} / 広さ{W_SIZE} / スペック{W_SPEC} / 管理{W_MGMT}")

baseline = payload.get("baseline", {})
current_home = payload.get("current_home", {})
if not baseline or not current_home:
    st.warning("基準となる現住居の“現状把握 / 現在の住居スコアリング”が未入力です。2_client_portal で保存してください。")

st.divider()

# ========= 1件ずつ 入力 → スコア → 保存 =========
st.subheader("物件を1件入力して保存（何件でも蓄積できます）")

with st.form("one_property_form"):
    prop_name = st.text_input("物件名（例：A_〇〇マンション〇〇号室）", value="")
    st.markdown("##### ① 価格")
    c1,c2,c3,c4 = st.columns(4)
    with c1:
        price_m = st.number_input("売出価格（万円）", 0, 50000, 0, key="p_price")
    with c2:
        tsubo_m = st.number_input("坪単価（万円/坪）", 0, 3000, 0, key="p_tsubo")
    with c3:
        fee_yen = st.number_input("管理費等（月額・円）", 0, 200000, 0, key="p_fee")
    with c4:
        renov_m = st.number_input("追加リフォーム費用（万円）", 0, 5000, 0, key="p_renov")

    st.markdown("##### ② 立地（資産性）")
    lc1,lc2,lc3 = st.columns(3)
    with lc1:
        walk = st.number_input("最寄徒歩（分）", 0, 60, 10, key="l_walk")
        lines = st.number_input("複線数（本）", 0, 10, 1, key="l_lines")
        acc = st.number_input("職場アクセス（分）", 0, 180, 30, key="l_acc")
    with lc2:
        shop = st.selectbox("商業施設", ["充実","普通","乏しい"], key="l_shop")
        edu = st.selectbox("教育", ["良い","普通","弱い"], key="l_edu")
        med = st.selectbox("医療", ["近い","普通","遠い"], key="l_med")
    with lc3:
        secu = st.selectbox("治安", ["良い","普通","悪い"], key="l_secu")
        haz  = st.selectbox("災害", ["低い","中","高"], key="l_haz")
        park = st.selectbox("公園・緑地", ["充実","普通","乏しい"], key="l_park")
        noise = st.selectbox("騒音", ["静か","普通","うるさい"], key="l_noise")

    st.markdown("##### ③ 広さ・間取り")
    sz1,sz2,sz3 = st.columns(3)
    with sz1:
        area = st.number_input("専有面積（㎡）", 0, 300, 60, key="s_area")
        liv  = st.number_input("リビング（帖）", 0, 50, 12, key="s_liv")
        layout = st.selectbox("間取りタイプ", ["田の字","ワイドスパン","センターイン","その他"], key="s_layout")
    with sz2:
        storage = st.selectbox("収納量", ["多い","普通","少ない"], key="s_storage")
        ceil = st.selectbox("天井高", ["高い","普通","低い"], key="s_ceil")
        aspect = st.selectbox("バルコニー向き", ["N","NE","E","SE","S","SW","W","NW"], key="s_aspect")
    with sz3:
        depth = st.number_input("バルコニー奥行（m）", 0.0, 5.0, 1.5, step=0.1, key="s_depth")
        sunwind = st.selectbox("採光・通風", ["良い","普通","悪い"], key="s_sunwind")
        flow = st.selectbox("廊下幅・家事動線", ["良い","普通","悪い"], key="s_flow")

    st.markdown("##### ④ スペック（専有部分・抜粋）")
    sp1,sp2,sp3,sp4 = st.columns(4)
    with sp1:
        dw   = st.checkbox("食洗機", key="sp_dw")
        disp = st.checkbox("ディスポーザー", key="sp_disp")
        pur  = st.checkbox("浄水器/整水器", key="sp_pur")
        oven = st.checkbox("ビルトインオーブン", key="sp_oven")
    with sp2:
        cook = st.checkbox("高機能コンロ", key="sp_cook")
        dry  = st.checkbox("浴室乾燥機", key="sp_dry")
        reh  = st.checkbox("追い焚き", key="sp_reh")
        sauna= st.checkbox("ミストサウナ", key="sp_sauna")
    with sp3:
        btv  = st.checkbox("浴室TV", key="sp_btv")
        bwin = st.checkbox("浴室に窓", key="sp_bwin")
        fh   = st.checkbox("床暖房", key="sp_fh")
        ac   = st.checkbox("エアコン（備付）", key="sp_ac")
    with sp4:
        lowe = st.checkbox("Low-E", key="sp_lowe")
        twin = st.checkbox("二重サッシ", key="sp_twin")
        multi= st.checkbox("複層ガラス", key="sp_multi")
        doors= st.checkbox("建具ハイグレード", key="sp_doors")

    st.markdown("##### ⑤ 管理・共有部・その他（抜粋）")
    mg1,mg2,mg3,mg4 = st.columns(4)
    with mg1:
        concierge = st.checkbox("コンシェルジュ", key="mg_conc")
        box = st.checkbox("宅配ボックス", key="mg_box")
        guest = st.checkbox("ゲストルーム", key="mg_guest")
    with mg2:
        lounge = st.checkbox("ラウンジ/キッズ", key="mg_lounge")
        gym = st.checkbox("ジム", key="mg_gym")
        pool = st.checkbox("プール", key="mg_pool")
    with mg3:
        parking = st.selectbox("駐車場形態", ["平置き","機械式","なし"], key="mg_parking")
        gomi = st.checkbox("24hゴミ出し", key="mg_gomi")
        seismic = st.checkbox("免震・制震", key="mg_seismic")
    with mg4:
        mgmt_sec = st.checkbox("セキュリティ強", key="mg_sec")
        design = st.selectbox("外観・エントランス", ["良い","普通","弱い"], key="mg_design")
        ev = st.number_input("EV台数（基数）", 0, 20, 2, key="mg_ev")

    submitted = st.form_submit_button("この物件を保存して一覧に追加")

# ---- スコア計算 & 保存 ----
def calc_scores():
    # ①価格
    s_price = (price_score(price_m) + tsubo_score(tsubo_m) + fee_score(fee_yen)) / 3
    # ②立地
    s_loc = ( (5.0 if walk<=5 else 4.0 if walk<=10 else 3.0 if walk<=15 else 2.5) +
              (5.0 if lines>=3 else 4.0 if lines==2 else 3.0 if lines==1 else 2.5) +
              (5.0 if acc<=20 else 4.0 if acc<=35 else 3.0 if acc<=50 else 2.5) +
              map3(shop,"充実","普通","乏しい") +
              map3(edu,"良い","普通","弱い") +
              map3(med,"近い","普通","遠い") +
              map3(secu,"良い","普通","悪い") +
              map3(haz,"低い","中","高") +
              map3(park,"充実","普通","乏しい") +
              map3(noise,"静か","普通","うるさい")
            ) / 10
    # ③広さ
    lay = 3.5 if layout in ["ワイドスパン","センターイン"] else 3.0
    s_size = ( size_score(area, liv) + lay + map3(storage,"多い","普通","少ない")
               + map3(ceil,"高い","普通","低い")
               + 3.0  # 向きは中立（必要なら係数化）
               + (4.0 if depth>=1.5 else 3.0)
               + map3(sunwind,"良い","普通","悪い")
               + map3(flow,"良い","普通","悪い")
             ) / 8
    # ④専有スペック
    keys_bool = [dw, disp, pur, oven, cook, dry, reh, sauna, btv, bwin, fh, ac, lowe, twin, multi, doors]
    s_spec = sum(bool_score(x) for x in keys_bool) / len(keys_bool)
    # ⑤管理
    mg_bool = [concierge, box, guest, lounge, gym, pool, gomi, seismic, (mgmt_sec==True)]
    ratio = (sum(1 for x in mg_bool if x) / len(mg_bool)) if mg_bool else 0.5
    s_mgmt = 2.5 + ratio * 2.5  # 2.5〜5.0
    return s_price, s_loc, s_size, s_spec, s_mgmt

if submitted:
    if not prop_name.strip():
        st.error("物件名を入力してください。")
    else:
        s_price, s_loc, s_size, s_spec, s_mgmt = calc_scores()
        wsum = W_PRICE + W_LOCATION + W_SIZE + W_SPEC + W_MGMT
        avg = (s_price*W_PRICE + s_loc*W_LOCATION + s_size*W_SIZE + s_spec*W_SPEC + s_mgmt*W_MGMT) / wsum
        hensachi = to_hensachi(avg)

        snap = {
            "name": prop_name.strip(),
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "score": {
                "price": round(s_price,1),
                "location": round(s_loc,1),
                "size": round(s_size,1),
                "spec": round(s_spec,1),
                "mgmt": round(s_mgmt,1),
                "avg": round(avg,2),
                "hensachi": hensachi,
            },
            "price": {"price_m": price_m, "tsubo_m": tsubo_m, "fee_yen": fee_yen, "renov_m": renov_m},
            "loc": {"walk": walk, "lines": lines, "acc": acc, "shop": shop, "edu": edu, "med": med, "secu": secu, "haz": haz, "park": park, "noise": noise},
            "size": {"area": area, "liv": liv, "layout": layout, "storage": storage, "ceil": ceil, "aspect": aspect, "depth": depth, "sunwind": sunwind, "flow": flow},
            "spec": {"dw":dw,"disp":disp,"pur":pur,"oven":oven,"cook":cook,"dry":dry,"reh":reh,"sauna":sauna,"btv":btv,"bwin":bwin,
                     "fh":fh,"ac":ac,"lowe":lowe,"twin":twin,"multi":multi,"doors":doors},
            "mgmt": {"concierge":concierge,"box":box,"guest":guest,"lounge":lounge,"gym":gym,"pool":pool,
                     "parking":parking,"gomi":gomi,"seismic":seismic,"sec":mgmt_sec,"design":design,"ev":ev},
        }

        payload.setdefault("comparisons", [])
        payload["comparisons"].append(snap)
        save_client(CLIENT_ID, payload)
        st.success(f"保存しました：{prop_name}（総合偏差値 {hensachi}）")

st.divider()

# ========= 保存済み 一覧 =========
st.subheader("保存済み一覧（A/B/C… を後から見返し・比較）")

comp = payload.get("comparisons", [])
if not comp:
    st.info("まだ保存された物件はありません。上で1件追加してください。")
else:
    for item in reversed(comp[-10:]):  # 直近10件までをカードで
        c1,c2,c3,c4,c5,c6,c7 = st.columns([2,1,1,1,1,1,1])
        with c1:
            st.markdown(f"**{item['name']}**")
            st.caption(item['ts'])
        with c2: st.metric("価格", f"{item['score']['price']}/5")
        with c3: st.metric("立地", f"{item['score']['location']}/5")
        with c4: st.metric("広さ", f"{item['score']['size']}/5")
        with c5: st.metric("専有スペック", f"{item['score']['spec']}/5")
        with c6: st.metric("管理その他", f"{item['score']['mgmt']}/5")
        with c7: st.metric("総合偏差値", f"{item['score']['hensachi']}")

        with st.expander("詳細（あった/なかった・入力値）", expanded=False):
            cur_spec = current_home if current_home else {}
            def diff_bool(label, key, group):
                tgt = item[group].get(key)
                cur = cur_spec.get(key)
                icon = "＋" if tgt and not cur else ("－" if (not tgt) and cur else "＝")
                st.write(f"- {label}：物件={'あり' if tgt else 'なし'} / 現住居={'あり' if cur else 'なし'}（{icon}）")

            st.markdown("**設備（専有）**")
            diff_cols = st.columns(2)
            with diff_cols[0]:
                for lb, ky in [("食洗機","dw"),("ディスポーザー","disp"),("浄水器/整水器","pur"),
                               ("ビルトインオーブン","oven"),("高機能コンロ","cook"),("浴室乾燥機","dry"),
                               ("追い焚き","reh"),("ミストサウナ","sauna")]:
                    diff_bool(lb, ky, "spec")
            with diff_cols[1]:
                for lb, ky in [("浴室TV","btv"),("浴室に窓","bwin"),("床暖房","fh"),("エアコン（備付）","ac"),
                               ("Low-E","lowe"),("二重サッシ","twin"),("複層ガラス","multi"),("建具ハイグレード","doors")]:
                    diff_bool(lb, ky, "spec")

            st.markdown("**管理・共有部（抜粋）**")
            for lb, ky in [("コンシェルジュ","concierge"),("宅配ボックス","box"),("ゲストルーム","guest"),
                           ("ラウンジ/キッズ","lounge"),("ジム","gym"),("プール","pool"),("24hゴミ出し","gomi"),
                           ("免震・制震","seismic"),("セキュリティ強","sec")]:
                diff_bool(lb, ky, "mgmt")

            st.divider()
            st.json(item)

    st.divider()
    rows = []
    for it in comp:
        rows.append({
            "日時": it["ts"],
            "物件名": it["name"],
            "価格(1-5)": it["score"]["price"],
            "立地(1-5)": it["score"]["location"],
            "広さ(1-5)": it["score"]["size"],
            "専有(1-5)": it["score"]["spec"],
            "管理(1-5)": it["score"]["mgmt"],
            "総合偏差値": it["score"]["hensachi"],
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

    col_del1, col_del2 = st.columns([1,4])
    with col_del1:
        if st.button("最後の保存を削除"):
            comp.pop()
            payload["comparisons"] = comp
            save_client(CLIENT_ID, payload)
            st.success("削除しました。ページを再表示してください。")