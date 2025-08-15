# -*- coding: utf-8 -*-
import streamlit as st
import json
from pathlib import Path

st.set_page_config(page_title="物件比較（偏差値）", layout="wide")

DATA_DIR = Path("data/clients")

def load_client(cid: str):
    f = DATA_DIR / f"{cid}.json"
    if not f.exists(): return None
    return json.loads(f.read_text(encoding="utf-8"))

def to_hensachi(avg_1to5: float) -> float:
    # 3.0 -> 50 を基準（現住まい=50の位置付け）。ロジックは暫定で線形。
    return round(50 + (avg_1to5 - 3.0) * 10, 1)

# -------- スコア関数（簡易） --------
def map3(x, good="良い", mid="普通", bad="悪い"):
    if x in ["充実","近い","静か","低い"] or x == good: return 5.0
    if x == mid: return 3.0
    return 2.5

def bool_score(b): return 5.0 if b else 2.5

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
    for k in ["concierge","box","guest","lounge","gym","pool","gomi","seismic","sec","brand","tower","pet"]:
        if k in m:
            n += 1
            pts += 1 if m[k] else 0
    if n == 0: return 3.0
    ratio = pts / n
    return 2.5 + ratio * 2.5  # 2.5〜5.0

# ========= レンダラー =========
def render_compare(client_id: str):
    payload = load_client(client_id)
    if not payload:
        st.error("このお客様IDのデータが見つかりません。"); st.stop()

    name = payload.get("meta",{}).get("name","")
    st.title("物件比較（偏差値）")
    st.caption(f"対象お客様：{name}（ID: {client_id}）")
    st.info("基準は“現住まい = 偏差値50”。重みはヒアリングのトレードオフを使用。")

    # 重み
    pri = payload.get("hearing", {})
    w_price     = int(pri.get("prio_price", 3))
    w_location  = int(pri.get("prio_location", 3))
    w_size      = int(pri.get("prio_size_layout", 3))
    w_spec      = int(pri.get("prio_spec", 3))
    w_mgmt      = int(pri.get("prio_mgmt", 3))
    st.caption(f"重み ▶ 価格:{w_price} / 立地:{w_location} / 広さ・間取り:{w_size} / スペック:{w_spec} / 管理:{w_mgmt}")

    # 入力列数
    if "compare_rows" not in st.session_state: st.session_state["compare_rows"] = 3
    rows = st.session_state["compare_rows"]

    st.subheader("横並び入力（A・B・C…）")
    cols = st.columns(rows); names=[]
    for i in range(rows):
        with cols[i]:
            names.append(st.text_input(f"物件名 {chr(65+i)}", value=f"物件{chr(65+i)}", key=f"name_{i}"))

    st.divider()

    # ① 価格
    st.markdown("### ① 価格")
    price_val=[]; tsubo_val=[]; fee_val=[]; renov_val=[]
    cols = st.columns(rows)
    for i in range(rows):
        with cols[i]:
            price_val.append(st.number_input(f"{names[i]}：売出価格（万円）", 0, 50000, 0, key=f"price_{i}"))
            tsubo_val.append(st.number_input(f"{names[i]}：坪単価（万円/坪）", 0, 2000, 0, key=f"tsubo_{i}"))
            fee_val.append(st.number_input(f"{names[i]}：管理費等（月額・円）", 0, 200000, 0, key=f"fee_{i}"))
            renov_val.append(st.number_input(f"{names[i]}：追加リフォーム費（万円）", 0, 5000, 0, key=f"renov_{i}"))

    # ② 立地
    st.markdown("### ② 立地（資産性）")
    loc_inputs=[]
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
            noise = st.selectbox(f"{names[i]}：騒音", ["静か","普通","うるさい"], key=f"noise_{i}")
        loc_inputs.append((walk,lines,acc,shop,edu,med,sec,haz,park,noise))

    # ③ 広さ・間取り
    st.markdown("### ③ 広さ・間取り")
    size_inputs=[]
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

    # ④ スペック（専有）
    st.markdown("### ④ スペック（専有）")
    spec_inputs=[]
    for i in range(rows):
        k1,k2,k3,k4,k5 = st.columns(5)
        with k1:
            dw  = st.checkbox(f"{names[i]}：食洗機", key=f"dw_{i}")
            disp= st.checkbox(f"{names[i]}：ディスポーザー", key=f"disp_{i}")
        with k2:
            pur = st.checkbox(f"{names[i]}：浄水器/整水器", key=f"pur_{i}")
            oven= st.checkbox(f"{names[i]}：ビルトインオーブン", key=f"oven_{i}")
        with k3:
            cook= st.checkbox(f"{names[i]}：高機能コンロ", key=f"cook_{i}")
            dryer=st.checkbox(f"{names[i]}：浴室乾燥機", key=f"dry_{i}")
        with k4:
            reheat = st.checkbox(f"{names[i]}：追い焚き", key=f"reh_{i}")
            sauna  = st.checkbox(f"{names[i]}：ミストサウナ", key=f"sauna_{i}")
        with k5:
            btv   = st.checkbox(f"{names[i]}：浴室TV", key=f"btv_{i}")
            bwin  = st.checkbox(f"{names[i]}：浴室に窓", key=f"bwin_{i}")

        h1,h2,h3,h4 = st.columns(4)
        with h1: fh = st.checkbox(f"{names[i]}：床暖房", key=f"fh_{i}")
        with h2: ac = st.checkbox(f"{names[i]}：エアコン（備付）", key=f"ac_{i}")
        with h3: lowe = st.checkbox(f"{names[i]}：Low-E", key=f"lowe_{i}")
        with h4: twin = st.checkbox(f"{names[i]}：二重サッシ", key=f"twin_{i}")
        w1,w2 = st.columns(2)
        with w1: multi = st.checkbox(f"{names[i]}：複層ガラス", key=f"multi_{i}")
        with w2: doors = st.checkbox(f"{names[i]}：建具ハイグレード", key=f"doors_{i}")

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

    # ⑤ 管理・共有部・その他
    st.markdown("### ⑤ 管理・共有部・その他")
    mgmt_inputs=[]
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

        line2 = st.columns(5)
        with line2[0]: gomi = st.checkbox(f"{names[i]}：24hゴミ出し", key=f"gomi_{i}")
        with line2[1]: seismic = st.checkbox(f"{names[i]}：免震・制震", key=f"sei_{i}")
        with line2[2]: sec = st.checkbox(f"{names[i]}：セキュリティ強", key=f"sec_{i}")
        with line2[3]: design = st.selectbox(f"{names[i]}：外観・エントランス", ["良い","普通","弱い"], key=f"design_{i}")
        with line2[4]: age = st.number_input(f"{names[i]}：築年数（年）", 0, 100, 20, key=f"age_{i}")

        line3 = st.columns(4)
        with line3[0]: ev = st.number_input(f"{names[i]}：EV台数（基数）", 0, 20, 2, key=f"ev_{i}")
        with line3[1]: brand = st.checkbox(f"{names[i]}：ブランド", key=f"brand_{i}")
        with line3[2]: tower = st.checkbox(f"{names[i]}：タワー", key=f"tower_{i}")
        with line3[3]: pet = st.checkbox(f"{names[i]}：ペット可", key=f"pet_{i}")
        mgmt_inputs.append({
            "concierge":concierge,"box":box,"guest":guest,"lounge":lounge,
            "gym":gym,"pool":pool,"parking":parking,"gomi":gomi,"seismic":seismic,
            "sec":sec,"design":design,"age":age,"ev":ev,"brand":brand,"tower":tower,"pet":pet
        })

    st.divider()

    # 結果
    if st.button("スコア計算・偏差値表示"):
        st.subheader("結果（カテゴリー別 / 総合）")
        for i in range(rows):
            # ①価格
            s_price = (price_score(price_val[i]) + tsubo_score(tsubo_val[i]) + fee_score(fee_val[i]))/3
            # ②立地
            walk, lines, acc, shop, edu, med, secu, haz, park, noise = loc_inputs[i]
            s_loc = ( (5.0 if walk<=5 else 4.0 if walk<=10 else 3.0 if walk<=15 else 2.5) +
                      (5.0 if lines>=3 else 4.0 if lines==2 else 3.0 if lines==1 else 2.5) +
                      (5.0 if acc<=20 else 4.0 if acc<=35 else 3.0 if acc<=50 else 2.5) +
                      map3(shop,"充実","普通","乏しい") + map3(edu,"良い","普通","弱い") + map3(med,"近い","普通","遠い") +
                      map3(secu,"良い","普通","悪い") + map3(haz,"低い","中","高") + map3(park,"充実","普通","乏しい") +
                      map3(noise,"静か","普通","うるさい")
                    ) / 10
            # ③広さ・間取り
            area, liv, layout, storage, ceil, aspect, depth, sunwind, flow = size_inputs[i]
            lay = 3.5 if layout in ["ワイドスパン","センターイン"] else 3.0
            s_size = ( size_score(area, liv) + lay + map3(storage,"多い","普通","少ない")
                       + map3(ceil,"高い","普通","低い") + 3.0
                       + (4.0 if depth>=1.5 else 3.0) + map3(sunwind,"良い","普通","悪い") + map3(flow,"良い","普通","悪い")
                     ) / 8
            # ④スペック（専有）
            sp = spec_inputs[i]
            keys = ["dw","disp","pur","oven","cook","dry","reh","sauna","btv","bwin","fh","ac","lowe","twin","multi","doors",
                    "allst","wic","sic","pantry","linen","video","sensor","ftth"]
            s_spec = sum(bool_score(sp[k]) for k in keys)/len(keys)
            # ⑤管理・その他
            s_mgmt = mgmt_score(mgmt_inputs[i])

            # 重み付き平均（1〜5）→ 偏差値（現住まい=50）
            wsum = w_price + w_location + w_size + w_spec + w_mgmt
            avg = (s_price*w_price + s_loc*w_location + s_size*w_size + s_spec*w_spec + s_mgmt*w_mgmt) / wsum
            hensachi = to_hensachi(avg)

            c1,c2,c3,c4,c5,c6 = st.columns(6)
            with c1: st.metric(f"{names[i]}｜価格", f"{s_price:.1f}/5")
            with c2: st.metric(f"{names[i]}｜立地", f"{s_loc:.1f}/5")
            with c3: st.metric(f"{names[i]}｜広さ・間取り", f"{s_size:.1f}/5")
            with c4: st.metric(f"{names[i]}｜スペック", f"{s_spec:.1f}/5")
            with c5: st.metric(f"{names[i]}｜管理その他", f"{s_mgmt:.1f}/5")
            with c6: st.metric(f"{names[i]}｜総合偏差値", f"{hensachi}")

    st.divider()
    st.caption("※ ロジックは暫定。現場運用に合わせてしきい値・重みは調整してください。")

# 直開き防止
if __name__ == "__main__":
    st.error("このファイルは共通ロジックです。お客様専用ランチャーから呼び出してください。")