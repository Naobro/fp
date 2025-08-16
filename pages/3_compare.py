# pages/compare.py
import streamlit as st
import json, os, math, datetime
from typing import Dict, List, Any, Tuple

st.set_page_config(page_title="物件比較（5件一括）", layout="wide")

DATA_DIR = "data"
MASTER_JSON = os.path.join(DATA_DIR, "master_options.json")
DRAFT_JSON = os.path.join(DATA_DIR, "properties_draft.json")

# =========================
# 初期データ（master が無ければ自動生成）
# =========================
DEFAULT_MASTER: Dict[str, Any] = {
    "balcony_facings": [
        ["北", "N"], ["北東", "NE"], ["東", "E"], ["南東", "SE"],
        ["南", "S"], ["南西", "SW"], ["西", "W"], ["北西", "NW"]
    ],
    "spec_categories": {
        "キッチン設備": [
            "システムキッチン","食器洗浄乾燥機（食洗機）","浄水器／整水器",
            "ディスポーザー","IHクッキングヒーター","ガスコンロ（3口・グリル付）",
            "オーブンレンジ（ビルトイン）","レンジフード（換気扇）",
            "キッチン収納（スライド・ソフトクローズ）"
        ],
        "バスルーム設備": [
            "浴室暖房乾燥機","追い焚き機能","ミストサウナ機能",
            "浴室テレビ","浴室に窓","半身浴"
        ],
        "洗面・トイレ設備": [
            "三面鏡付き洗面化粧台","シャワー水栓付き洗面台","ウォシュレット",
            "手洗いカウンター（トイレ内）","タンクレストイレ"
        ],
        "暖房・空調設備": ["床暖房（LD/全室/一部）","エアコン"],
        "窓・建具設備": ["複層ガラス（ペアガラス）","Low-Eガラス","二重サッシ","建具：鏡面仕上げ"],
        "収納設備": ["全居室収納","WIC（ウォークイン）","SIC（シューズイン）","パントリー","リネン庫"],
        "セキュリティ・通信設備": [
            "TVモニター付インターホン","センサーライト（玄関）",
            "インターネット光配線方式（各戸まで光）"
        ]
    },
    "mgmt_shared_etc": [
        "コンシェルジュサービス","宅配ボックス","ゲストルーム","ラウンジ","キッズルーム",
        "ジム","プール","ゴミ出し24時間可","免震・制震構造",
        "セキュリティ（オートロック・防犯カメラ・24h有人）",
        "外観・エントランスのデザイン","ブランドマンション","タワーマンション",
        "長期修繕計画・資金計画","修繕積立金 妥当性","管理体制","共有部修繕履歴","収益性（利回り）"
    ],
    "parking_types": ["平置き","機械式","なし/不明"]
}

os.makedirs(DATA_DIR, exist_ok=True)
if not os.path.exists(MASTER_JSON):
    with open(MASTER_JSON, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_MASTER, f, ensure_ascii=False, indent=2)

