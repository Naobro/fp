# -*- coding: utf-8 -*-
import streamlit as st
import json
from pathlib import Path

st.set_page_config(page_title="物件比較（偏差値：現住まい=50）", layout="wide")

DATA_DIR = Path("data/clients")

def load_client(cid: str):
    f = DATA_DIR / f"{cid}.json"
    if not f.exists():
        return None
    return json.loads(f.read_text(encoding="utf-8"))

def to_hensachi(avg_1to5: float) -> float:
    return round(50 + (avg_1to5 - 3.0) * 10, 1)

# =============== URL =================
client_id = None
try:
    client_id = st.query_params.get("client", None)
except Exception:
    client_id = st.experimental_get_query_params().get("client", [None])
    client_id = client_id[0] if isinstance(client_id, list) else client_id

if not client_id:
    st.warning("このページは専用URLからアクセスしてください。（末尾に ?client=お客様ID）")
    st.stop()

payload = load_client(client_id)
if not payload:
    st.error("このお客様IDのデータが見つかりません。")
    st.stop()

name = payload.get("meta",{}).get("name","")
b = payload.get("baseline", {})  # ← 現住まい（基準）
pri = payload.get("hearing", {})
w_price     = int(pri.get("prio_price", 3))
w_location  = int(pri.get("prio_location", 3))
w_size      = int(pri.get("prio_size_layout", 3))
w_spec      = int(pri.get("prio_spec", 3))
w_mgmt      = int(pri.get("prio_mgmt", 3))

st.title("物件比較（基準＝現住まい 偏差値50）")
st.caption(f"対象：{name}（ID: {client_id}） / 重み：価格{w_price}・立地{w_location}・広さ{w_size}・スペック{w_spec}・管理{w_mgmt}")

# =============== スコア関数（基準 b に対する相対） =================
def s_walk(m):  # 少ないほど良
    if m is None: return 3.0
    if m <= 5: return 5.0
    if m <=10: return 4.0
    if m <=15: return 3.0
    if m <=20: return 2.5
    return 2.0

def s_comm(m):  # 少ないほど良
    if m is None: return 3.0
    if m <=20: return 5.0
    if m <=35: return 4.0
    if m <=50: return 3.0
    if m <=65: return 2.5
    return 2.0

def score_location_rel(walk_min, h_commute, w_commute, shop, edu, med, secu, haz, park, noise):
    base = []
    base.append(s_walk(walk_min))
    base.append(s_comm(h_commute))
    base.append(s_comm(w_commute))

    def map3(x, good, mid, bad):
        if x == good: return 5.0
        if x == mid:  return 3.0
        return 2.0

    base += [
        map3(shop,"充実","普通","乏しい"),
        map3(edu,"良い","普通","弱い"),
        map3(med,"近い","普通","遠い"),
        map3(secu,"良い","普通","悪い"),
        map3(haz,"低い","中","高"),
        map3(park,"充実","普通","乏しい"),
        map3(noise,"静か","普通","うるさい"),
    ]
    return sum(base)/len(base)

def score_size_layout_rel(area_m2, floor, corner):
    pts = []
    # 面積（基準比）
    ba = b.get("area_m2")
    if area_m2 and ba:
        ratio = area_m2/ba
        if ratio >= 1.30: pts.append(5.0)
        elif ratio >= 1.15: pts.append(4.0)
        elif ratio >= 1.00: pts.append(3.5)
        elif ratio >= 0.90: pts.append(3.0)
        else: pts.append(2.5)
    else:
        pts.append(3.0)
    # 階（基準比）
    bf = b.get("floor")
    if floor is not None and bf is not None:
        df = floor - bf
        if df >= +6: pts.append(4.5)
        elif df >= +3: pts.append(4.0)
        elif df >= 0: pts.append(3.5)
        elif df >= -2: pts.append(3.0)
        else: pts.append(2.5)
    else:
        pts.append(3.0)
    # 角部屋（基準比）
    bc = b.get("corner", None)
    if corner is None or bc is None:
        pts.append(3.0)
    else:
        if corner and not bc: pts.append(4.0)
        elif corner == bc:   pts.append(3.5)
        else:                pts.append(3.0)
    return sum(pts)/len(pts)

