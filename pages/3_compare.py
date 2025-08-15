# -*- coding: utf-8 -*-
import streamlit as st
import json
from pathlib import Path

st.set_page_config(page_title="物件比較（現住居=偏差値50）", layout="wide")

DATA_DIR = Path("data/clients")

def load_client(cid: str):
    f = DATA_DIR / f"{cid}.json"
    if not f.exists():
        return None
    return json.loads(f.read_text(encoding="utf-8"))

# ===== スコア関数（1〜5点） =====
def map3(x, good="良い", mid="普通", bad="悪い"):
    if x == good or x in ["充実","近い","静か","低い"]:
        return 5.0
    if x == mid:
        return 3.0
    return 2.0

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

def mgmt_score(m):
    pts = 0; n = 0
    for k in ["concierge","box","guest","lounge","gym","pool","gomi","seismic","sec","brand","pet"]:
        if k in m:
            n += 1
            pts += 1 if m[k] else 0
    if n == 0: return 3.0
    ratio = pts / n
    return 2.5 + ratio * 2.5  # 2.5〜5.0

# 相対偏差値（現住居を50）
def hensachi_relative(avg, baseline_avg):
    return round(50 + (avg - baseline_avg) * 10, 1)

# ===== 画面本体（ランチャーから client_id を渡す） =====
def render_compare(client_id: str):
    payload = load_client(client_id)
    if not payload:
        st.error("このお客様IDのデータが見つかりません。")
        st.stop()

    st.title("物件比較（現住居=偏差値50）")
    st.caption(f"対象お客様：{payload.get('meta',{}).get('name','')}（ID: {client_id}）")

    # 重み（ヒアリングから）
    pri = payload.get("hearing", {})
    w_price = int(pri.get("prio_price", 3))
    w_location = int(pri.get("prio_location", 3))
    w_size = int(pri.get("prio_size_layout", 3))
    w_spec = int(pri.get("prio_spec", 3))
    w_mgmt = int(pri.get("prio_mgmt", 3))
    st.info(f"重み（価格:{w_price} / 立地:{w_location} / 広さ・間取り:{w_size} / スペック:{w_spec} / 管理:{w_mgmt}）")

    # ---- 現住居の“平均点（1〜5）”を同ロジックで算出 → baseline_avg
    # 入力は payload["baseline"] / ["current_home"] を使う
    b = payload.get("baseline", {})
    cur = payload.get("current_home", {})

    # 価格カテゴリは現住居には価格がない＝中立 3.0
    s_price_base = 3.0

    # 立地（walk/access他）
    def s_loc_from(cur):
        walk = int(cur.get("walk_min", 10))
        lines = int(cur.get("multi_lines", 1))
        acc = int(cur.get("access_min", 30))
        shop = cur.get("shop_level", "普通"); edu = cur.get("edu_level","普通"); med = cur.get("med_level","普通")
        sec = cur.get("security_level","普通"); haz = cur.get("hazard_level","中")
        park = cur.get("park_level","普通"); noise = cur.get("noise_level","普通")
        val = (
            (5.0 if walk<=5 else 4.0 if walk<=10 else 3.0 if walk<=15 else 2.5) +
            (5.0 if lines>=3 else 4.0 if lines==2 else 3.0 if lines==1 else 2.5) +
            (5.0 if acc<=20 else 4.0 if acc<=35 else 3.0 if acc<=50 else 2.5) +
            map3(shop,"充実","普通","乏しい") + map3(edu,"良い","普通","弱い") +
            map3(med,"近い","普通","遠い") + map3(sec,"良い","普通","悪い") +
            map3(haz,"低い","中","高") + map3(park,"充実","普通","乏しい") +
            map3(noise,"静か","普通","うるさい")
        )/10
        return val

    s_loc_base = s_loc_from(cur if cur else {"walk_min":b.get("walk_min",10),"access_min":30,"multi_lines":1})

    # 広さ・間取り
    def s_size_from(cur, b):
        area = float(cur.get("area_m2", b.get("area_m2", 60)))
        liv  = float(cur.get("living_jyo", 12))
        layout = cur.get("layout_type", "田の字")
        storage = cur.get("storage_level","普通")
        ceil = cur.get("ceiling_level","普通")
        depth = float(cur.get("balcony_depth_m", b.get("balcony_depth_m",1.5)))
        sunwind = cur.get("sun_wind_level","普通")
        flow = cur.get("hall_flow_level","普通")
        lay = 3.5 if layout in ["ワイドスパン","センターイン"] else 3.0
        return (
            size_score(area, liv) + lay + map3(storage,"多い","普通","少ない") +
            map3(ceil,"高い","普通","低い") + 3.0 +
            (4.0 if depth>=1.5 else 3.0) + map3(sunwind,"良い","普通","悪い") + map3(flow,"良い","普通","悪い")
        )/8

    s_size_base = s_size_from(cur, b)

    # スペック（専有）
    def s_spec_from(cur):
        keys = [
            "k_dishwasher","k_disposer","k_purifier","k_bi_oven","k_highend_cooktop",
            "b_dryer","b_reheating","b_mist_sauna","b_tv","b_window",
            "h_floorheat","h_aircon_built",
            "w_low_e","w_double_sash","w_multi","w_premium_doors",
            "s_allrooms","s_wic","s_sic","s_pantry","s_linen",
            "sec_tvphone","sec_sensor","net_ftth"
        ]
        return sum(bool_score(bool(cur.get(k, False))) for k in keys)/len(keys)

    s_spec_base = s_spec_from(cur)

    # 管理・その他（最低限）
    s_mgmt_base = mgmt_score({
        "concierge": False,
        "box": bool(cur.get("c_box", True)),
        "guest": False,
        "lounge": False,
        "gym": False,
        "pool": False,
        "gomi": bool(cur.get("c_gomi24", True)),
        "seismic": bool(cur.get("c_seismic", False)),
        "sec": bool(cur.get("c_security", True)),
        "brand": False,
        "pet": bool(cur.get("c_pet_ok", True)),
    })

    wsum = w_price + w_location + w_size + w_spec + w_mgmt
    baseline_avg = (
        s_price_base*w_price +
        s_loc_base*w_location +
        s_size_base*w_size +
        s_spec_base*w_spec +
        s_mgmt_base*w_mgmt
    ) / max(wsum, 1)

    st.success(f"現住居の基準平均：{baseline_avg:.2f}（この値が**偏差値50**の中心）")

    # =========================
    # 物件入力（横並び A/B/C）
    # =========================
    st.subheader("横並び入力：A・B・C")
    if "compare_rows" not in st.session_state:
        st.session_state["compare_rows"] = 3
    rows = st.session_state["compare_rows"]
    cols = st.columns(rows)
    names = []
    for i in range(rows):
        with cols[i]:
            names.append(st.text_input(f"物件名 {chr(65+i)}", value=f"物件{chr(65+i)}"))

    st.divider()

    # --- ① 価格
    st.markdown("### ① 価格")
    c_price = st.columns(rows)
    price_val = []; tsubo_val = []; fee_val = []; renov_val = []
    for i in range(rows):
        with c_price[i]:
            price_val.append(st.number_input(f"{names[i]}：売出価格（万円）", 0, 50000, 0, key=f"price_{i}"))
            tsubo_val.append(st.number_input(f"{names[i]}：坪単価（万円/坪）", 0, 2000, 0, key=f"tsubo_{i}"))
            fee_val.append(st.number_input(f"{names[i]}：管理費等（月額・円）", 0, 200000, 0, key=f"fee_{i}"))
            renov_val.append(st.number_input(f"{names[i]}：追加リフォーム費用（万円）", 0, 5000, 0, key=f"renov_{i}"))

    # --- ② 立地
    st.markdown("### ② 立地（資産性）")
    loc_inputs = []
    for i in range(rows):
        c1,c2,c3 = st.columns(3)
        with c1:
            walk = st.number_input(f"{names[i]}：最寄徒歩（分）", 0, 60, 10, key=f"walk_{i}")
            lines = st.number_input(f"{names[i]}：複線数（本）", 0, 10, 1, key=f"lines_{i}")
            acc = st.number_input(f"{names[i]}：職場アクセス（分）", 0, 180, 30, key=f"acc_{i}")
        with c2:
            shop = st.selectbox(f"{names[i]}：商業施設", ["充実","普通","乏しい"], key=f"shop_{i}")
            edu  = st.selectbox(f"{names[i]}：教育", ["良い","普通","弱い"], key=f"edu_{i}")
            med  = st.selectbox(f"{names[i]}：医療", ["近い","普通","遠い"], key=f"med_{i}")
        with c3:
            sec  = st.selectbox(f"{names[i]}：治安", ["良い","普通","悪い"], key=f"sec_{i}")
            haz  = st.selectbox(f"{names[i]}：災害", ["低い","中","高"], key=f"haz_{i}")
            park = st.selectbox(f"{names[i]}：公園・緑地", ["充実","普通","乏しい"], key=f"park_{i}")
            noise= st.selectbox(f"{names[i]}：騒音", ["静か","普通","うるさい"], key=f"noise_{i}")
        loc_inputs.append((walk,lines,acc,shop,edu,med,sec,haz,park,noise))

    # --- ③ 広さ・間取り
    st.markdown("### ③ 広さ・間取り")
    size_inputs = []
    for i in range(rows):
        c1,c2,c3 = st.columns(3)
        with c1:
            area = st.number_input(f"{names[i]}：専有面積（㎡）", 0, 300, 60, key=f"area_{i}")
            liv  = st.number_input(f"{names[i]}：リビング（帖）", 0, 50, 12, key=f"liv_{i}")
            layout = st.selectbox(f"{names[i]}：間取りタイプ", ["田の字","ワイドスパン","センターイン","その他"], key=f"layout_{i}")
        with c2:
            storage = st.selectbox(f"{names[i]}：収納量", ["多い","普通","少ない"], key=f"storage_{i}")
            ceil = st.selectbox(f"{names[i]}：天井高", ["高い","普通","低い"], key=f"ceil_{i}")
            aspect = st.selectbox(f"{names[i]}：バルコニー向き", ["N","NE","E","SE","S","SW","W","NW"], key=f"aspect_{i}")
        with c3:
            depth = st.number_input(f"{names[i]}：バルコニー奥行（m）", 0.0, 5.0, 1.5, step=0.1, key=f"depth_{i}")
            sunwind = st.selectbox(f"{names[i]}：採光・通風", ["良い","普通","悪い"], key=f"sunwind_{i}")
            flow = st.selectbox(f"{names[i]}：廊下幅・家事動線", ["良い","普通","悪い"], key=f"flow_{i}")
        size_inputs.append((area, liv, layout, storage, ceil, aspect, depth, sunwind, flow))

    # --- ④ スペック（専有部分）
    st.markdown("### ④ スペック（専有部分）")
    spec_inputs = []
    for i in range(rows):
        k1,k2,k3,k4,k5 = st.columns(5)
        with k1:
            dw = st.checkbox(f"{names[i]}：食洗機", key=f"dw_{i}")
            disp = st.checkbox(f"{names[i]}：ディスポーザー", key=f"disp_{i}")
        with k2:
            pur = st.checkbox(f"{names[i]}：浄水器/整水器", key=f"pur_{i}")
            oven = st.checkbox(f"{names[i]}：ビルトインオーブン", key=f"oven_{i}")
        with k3:
            cook = st.checkbox(f"{names[i]}：高機能コンロ（IH/高火力）", key=f"cook_{i}")
            dryer = st.checkbox(f"{names[i]}：浴室乾燥機", key=f"dry_{i}")
        with k4:
            reheat = st.checkbox(f"{names[i]}：追い焚き", key=f"reh_{i}")
            sauna = st.checkbox(f"{names[i]}：ミストサウナ", key=f"sauna_{i}")
        with k5:
            btv = st.checkbox(f"{names[i]}：浴室TV", key=f"btv_{i}")
            bwin = st.checkbox(f"{names[i]}：浴室に窓", key=f"bwin_{i}")

        h1,h2,h3,h4 = st.columns(4)
        with h1: fh = st.checkbox(f"{names[i]}：床暖房", key=f"fh_{i}")
        with h2: ac = st.checkbox(f"{names[i]}：エアコン（備付）", key=f"ac_{i}")
        with h3: lowe = st.checkbox(f"{names[i]}：Low-E", key=f"lowe_{i}")
        with h4: twin = st.checkbox(f"{names[i]}：二重サッシ", key=f"twin_{i}")
        w1,w2 = st.columns(2)
        with w1: multi = st.checkbox(f"{names[i]}：複層ガラス", key=f"multi_{i}")
        with w2: doors = st.checkbox(f"{names[i]}：建具ハイグレード（鏡面等）", key=f"doors_{i}")

        s1,s2,s3,s4,s5 = st.columns(5)
        with s1: allst = st.checkbox(f"{names[i]}：全居室収納", key=f"allst_{i}")
        with s2: wic = st.checkbox(f"{names[i]}：WIC", key=f"wic_{i}")
        with s3: sic = st.checkbox(f"{names[i]}：SIC", key=f"sic_{i}")
        with s4: pantry = st.checkbox(f"{names[i]}：パントリー", key=f"pantry_{i}")
        with s5: linen = st.checkbox(f"{names[i]}：リネン庫", key=f"linen_{i}")

        sec1,sec2,sec3 = st.columns(3)
        with sec1: video = st.checkbox(f"{names[i]}：TVモニターインターホン", key=f"video_{i}")
        with sec2: sensor = st.checkbox(f"{names[i]}：玄関センサー", key=f"sensor_{i}")
        with sec3: ftth = st.checkbox(f"{names[i]}：光配線（各戸）", key=f"ftth_{i}")

        spec_inputs.append({
            "dw":dw, "disp":disp, "pur":pur, "oven":oven, "cook":cook,
            "dry":dryer, "reh":reheat, "sauna":sauna, "btv":btv, "bwin":bwin,
            "fh":fh, "ac":ac, "lowe":lowe, "twin":twin, "multi":multi, "doors":doors,
            "allst":allst, "wic":wic, "sic":sic, "pantry":pantry, "linen":linen,
            "video":video, "sensor":sensor, "ftth":ftth
        })

    # --- ⑤ 管理・共有部・その他
    st.markdown("### ⑤ 管理・共有部・その他")
    mgmt_inputs = []
    for i in range(rows):
        c1,c2,c3,c4 = st.columns(4)
        with c1:
            concierge = st.checkbox(f"{names[i]}：コンシェルジュ", key=f"con_{i}")
            box = st.checkbox(f"{names[i]}：宅配ボックス", key=f"box_{i}")
        with c2:
            guest = st.checkbox(f"{names[i]}：ゲストルーム", key=f"guest_{i}")
            lounge = st.checkbox(f"{names[i]}：ラウンジ/キッズ", key=f"lounge_{i}")
        with c3:
            gym = st.checkbox(f"{names[i]}：ジム", key=f"gym_{i}")
            pool = st.checkbox(f"{names[i]}：プール", key=f"pool_{i}")
        with c4:
            parking = st.selectbox(f"{names[i]}：駐車場形態", ["平置き","機械式","なし"], key=f"park_{i}")

        line2 = st.columns(4)
        with line2[0]: gomi = st.checkbox(f"{names[i]}：24hゴミ出し", key=f"gomi_{i}")
        with line2[1]: seismic = st.checkbox(f"{names[i]}：免震・制震", key=f"sei_{i}")
        with line2[2]: sec = st.checkbox(f"{names[i]}：セキュリティ強", key=f"sec_{i}")
        with line2[3]: design = st.selectbox(f"{names[i]}：外観・エントランス", ["良い","普通","弱い"], key=f"design_{i}")

        line3 = st.columns(4)
        with line3[0]: ev = st.number_input(f"{names[i]}：EV台数（基数）", 0, 20, 2, key=f"ev_{i}")
        with line3[1]: brand = st.checkbox(f"{names[i]}：ブランド/タワー属性", key=f"brand_{i}")
        with line3[2]: pet = st.checkbox(f"{names[i]}：ペット可", key=f"pet_{i}")
        with line3[3]: note = st.text_input(f"{names[i]}：備考", key=f"note_{i}")
        mgmt_inputs.append({
            "concierge":concierge,"box":box,"guest":guest,"lounge":lounge,
            "gym":gym,"pool":pool,"parking":parking,"gomi":gomi,"seismic":seismic,
            "sec":sec,"design":design,"ev":ev,"brand":brand,"pet":pet,"note":note
        })

    st.divider()

    # =========================
    # 計算（相対偏差値）
    # =========================
    if st.button("スコア計算・偏差値表示"):
        for i in range(rows):
            # ①価格
            s_price = (price_score(price_val[i]) + tsubo_score(tsubo_val[i]) + fee_score(fee_val[i]))/3
            # ②立地
            walk, lines, acc, shop, edu, med, secu, haz, park, noise = loc_inputs[i]
            s_loc = (
                (5.0 if walk<=5 else 4.0 if walk<=10 else 3.0 if walk<=15 else 2.5) +
                (5.0 if lines>=3 else 4.0 if lines==2 else 3.0 if lines==1 else 2.5) +
                (5.0 if acc<=20 else 4.0 if acc<=35 else 3.0 if acc<=50 else 2.5) +
                map3(shop,"充実","普通","乏しい") + map3(edu,"良い","普通","弱い") + map3(med,"近い","普通","遠い") +
                map3(secu,"良い","普通","悪い") + map3(haz,"低い","中","高") +
                map3(park,"充実","普通","乏しい") + map3(noise,"静か","普通","うるさい")
            )/10
            # ③広さ
            area, liv, layout, storage, ceil, aspect, depth, sunwind, flow = size_inputs[i]
            lay = 3.5 if layout in ["ワイドスパン","センターイン"] else 3.0
            s_size = (
                size_score(area, liv) + lay + map3(storage,"多い","普通","少ない") +
                map3(ceil,"高い","普通","低い") + 3.0 +
                (4.0 if depth>=1.5 else 3.0) + map3(sunwind,"良い","普通","悪い") + map3(flow,"良い","普通","悪い")
            )/8
            # ④スペック（専有）
            sp = spec_inputs[i]
            keys = ["dw","disp","pur","oven","cook","dry","reh","sauna","btv","bwin","fh","ac","lowe","twin","multi","doors","allst","wic","sic","pantry","linen","video","sensor","ftth"]
            s_spec = sum(bool_score(sp[k]) for k in keys)/len(keys)
            # ⑤管理・その他
            s_mgmt = mgmt_score(mgmt_inputs[i])

            # 重み付き平均
            wsum = w_price + w_location + w_size + w_spec + w_mgmt
            avg = (s_price*w_price + s_loc*w_location + s_size*w_size + s_spec*w_spec + s_mgmt*w_mgmt) / max(wsum,1)

            hensachi = hensachi_relative(avg, baseline_avg)

            c1,c2,c3,c4,c5,c6 = st.columns(6)
            with c1: st.metric(f"{names[i]}｜価格", f"{s_price:.1f}/5")
            with c2: st.metric(f"{names[i]}｜立地", f"{s_loc:.1f}/5")
            with c3: st.metric(f"{names[i]}｜広さ", f"{s_size:.1f}/5")
            with c4: st.metric(f"{names[i]}｜専有スペック", f"{s_spec:.1f}/5")
            with c5: st.metric(f"{names[i]}｜管理その他", f"{s_mgmt:.1f}/5")
            with c6: st.metric(f"{names[i]}｜総合偏差値", f"{hensachi}")

    st.caption("※ 現住居を“50”に据えた相対偏差値。係数・閾値は運用でチューニング可能。")


# 直接実行時の保険（開発用）
if __name__ == "__main__":
    st.write("このファイルは共通ロジックです。お客様専用ランチャーから呼び出してください。")