# pages/2_master_admin.py
# マスター項目（方位・専有スペック・管理共有部・駐車場タイプ）の編集ページ
# ※ 初回アクセス時に data/master_options.json を自動生成します

import streamlit as st
import json, os
from typing import Dict, Any, List

st.set_page_config(page_title="管理：マスター項目 編集", layout="wide")

DATA_DIR = "data"
MASTER_JSON = os.path.join(DATA_DIR, "master_options.json")

# -------------------------------
# 初期データ（ファイルが無ければこれで作る）
# -------------------------------
DEFAULT_MASTER: Dict[str, Any] = {
    "balcony_facings": [
        ["北","N"], ["北東","NE"], ["東","E"], ["南東","SE"],
        ["南","S"], ["南西","SW"], ["西","W"], ["北西","NW"]
    ],
    "spec_categories": {
        "キッチン設備": [
            "システムキッチン",
            "食器洗浄乾燥機（食洗機）",
            "浄水器／整水器",
            "ディスポーザー",
            "IHクッキングヒーター",
            "ガスコンロ（3口・グリル付）",
            "オーブンレンジ（ビルトイン）",
            "レンジフード（換気扇）",
            "キッチン収納（スライド・ソフトクローズ）"
        ],
        "バスルーム設備": [
            "浴室暖房乾燥機",
            "追い焚き機能",
            "ミストサウナ機能",
            "浴室テレビ",
            "浴室に窓",
            "半身浴"
        ],
        "洗面・トイレ設備": [
            "三面鏡付き洗面化粧台",
            "シャワー水栓付き洗面台",
            "ウォシュレット",
            "手洗いカウンター（トイレ内）",
            "タンクレストイレ"
        ],
        "暖房・空調設備": [
            "床暖房（LD/全室/一部）",
            "エアコン"
        ],
        "窓・建具設備": [
            "複層ガラス（ペアガラス）",
            "Low-Eガラス",
            "二重サッシ",
            "建具：鏡面仕上げ"
        ],
        "収納設備": [
            "全居室収納",
            "WIC（ウォークインクローゼット）",
            "SIC（シューズインクローゼット）",
            "パントリー（食品庫）",
            "リネン庫"
        ],
        "セキュリティ・通信設備": [
            "TVモニター付インターホン",
            "センサーライト（玄関）",
            "インターネット光配線方式（各戸まで光）"
        ]
    },
    "mgmt_shared_etc": [
        "コンシェルジュサービス",
        "宅配ボックス",
        "ゲストルーム",
        "ラウンジ",
        "キッズルーム",
        "ジム",
        "プール",
        "ゴミ出し24時間可",
        "免震・制震構造",
        "セキュリティ（オートロック・防犯カメラ・24h有人）",
        "外観・エントランスのデザイン",
        "ブランドマンション",
        "タワーマンション",
        "長期修繕計画・資金計画",
        "修繕積立金 妥当性",
        "管理体制",
        "共有部修繕履歴",
        "収益性（利回り）"
    ],
    "parking_types": ["平置き","機械式","なし/不明"]
}