MAP_WISH = {"must":2.0, "want":1.0, "neutral":0.0, "no_need":0.0}
def score_spec_match(spec_wish: dict, spec_has: dict) -> float:
    if not spec_wish: return 3.0
    total_w = 0.0; got = 0.0
    for k, wish in spec_wish.items():
        w = MAP_WISH.get(wish, 0.0)
        total_w += w
        if w == 0.0: continue
        if bool(spec_has.get(k)): got += w
    if total_w == 0.0: return 3.0
    r = got/total_w
    if   r >= 0.85: return 5.0
    elif r >= 0.65: return 4.0
    elif r >= 0.45: return 3.5
    elif r >= 0.25: return 3.0
    else: return 2.5

def mgmt_score(m):  # 管理・共用（簡易）
    pts = 0; n = 0
    for k in ["concierge","box","guest","lounge","gym","pool","gomi","seismic","sec","brand","pet"]:
        if k in m:
            n += 1
            pts += 1 if m[k] else 0
    if n == 0: return 3.0
    return 2.5 + (pts/n) * 2.5

# =============== UI：横並び A/B/C =================
st.subheader("物件入力（A/B/C）")
if "compare_rows" not in st.session_state:
    st.session_state["compare_rows"] = 3
rows = st.session_state["compare_rows"]

cols = st.columns(rows)
names = []
for i in range(rows):
    with cols[i]:
        names.append(st.text_input(f"物件名 {chr(65+i)}", value=f"物件{chr(65+i)}"))

st.divider()

# ①価格
st.markdown("### ① 価格")
c_price = st.columns(rows)
price_val = []; tsubo_val = []; fee_val = []; renov_val = []
for i in range(rows):
    with c_price[i]:
        price_val.append(st.number_input(f"{names[i]}：売出価格（万円）", 0, 50000, 0, key=f"price_{i}"))
        tsubo_val.append(st.number_input(f"{names[i]}：坪単価（万円/坪）", 0, 2000, 0, key=f"tsubo_{i}"))
        fee_val.append(st.number_input(f"{names[i]}：管理費等（月額・円）", 0, 200000, 0, key=f"fee_{i}"))
        renov_val.append(st.number_input(f"{names[i]}：追加リフォーム費用（万円）", 0, 5000, 0, key=f"renov_{i}"))

# ②立地
st.markdown("### ② 立地（資産性）")
loc_inputs = []
for i in range(rows):
    c1,c2,c3 = st.columns(3)
    with c1:
        walk = st.number_input(f"{names[i]}：最寄徒歩（分）", 0, 60, int(b.get("walk_min",10)), key=f"walk_{i}")
        lines = st.number_input(f"{names[i]}：複線数（本）", 0, 10, 1, key=f"lines_{i}")
        acc_h = st.number_input(f"{names[i]}：通勤（主）分", 0, 180, int(b.get("husband_commute_min",30)), key=f"acch_{i}")
    with c2:
        acc_w = st.number_input(f"{names[i]}：通勤（副）分", 0, 180, int(b.get("wife_commute_min",40)), key=f"accw_{i}")
        shop = st.selectbox(f"{names[i]}：商業施設", ["充実","普通","乏しい"], key=f"shop_{i}")
        edu  = st.selectbox(f"{names[i]}：教育", ["良い","普通","弱い"], key=f"edu_{i}")
    with c3:
        med  = st.selectbox(f"{names[i]}：医療", ["近い","普通","遠い"], key=f"med_{i}")
        sec  = st.selectbox(f"{names[i]}：治安", ["良い","普通","悪い"], key=f"sec_{i}")
        haz  = st.selectbox(f"{names[i]}：災害", ["低い","中","高"], key=f"haz_{i}")
        park = st.selectbox(f"{names[i]}：公園・緑地", ["充実","普通","乏しい"], key=f"park_{i}")
        noise= st.selectbox(f"{names[i]}：騒音", ["静か","普通","うるさい"], key=f"noise_{i}")
    loc_inputs.append((walk,acc_h,acc_w,shop,edu,med,sec,haz,park,noise,lines))

# ③広さ・間取り（相対）
st.markdown("### ③ 広さ・間取り（基準比）")
size_inputs = []
for i in range(rows):
    c1,c2 = st.columns(2)
    with c1:
        area = st.number_input(f"{names[i]}：専有面積（㎡）", 0, 300, int(b.get("area_m2",60)), key=f"area_{i}")
        floor = st.number_input(f"{names[i]}：所在階", 0, 70, int(b.get("floor",3)), key=f"floor_{i}")
    with c2:
        corner = st.selectbox(f"{names[i]}：角部屋", ["不明","いいえ","はい"], key=f"corner_{i}")
    size_inputs.append((area, floor, True if corner=="はい" else (False if corner=="いいえ" else None)))