# =========================
# 読み込み
# =========================
def load_master() -> Dict[str, Any]:
    with open(MASTER_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

def save_draft(d):
    with open(DRAFT_JSON, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

def load_draft():
    if os.path.exists(DRAFT_JSON):
        with open(DRAFT_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

M = load_master()

# =========================
# 共通ユーティリティ
# =========================
def auto_tsubo_price(price_man: float, area_m2: float) -> float:
    # 坪単価（万/坪）= 価格(万円) / ㎡ × 3.30578
    if area_m2 <= 0:
        return 0.0
    return price_man / max(area_m2, 1e-9) * 3.30578

def build_age_text(year_built: int) -> str:
    if year_built <= 0:
        return "築年不明"
    y = datetime.date.today().year
    age = max(0, y - year_built)
    return f"築{age}年"

def norm_more(x, lo, hi):  # 大きい方が良い
    if hi <= lo: return 0.5
    x = min(max(x, lo), hi)
    return (x - lo) / (hi - lo)

def norm_less(x, lo, hi):  # 小さい方が良い
    if hi <= lo: return 0.5
    x = min(max(x, lo), hi)
    return 1.0 - (x - lo) / (hi - lo)

def score_property(p: Dict[str, Any], current_score: float) -> Tuple[float, Dict[str, float]]:
    """
    スコアは 価格/アクセス/面積/収納/採光/天井/廊下/バルコニー奥行/階数/立地総合などを加重平均。
    立地（資産性）は「再開発・特定都市再生緊急整備地域」チェックで 1.5 倍（上限1.0）に補正。
    """
    # 価格系
    s_price = norm_less(p.get("tsubo_price", 350.0), 100, 600)
    # アクセス系
    s_dist  = norm_less(p.get("dist_station", 10), 0, 20)
    s_work  = norm_less(p.get("access_work", 30), 0, 90)
    # 面積
    s_area  = norm_more(p.get("area_m2", 60), 40, 90)
    # 定性
    s_store = {"多い": 1.0, "普通": 0.6, "少ない": 0.2}.get(p.get("storage_level","普通"), 0.6)
    s_sun   = {"良い": 1.0, "普通": 0.6, "悪い": 0.2}.get(p.get("sun_wind","普通"), 0.6)
    s_ceil  = {"高い": 1.0, "普通": 0.6, "低い": 0.2}.get(p.get("ceiling","普通"), 0.6)
    s_hall  = {"良い": 1.0, "普通": 0.6, "悪い": 0.2}.get(p.get("hall_width","普通"), 0.6)
    s_balc  = norm_more(p.get("balcony_depth", 1.2), 1.0, 2.0)
    s_floor = norm_more(p.get("floor", 3), 1, 20)

    # 立地要素（商業・教育・医療・治安・災害・公園・騒音）
    def cat4(v):
        return {"充実":1.0,"良い":0.8,"普通":0.5,"弱い":0.2}.get(v,0.5)

    loc_raw = (
        0.25*s_dist + 0.15*s_work +
        0.10*cat4(p.get("shop","普通")) +
        0.10*cat4(p.get("edu","普通")) +
        0.10*cat4(p.get("medical","普通")) +
        0.10*cat4(p.get("security","普通")) +  # 治安
        0.10*cat4(p.get("disaster","普通")) +  # 災害リスク（良い=低リスク）
        0.05*cat4(p.get("park","普通")) +
        0.05*cat4(p.get("noise","普通"))
    )
    if p.get("redevelopment_bonus", False):
        loc = min(1.0, loc_raw * 1.5)  # 1.5倍、上限1.0
    else:
        loc = loc_raw

    weights = {
        "price":2.0,"dist":1.5,"work":1.5,"area":2.0,"storage":1.0,
        "sun":1.0,"ceil":0.8,"hall":0.6,"balc":0.5,"floor":0.6,"loc":2.0
    }
    parts = {
        "price": s_price, "dist": s_dist, "work": s_work, "area": s_area,
        "storage": s_store, "sun": s_sun, "ceil": s_ceil, "hall": s_hall,
        "balc": s_balc, "floor": s_floor, "loc": loc
    }
    total = sum(weights[k]*parts[k] for k in parts)/sum(weights.values())
    score = total*100.0
    hensachi = 50.0 + 10.0*(score - current_score)/15.0
    return hensachi, {**parts, "_score":score}

# =====================================
# 画面：ヘッダ／現住情報（基準=50）
# =====================================
st.title("🏠 物件比較（5件一括入力＆保存）")

with st.container(border=True):
    st.subheader("基準：現住のスコア（= 偏差値50の基準）")
    c1,c2,c3,c4 = st.columns(4)
    with c1:
        cur_area = st.number_input("現住：専有面積（㎡）", min_value=0.0, value=55.0, step=1.0)
    with c2:
        cur_floor = st.number_input("現住：所在階", min_value=0, value=3, step=1)
    with c3:
        cur_commute = st.number_input("現住：最短通勤（分）", min_value=0, value=45, step=5)
    with c4:
        cur_station = st.number_input("現住：駅徒歩（分）", min_value=0, value=20, step=1)

    # 現住の暫定スコア（0-100）
    cur_score = (
        0.18*norm_more(cur_area,40,90)
        +0.12*norm_more(cur_floor,1,20)
        +0.20*norm_less(cur_commute,0,90)
        +0.20*norm_less(cur_station,0,20)
        +0.30*0.6  # 既定中庸
    )*100.0
    st.info(f"現住スコア（0-100の内部指標）: **{cur_score:.1f}**  → これを偏差値50の基準にします。")

# =====================================
# 物件リスト（5件）
# =====================================
if "props" not in st.session_state:
    # 下書き復元
    draft = load_draft()
    if draft.get("props"):
        st.session_state.props = draft["props"]
    else:
        st.session_state.props = [
            {
                "name": f"物件{i+1}",
                "price_man": 0.0,
                "year_built": 0,
                "area_m2": 0.0,
                "kanri_man": 0.0,
                "shuzen_man": 0.0
            } for i in range(5)
        ]

props: List[Dict[str,Any]] = st.session_state.props

# 上段に「5件の基本情報」テーブル風入力
st.header("① 5物件の基本情報（先にまとめて入力・保存可）")
with st.container(border=True):
    cols = st.columns([1.1,1,1,1,1,1,1])
    headers = ["名称","価格（万円）","西暦（築）","築表示","専有面積（㎡）","管理費（円/月）","修繕積立金（円/月）"]
    for i,h in enumerate(headers):
        cols[i].markdown(f"**{h}**")
    for idx in range(5):
        c0,c1,c2,c3,c4,c5,c6 = st.columns([1.1,1,1,1,1,1,1], gap="small")
        props[idx]["name"] = c0.text_input("名称", value=props[idx].get("name", f"物件{idx+1}"), key=f"name{idx}")
        props[idx]["price_man"] = c1.number_input("価格", min_value=0.0, step=10.0, value=float(props[idx].get("price_man",0)), key=f"p{idx}")
        props[idx]["year_built"] = c2.number_input("築西暦", min_value=0, step=1, value=int(props[idx].get("year_built",0)), key=f"y{idx}")
        c3.write(build_age_text(int(props[idx]["year_built"])) if props[idx]["year_built"] else "—")
        props[idx]["area_m2"] = c4.number_input("面積", min_value=0.0, step=0.5, value=float(props[idx].get("area_m2",0)), key=f"a{idx}")
        props[idx]["kanri_man"] = c5.number_input("管理費", min_value=0.0, step=500.0, value=float(props[idx].get("kanri_man",0)), key=f"k{idx}")
        props[idx]["shuzen_man"] = c6.number_input("修繕", min_value=0.0, step=500.0, value=float(props[idx].get("shuzen_man",0)), key=f"s{idx}")

    b1,b2,b3 = st.columns(3)
    with b1:
        if st.button("💾 下書き保存（/data/properties_draft.json）"):
            save_draft({"props": props})
            st.success("保存しました。")
    with b2:
        if st.button("♻ 下書き読込"):
            st.session_state.props = load_draft().get("props", props)
            st.experimental_rerun()
    with b3:
        if st.button("🗑 下書きクリア"):
            if os.path.exists(DRAFT_JSON): os.remove(DRAFT_JSON)
            st.session_state.props = [
                {"name": f"物件{i+1}","price_man":0.0,"year_built":0,"area_m2":0.0,"kanri_man":0.0,"shuzen_man":0.0}
                for i in range(5)
            ]
            st.experimental_rerun()

st.divider()

# =====================================
# 各物件の詳細入力（タブで5件同時に）
# =====================================
st.header("② 各物件の詳細入力（タブ切替で5件同時）")

tabs = st.tabs([p["name"] for p in props])

def cat4_select(label: str, help_txt: str, key: str, default_index=2):
    return st.selectbox(label, ["充実","良い","普通","弱い"], index=default_index, help=help_txt, key=key)

for i, tab in enumerate(tabs):
    with tab:
        p = props[i]
        st.subheader(f"{p['name']}：詳細")
        with st.container(border=True):
            cA,cB,cC,cD = st.columns(4)
            with cA:
                price_man = st.number_input("売出価格（万円）", min_value=0.0, value=float(p.get("price_man",0)), step=10.0, key=f"dp{i}")
                area_m2 = st.number_input("専有面積（㎡）", min_value=0.0, value=float(p.get("area_m2",0)), step=0.5, key=f"da{i}")
                st.markdown(f"**坪単価（万/坪・自動）**：{auto_tsubo_price(price_man, area_m2):.1f}")
            with cB:
                year_built = st.number_input("築年（西暦）", min_value=0, value=int(p.get("year_built",0)), step=1, key=f"dy{i}")
                st.caption(build_age_text(year_built) if year_built else "—")
                floor = st.number_input("所在階（任意）", min_value=0, value=int(p.get("floor",0)), step=1, key=f"fl{i}")
            with cC:
                kanri = st.number_input("管理費（円/月）", min_value=0.0, value=float(p.get("kanri_man",0)), step=500.0, key=f"dk{i}")
                shuzen = st.number_input("修繕積立金（円/月）", min_value=0.0, value=float(p.get("shuzen_man",0)), step=500.0, key=f"ds{i}")
            with cD:
                facing_j = st.selectbox("バルコニー向き（日本語表記）", [j for j,_ in M["balcony_facings"]],
                                        index=4 if p.get("facing_j") is None else [j for j,_ in M["balcony_facings"]].index(p.get("facing_j","南")),
                                        key=f"fj{i}")
                balcony_depth = st.number_input("バルコニー奥行（m）", min_value=0.0, value=float(p.get("balcony_depth",1.5)), step=0.1, key=f"bd{i}")

            p.update(dict(price_man=price_man, area_m2=area_m2, year_built=year_built,
                          kanri_man=kanri, shuzen_man=shuzen, facing_j=facing_j,
                          balcony_depth=balcony_depth, floor=floor))
            p["tsubo_price"] = auto_tsubo_price(price_man, area_m2)

        st.subheader("立地（資産性）")
        with st.container(border=True):
            # 追加：最寄駅（先頭）
            st.text_input("最寄駅（駅名・路線等）", value=p.get("nearest_station",""), key=f"ns{i}")
            c1,c2,c3,c4 = st.columns(4)
            with c1:
                p["dist_station"] = st.number_input("最寄駅 徒歩（分）", min_value=0, value=int(p.get("dist_station",10)), step=1, key=f"dst{i}")
            with c2:
                p["access_work"] = st.number_input("職場アクセス（分）", min_value=0, value=int(p.get("access_work",30)), step=5, key=f"awk{i}")
            with c3:
                p["line_count"] = st.number_input("複線数（本）", min_value=0, value=int(p.get("line_count",1)), step=1, key=f"lc{i}")
            with c4:
                # 再開発・緊急整備地域 → 資産性1.5倍
                p["redevelopment_bonus"] = st.checkbox("再開発予定・特定都市再生緊急整備地域（資産価値1.5倍）",
                                                      value=bool(p.get("redevelopment_bonus", False)),
                                                      key=f"rd{i}")

            st.markdown("**周辺評価（説明付き）**")
            p["shop"] = cat4_select("商業施設（スーパー・コンビニ・ドラッグストア）",
                                    "生活利便施設の充実度を評価", key=f"shop{i}", default_index=0)
            p["edu"] = cat4_select("教育環境（保育園・幼稚園・小中学校・学区）",
                                   "子育て観点・学区の評価", key=f"edu{i}", default_index=1)
            p["medical"] = cat4_select("医療施設（総合病院やクリニックの近さ）",
                                       "通院利便性や救急時の安心感", key=f"med{i}", default_index=1)
            p["security"] = cat4_select("治安（夜間の人通り・街灯）",
                                        "夜間の安全性・防犯面の安心感", key=f"sec{i}", default_index=2)
            p["disaster"] = cat4_select("災害リスク（洪水・液状化・ハザードマップ）",
                                        "低リスクほど評価が高い", key=f"dis{i}", default_index=2)
            p["park"] = cat4_select("公園・緑地など子育て環境",
                                    "子育てのしやすさ・身近な緑", key=f"park{i}", default_index=2)
            p["noise"] = cat4_select("騒音（線路・幹線道路・繁華街）",
                                     "静穏性。静かなほど高評価", key=f"noi{i}", default_index=2)

        st.subheader("スペック（専有部分）※カテゴリ別に整理")
        with st.container(border=True):
            # 収納・採光・天井・廊下などの総合スコア用項目
            sc1,sc2,sc3 = st.columns(3)
            with sc1:
                p["storage_level"] = st.selectbox("収納量（総合）", ["多い","普通","少ない"],
                                                  index={"多い":0,"普通":1,"少ない":2}.get(p.get("storage_level","多い"),0),
                                                  key=f"stor{i}")
            with sc2:
                p["ceiling"] = st.selectbox("天井高", ["高い","普通","低い"],
                                            index={"高い":0,"普通":1,"低い":2}.get(p.get("ceiling","高い"),0),
                                            key=f"ceil{i}")
            with sc3:
                p["sun_wind"] = st.selectbox("採光・通風", ["良い","普通","悪い"],
                                             index={"良い":0,"普通":1,"悪い":2}.get(p.get("sun_wind","良い"),0),
                                             key=f"sun{i}")
            st.selectbox("廊下幅・家事動線", ["良い","普通","悪い"],
                         index={"良い":0,"普通":1,"悪い":2}.get(p.get("hall_width","良い"),0), key=f"hall{i}")

            # 完全カテゴリ化チェック群
            for cat, items in M["spec_categories"].items():
                with st.expander(f"【{cat}】"):
                    cols = st.columns(3)
                    for idx_item, item in enumerate(items):
                        col = cols[idx_item % 3]
                        key = f"spec_{i}_{cat}_{idx_item}"
                        checked = st.session_state.get(key, False)
                        new_val = col.checkbox(item, value=checked, key=key)
                        # 保存形式：p["spec"][cat] = {item:bool}
                        p.setdefault("spec", {}).setdefault(cat, {})[item] = new_val

        st.subheader("管理・共有部・その他")
        with st.container(border=True):
            cpk, cpt, cpt2 = st.columns([1,1,1])
            with cpk:
                p["parking_type"] = st.selectbox("駐車場形態", M["parking_types"],
                                                 index=M["parking_types"].index(p.get("parking_type","平置き")) if p.get("parking_type") in M["parking_types"] else 0,
                                                 key=f"pt{i}")
            with cpt:
                p["elev_num"] = st.number_input("エレベーター台数（基数）", min_value=0, value=int(p.get("elev_num",1)), step=1, key=f"el{i}")
            with cpt2:
                p["pet_ok"] = st.selectbox("ペット飼育可否", ["可","不可","不明"],
                                           index={"可":0,"不可":1,"不明":2}.get(p.get("pet_ok","不明"),2),
                                           key=f"pet{i}")

            cols = st.columns(3)
            for idx_item, item in enumerate(M["mgmt_shared_etc"]):
                col = cols[idx_item % 3]
                k = f"mg_{i}_{idx_item}"
                chk = st.session_state.get(k, False)
                val = col.checkbox(item, value=chk, key=k)
                p.setdefault("mgmt", {})[item] = val

        # スコア・偏差値
        hensachi, parts = score_property(p, cur_score)
        st.success(f"偏差値：**{hensachi:.1f}**（現住=50 基準）｜内部スコア：{parts['_score']:.1f}")
        with st.expander("スコア内訳（正規化値）"):
            st.json({k: round(v,3) for k,v in parts.items() if k!="_score"})

# =====================================
# 総括テーブル
# =====================================
st.header("③ 比較サマリー")
rows = []
for p in props:
    name = p["name"]
    tsubo = auto_tsubo_price(float(p.get("price_man",0)), float(p.get("area_m2",0)))
    hensachi, parts = score_property(p, cur_score)
    rows.append({
        "物件名": name,
        "価格(万円)": p.get("price_man",0),
        "面積(㎡)": p.get("area_m2",0),
        "坪単価(万/坪)": round(tsubo,1),
        "築": build_age_text(int(p.get("year_built",0))) if p.get("year_built") else "—",
        "駅徒歩(分)": p.get("dist_station", None),
        "通勤(分)": p.get("access_work", None),
        "再開発ボーナス": "有" if p.get("redevelopment_bonus") else "無",
        "内部スコア(0-100)": round(parts["_score"],1),
        "偏差値(現住=50)": round(hensachi,1)
    })

st.dataframe(rows, use_container_width=True)
st.caption("※ 偏差値は内部スコアを現住スコアと比較して換算。再開発チェック時は立地要素が**1.5倍**で評価されます（上限1.0）。")