# -------------------------------
# 初期化（無ければ作る）
# -------------------------------
def ensure_master() -> Dict[str, Any]:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(MASTER_JSON):
        with open(MASTER_JSON, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_MASTER, f, ensure_ascii=False, indent=2)
    with open(MASTER_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

def save_master(d: Dict[str, Any]):
    with open(MASTER_JSON, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

M = ensure_master()

# -------------------------------
# UI
# -------------------------------
st.title("🛠 管理：マスター項目 編集（方位／専有スペック／管理・共有部／駐車場）")

st.caption(f"マスターJSON: `{MASTER_JSON}`（この画面で保存）")

# ① バルコニー向き
st.header("① バルコニー向き（表示 ↔ コード）")
with st.container(border=True):
    st.write("例：['南','S'] のように、**表示は日本語・内部コードは英字**。順番も編集可。")
    for i, pair in enumerate(list(M["balcony_facings"])):
        disp, code = pair if isinstance(pair, list) else [pair[0], pair[1]]
        c1, c2, c3, c4 = st.columns([2,1,1,1])
        with c1:
            new_disp = st.text_input("表示", value=disp, key=f"bf_d_{i}")
        with c2:
            new_code = st.text_input("コード", value=code, key=f"bf_c_{i}")
        with c3:
            if st.button("↑", key=f"bf_up_{i}") and i > 0:
                M["balcony_facings"][i-1], M["balcony_facings"][i] = M["balcony_facings"][i], M["balcony_facings"][i-1]
                save_master(M); st.experimental_rerun()
        with c4:
            if st.button("🗑 削除", key=f"bf_rm_{i}"):
                M["balcony_facings"].pop(i)
                save_master(M); st.experimental_rerun()
        M["balcony_facings"][i] = [new_disp, new_code]

    add_d = st.text_input("新規：表示", key="bf_add_d")
    add_c = st.text_input("新規：コード", key="bf_add_c")
    if st.button("＋ 追加（向き）"):
        if add_d and add_c:
            M["balcony_facings"].append([add_d, add_c])
            save_master(M)
            st.success("追加しました。")

# ② スペック（専有部分）
st.header("② スペック（専有部分）のカテゴリ＆項目")
for cat, items in list(M["spec_categories"].items()):
    with st.expander(f"【{cat}】（{len(items)}件）", expanded=False):
        new_cat = st.text_input("カテゴリ名", value=cat, key=f"catname_{cat}")
        if new_cat != cat:
            M["spec_categories"][new_cat] = M["spec_categories"].pop(cat)
            save_master(M)
            st.experimental_rerun()
        # 項目編集
        for idx, it in enumerate(list(items)):
            c1, c2 = st.columns([4,1])
            with c1:
                items[idx] = st.text_input("項目", value=it, key=f"{cat}_{idx}")
            with c2:
                if st.button("🗑", key=f"rm_{cat}_{idx}"):
                    items.pop(idx)
                    save_master(M)
                    st.experimental_rerun()
        add_it = st.text_input("新規項目", key=f"add_{cat}")
        if st.button(f"＋ 追加（{cat}）", key=f"addbtn_{cat}"):
            if add_it:
                items.append(add_it)
                save_master(M)
                st.success("追加しました。")

# ③ 管理・共有部
st.header("③ 管理・共有部・その他（チェック群）")
with st.container(border=True):
    for idx, it in enumerate(list(M["mgmt_shared_etc"])):
        c1, c2 = st.columns([4,1])
        with c1:
            M["mgmt_shared_etc"][idx] = st.text_input("項目", value=it, key=f"mg_{idx}")
        with c2:
            if st.button("🗑", key=f"mg_rm_{idx}"):
                M["mgmt_shared_etc"].pop(idx)
                save_master(M)
                st.experimental_rerun()
    add_mg = st.text_input("新規項目（管理・共有部）", key="mg_add")
    if st.button("＋ 追加（管理・共有部）"):
        if add_mg:
            M["mgmt_shared_etc"].append(add_mg)
            save_master(M)
            st.success("追加しました。")

# ④ 駐車場タイプ
st.header("④ 駐車場タイプ")
with st.container(border=True):
    for idx, it in enumerate(list(M["parking_types"])):
        c1, c2 = st.columns([4,1])
        with c1:
            M["parking_types"][idx] = st.text_input("タイプ", value=it, key=f"pk_{idx}")
        with c2:
            if st.button("🗑", key=f"pk_rm_{idx}"):
                M["parking_types"].pop(idx)
                save_master(M)
                st.experimental_rerun()
    add_pk = st.text_input("新規タイプ", key="pk_add")
    if st.button("＋ 追加（駐車場）"):
        if add_pk:
            M["parking_types"].append(add_pk)
            save_master(M)
            st.success("追加しました。")

st.divider()
if st.button("💾 すべて保存"):
    save_master(M)
    st.success("保存しました。")

# --- バルコニー方位：マスター ↔ UI 変換ユーティリティ ---
from pathlib import Path
def _load_master_balcony_pairs():
    # data/master_options.json から [["北","N"], ...] を読む
    p = Path("data/master_options.json")
    if not p.exists():
        return [["北","N"],["北東","NE"],["東","E"],["南東","SE"],["南","S"],["南西","SW"],["西","W"],["北西","NW"]]
    import json
    m = json.loads(p.read_text(encoding="utf-8"))
    return m.get("balcony_facings", [])

def _code_to_disp(code: str) -> str:
    for disp, c in _load_master_balcony_pairs():
        if c == code:
            return disp
    return "不明"

def _disp_to_code(disp: str) -> str:
    for d, code in _load_master_balcony_pairs():
        if d == disp:
            return code
    return "S"  # 既定は南