# ④スペック（専有）一致率
st.markdown("### ④ スペック（専有）")
spec_inputs = []
for i in range(rows):
    k1,k2,k3,k4,k5 = st.columns(5)
    with k1:
        dw   = st.checkbox(f"{names[i]}：食洗機", key=f"dw_{i}")
        disp = st.checkbox(f"{names[i]}：ディスポーザー", key=f"disp_{i}")
    with k2:
        pur  = st.checkbox(f"{names[i]}：浄水器/整水器", key=f"pur_{i}")
        oven = st.checkbox(f"{names[i]}：ビルトインオーブン", key=f"ov_{i}")
    with k3:
        cook = st.checkbox(f"{names[i]}：高機能コンロ", key=f"cook_{i}")
        dry  = st.checkbox(f"{names[i]}：浴室乾燥機", key=f"dry_{i}")
    with k4:
        reh  = st.checkbox(f"{names[i]}：追い焚き", key=f"reh_{i}")
        sauna= st.checkbox(f"{names[i]}：ミストサウナ", key=f"sauna_{i}")
    with k5:
        btv  = st.checkbox(f"{names[i]}：浴室TV", key=f"btv_{i}")
        bwin = st.checkbox(f"{names[i]}：浴室に窓", key=f"bwin_{i}")
    h1,h2,h3,h4 = st.columns(4)
    with h1: fh   = st.checkbox(f"{names[i]}：床暖房", key=f"fh_{i}")
    with h2: ac   = st.checkbox(f"{names[i]}：エアコン（備付）", key=f"ac_{i}")
    with h3: lowe = st.checkbox(f"{names[i]}：Low-E", key=f"lowe_{i}")
    with h4: twin = st.checkbox(f"{names[i]}：二重サッシ", key=f"twin_{i}")
    w1,w2 = st.columns(2)
    with w1: multi = st.checkbox(f"{names[i]}：複層ガラス", key=f"multi_{i}")
    with w2: doors = st.checkbox(f"{names[i]}：建具ハイグレード", key=f"doors_{i}")
    s1,s2,s3,s4,s5 = st.columns(5)
    with s1: allst = st.checkbox(f"{names[i]}：全居室収納", key=f"allst_{i}")
    with s2: wic   = st.checkbox(f"{names[i]}：WIC", key=f"wic_{i}")
    with s3: sic   = st.checkbox(f"{names[i]}：SIC", key=f"sic_{i}")
    with s4: pantry= st.checkbox(f"{names[i]}：パントリー", key=f"pantry_{i}")
    with s5: linen = st.checkbox(f"{names[i]}：リネン庫", key=f"linen_{i}")
    sec1,sec2,sec3 = st.columns(3)
    with sec1: video = st.checkbox(f"{names[i]}：TVモニタホン", key=f"video_{i}")
    with sec2: sensor= st.checkbox(f"{names[i]}：玄関センサー", key=f"sensor_{i}")
    with sec3: ftth  = st.checkbox(f"{names[i]}：光配線（各戸）", key=f"ftth_{i}")

    spec_inputs.append({
        "k_dishwasher":dw, "k_disposer":disp, "k_purifier":pur, "k_bi_oven":oven, "k_highend_cooktop":cook,
        "b_dryer":dry, "b_reheating":reh, "b_mist_sauna":sauna, "b_tv":btv, "b_window":bwin,
        "h_floorheat":fh, "h_aircon_built":ac,
        "w_low_e":lowe, "w_double_sash":twin, "w_multi":multi, "w_premium_doors":doors,
        "s_allrooms":allst, "s_wic":wic, "s_sic":sic, "s_pantry":pantry, "s_linen":linen,
        "sec_tvphone":video, "sec_sensor":sensor, "net_ftth":ftth,
    })

# ⑤管理・共有部・その他
st.markdown("### ⑤ 管理・共有部・その他")
mgmt_inputs = []
for i in range(rows):
    c1,c2,c3 = st.columns(3)
    with c1:
        concierge = st.checkbox(f"{names[i]}：コンシェルジュ", key=f"con_{i}")
        box = st.checkbox(f"{names[i]}：宅配ボックス", key=f"box_{i}")
        guest = st.checkbox(f"{names[i]}：ゲストルーム", key=f"guest_{i}")
        lounge = st.checkbox(f"{names[i]}：ラウンジ/キッズ", key=f"lounge_{i}")
    with c2:
        gym = st.checkbox(f"{names[i]}：ジム", key=f"gym_{i}")
        pool = st.checkbox(f"{names[i]}：プール", key=f"pool_{i}")
        gomi = st.checkbox(f"{names[i]}：24hゴミ出し", key=f"gomi_{i}")
        seismic = st.checkbox(f"{names[i]}：免震/制震", key=f"sei_{i}")
    with c3:
        sec  = st.checkbox(f"{names[i]}：セキュリティ強", key=f"sec_{i}")
        design = st.selectbox(f"{names[i]}：外観/エントランス", ["良い","普通","弱い"], key=f"design_{i}")
        brand = st.checkbox(f"{names[i]}：ブランド/タワー", key=f"brand_{i}")
        pet = st.checkbox(f"{names[i]}：ペット可", key=f"pet_{i}")
    mgmt_inputs.append({"concierge":concierge,"box":box,"guest":guest,"lounge":lounge,"gym":gym,"pool":pool,
                        "gomi":gomi,"seismic":seismic,"sec":sec,"design":design,"brand":brand,"pet":pet})

st.divider()

wish = payload.get("wish", {})

if st.button("スコア計算・偏差値表示"):
    st.subheader("結果（カテゴリー別 / 総合）")
    for i in range(rows):
        # 価格（暫定：安いほど高得点、坪単価/管理費/リフォーム費も平均化）
        def price_score(price_m, tsubo_m, fee_yen, renov_m):
            s = 0; n = 0
            if price_m is not None:
                if price_m <= 5000: s+=4.0
                elif price_m <= 8000: s+=3.5
                elif price_m <= 10000: s+=3.0
                else: s+=2.5; n+=1
            else: n+=1
            if tsubo_m is not None:
                if tsubo_m <= 300: s+=4.0
                elif tsubo_m <= 400: s+=3.5
                elif tsubo_m <= 500: s+=3.0
                else: s+=2.5; n+=1
            else: n+=1
            if fee_yen is not None:
                if fee_yen <= 15000: s+=4.0
                elif fee_yen <= 25000: s+=3.5
                elif fee_yen <= 35000: s+=3.0
                else: s+=2.5; n+=1
            else: n+=1
            if renov_m is not None:
                if renov_m == 0: s+=3.5
                elif renov_m <= 200: s+=3.2
                else: s+=2.8
            else: n+=1
            return max(2.5, min(5.0, s/4))
        s_price = price_score(price_val[i], tsubo_val[i], fee_val[i], renov_val[i])

        # 立地（相対＋定性）
        walk, acch, accw, shop, edu, med, sec, haz, park, noise, lines = loc_inputs[i]
        s_loc = score_location_rel(walk, acch, accw, shop, edu, med, sec, haz, park, noise)

        # 広さ・間取り（相対）
        area, floor, corner = size_inputs[i]
        s_size = score_size_layout_rel(area, floor, corner)

        # スペック一致率（◎○△×）
        s_spec = score_spec_match(wish, spec_inputs[i])

        # 管理・その他（簡易）
        s_mgmt = mgmt_score(mgmt_inputs[i])

        # 重み付き平均 → 偏差値
        wsum = w_price + w_location + w_size + w_spec + w_mgmt
        avg = (s_price*w_price + s_loc*w_location + s_size*w_size + s_spec*w_spec + s_mgmt*w_mgmt) / wsum
        hensachi = to_hensachi(avg)

        c1,c2,c3,c4,c5,c6 = st.columns(6)
        with c1: st.metric(f"{names[i]}｜価格", f"{s_price:.1f}/5")
        with c2: st.metric(f"{names[i]}｜立地", f"{s_loc:.1f}/5")
        with c3: st.metric(f"{names[i]}｜広さ", f"{s_size:.1f}/5")
        with c4: st.metric(f"{names[i]}｜専有スペック", f"{s_spec:.1f}/5")
        with c5: st.metric(f"{names[i]}｜管理その他", f"{s_mgmt:.1f}/5")
        with c6: st.metric(f"{names[i]}｜総合偏差値", f"{hensachi}")

st.caption("※ 基準（現住まい）は 2_client_portal.py の『②現状把握』で保存した値を参照します。")