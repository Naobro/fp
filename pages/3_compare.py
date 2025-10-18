# pages/compare.py
# -*- coding: utf-8 -*-

import streamlit as st
import json, os, datetime, hashlib, sqlite3
from typing import Dict, Any, List
from contextlib import contextmanager
from fpdf import FPDF # ← これを追加
import io # ← PDF出力時に使用するのでここで読み込む

# ---------------- グローバル設定 ----------------
st.set_page_config(
    page_title="物件比較｜点数＋コメント入力 × 偏差値（顧客別自動保存・フル版）",
    layout="wide"
)

# ディレクトリとDBの準備
DATA_DIR    = "data"
CLIENTS_DIR = os.path.join(DATA_DIR, "clients")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = "clients.db"

# ---------------- DBユーティリティ ----------------
@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def _table_exists(conn, name: str) -> bool:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
        (name,)
    )
    return cur.fetchone() is not None

def init_db():
    """compare_states テーブルを作成（存在しない場合のみ）"""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS compare_states (
                client_id TEXT PRIMARY KEY,
                updated_at TEXT NOT NULL,
                state TEXT NOT NULL
            )
        """)
        conn.commit()

def _ensure_schema_if_writable(conn):
    """保存時のみテーブルを保証"""
    if not _table_exists(conn, "compare_states"):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS compare_states (
                client_id TEXT PRIMARY KEY,
                updated_at TEXT NOT NULL,
                state TEXT NOT NULL
            )
        """)
        conn.commit()

# ---------------- 顧客IDユーティリティ ----------------
def _get_client_id_from_query() -> str | None:
    """URL ?client=xxx から顧客IDを取得"""
    try:
        v = st.query_params.get("client", None)
        if isinstance(v, list):
            v = v[0] if v else None
        return (str(v).strip() or None) if v else None
    except Exception:
        # st.experimental_get_query_params の代替（Streamlit > 1.28.0 では非推奨）
        qp = st.experimental_get_query_params()
        v = qp.get("client", [None])
        v = v[0] if isinstance(v, list) else v
        return (str(v).strip() or None) if v else None

def _set_client_query(cid: str):
    """URLに顧客IDを固定"""
    try:
        st.query_params["client"] = cid
    except Exception:
        st.experimental_set_query_params(client=cid)

def _client_dir(cid: str) -> str:
    return os.path.join(CLIENTS_DIR, cid)

def _ensure_client_dir(cid: str):
    os.makedirs(_client_dir(cid), exist_ok=True)

def _compare_json_path(cid: str) -> str:
    return os.path.join(_client_dir(cid), "compare.json")

# ---------------- 保存/読込ユーティリティ ----------------
def load_compare_state(client_id: str) -> Dict[str, Any]:
    """顧客データの読込（DB優先・なければJSONファイル）"""
    with get_db() as conn:
        if _table_exists(conn, "compare_states"):
            row = conn.execute(
                "SELECT state FROM compare_states WHERE client_id=?",
                (client_id,)
            ).fetchone()
            if row and row["state"]:
                try:
                    return json.loads(row["state"])
                except Exception:
                    pass
    
    # JSONファイルからの読み込み (with open を使用して安全に)
    pth = _compare_json_path(client_id)
    if os.path.exists(pth):
        try:
            with open(pth, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_compare_state(client_id: str, state: Dict[str, Any]):
    """顧客データを保存（DB優先、失敗時はJSON）"""
    try:
        with get_db() as conn:
            _ensure_schema_if_writable(conn)
            conn.execute(
                "INSERT OR REPLACE INTO compare_states (client_id, updated_at, state) VALUES (?, ?, ?)",
                (client_id, datetime.datetime.now().isoformat(), json.dumps(state, ensure_ascii=False))
            )
            conn.commit()
            return
    except Exception as e:
        st.warning(f"DB保存失敗: {e}")

    _ensure_client_dir(client_id)
    with open(_compare_json_path(client_id), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def _hash_dict(d: Dict[str, Any]) -> str:
    try:
        s = json.dumps(d, ensure_ascii=False, sort_keys=True)
    except Exception:
        s = json.dumps(d.get("props", {}), ensure_ascii=False, sort_keys=True)
    return hashlib.md5(s.encode("utf-8")).hexdigest()

# ---------------- 偏差値計算 ----------------
def to_hensachi_rel(score: float, cur: float) -> float:
    return 50.0 + (score - cur)

# ---------------- UI 開始 ----------------
st.title("🏠 物件比較｜")

client_id = _get_client_id_from_query()
colA, colB = st.columns([2,1])
with colA:
    # 顧客IDがURLに設定されている場合、それを初期値として使用
    client_id_in = st.text_input("顧客ID", value=client_id or "")
with colB:
    if st.button("URL固定"):
        if client_id_in:
            _set_client_query(client_id_in)
            st.rerun()

# 顧客IDに基づいてデータをロード（UI要素が作成される前に実行される必要あり）
if client_id_in and "props" not in st.session_state:
    loaded_state = load_compare_state(client_id_in)
    if "props" in loaded_state:
        st.session_state.props = loaded_state["props"]
    if "current_home" in loaded_state:
        st.session_state.curhome = loaded_state["current_home"]

# ---------------- 現在の住まい ----------------
st.header("① 現在の住まい（基準=偏差値50）")
if "curhome" not in st.session_state:
    # 初期化：5件の検討物件と比較できるように現住のスコア項目も定義
    curhome_feats = [
        "価格","専有面積/建物面積","土地面積","間取り","築年数",
        "駅徒歩","通勤","周辺環境","管理費/修繕費","眺望",
        "ペット飼育","共用施設","戸数","インターネット環境","修繕積立金㎡単価"
    ]
    st.session_state.curhome = {
        "name": "現住", 
        "scores": {f: 0 for f in curhome_feats}, 
        "comments": {f: "" for f in curhome_feats}
    }

cur = st.session_state.curhome

with st.container(border=True):
    st.markdown("### 現在の住まいスコア（点数＋コメント入力）")
    # scoresとcommentsのキーを確実に取得
    all_cur_feats = list(set(cur["scores"].keys()) | set(cur["comments"].keys()) | 
                        {"価格","専有面積/建物面積","土地面積","間取り","築年数",
                        "駅徒歩","通勤","周辺環境","管理費/修繕費","眺望",
                        "ペット飼育","共用施設","戸数","インターネット環境","修繕積立金㎡単価"})
    
    for feat in all_cur_feats:
        # ここで定義されている基本の15項目に限定
        if feat not in [
            "価格","専有面積/建物面積","土地面積","間取り","築年数",
            "駅徒歩","通勤","周辺環境","管理費/修繕費","眺望",
            "ペット飼育","共用施設","戸数","インターネット環境","修繕積立金㎡単価"
        ]:
            continue
            
        col1, col2 = st.columns([1,3])
        # scoresにキーが存在しない場合の初期値設定
        if feat not in cur["scores"]:
             cur["scores"][feat] = 0
        if feat not in cur["comments"]:
             cur["comments"][feat] = ""
             
        with col1:
            cur["scores"][feat] = st.number_input(
                f"{feat} 点数 (0〜5)", min_value=0, max_value=5,
                value=int(cur["scores"].get(feat, 0)), key=f"cur_{feat}_score"
            )
        with col2:
            cur["comments"][feat] = st.text_input(
                f"{feat} コメント",
                value=cur["comments"].get(feat, ""), key=f"cur_{feat}_comment"
            )

cur_total = sum(cur["scores"].values())
st.metric("現住スコア合計", cur_total)
cur_score = cur_total

# ---------------- 検討物件 ----------------
st.header("② 検討物件（点数＋コメント入力）")

if "props" not in st.session_state:
    st.session_state.props = [
        {"name": f"物件{i+1}", "scores": {}, "comments": {}} for i in range(5)
    ]
props: List[Dict[str, Any]] = st.session_state.props

tabs = st.tabs([p["name"] for p in props])
for i, tab in enumerate(tabs):
    with tab:
        p = props[i]
        
        # 物件名
        p["name"] = st.text_input(
            "物件名",
            value=p.get("name", f"物件{i+1}"),
            key=f"name_{i}_{p.get('id', str(i))}"
        )
        if "scores" not in p:
            p["scores"] = {}
        if "comments" not in p:
            p["comments"] = {}

        # ================= 基本情報・スペック =================
        st.markdown("### 基本情報・スペック")
        for feat in [
            "価格","専有面積/建物面積","土地面積","間取り","築年数",
            "駅徒歩","通勤","周辺環境","管理費/修繕費","眺望",
            "ペット飼育","共用施設","戸数","インターネット環境","修繕積立金㎡単価"
        ]:
            col1, col2 = st.columns([1,3])
            # scoresにキーが存在しない場合の初期値設定
            if feat not in p["scores"]:
                p["scores"][feat] = 0
            if feat not in p["comments"]:
                p["comments"][feat] = ""
                
            with col1:
                p["scores"][feat] = st.number_input(
                    f"{feat} 点数 (0〜5)", min_value=0, max_value=5,
                    value=int(p["scores"].get(feat, 0)), key=f"{feat}_score_{i}"
                )
            with col2:
                p["comments"][feat] = st.text_input(
                    f"{feat} コメント",
                    value=p["comments"].get(feat, ""), key=f"{feat}_comment_{i}"
                )

        # ================= 内見チェックリスト =================
        st.subheader("内見チェックリスト")

        # タイプ選択：マンション / 戸建・土地
        # セッションステートに型を保存し、再描画時に選択を維持
        type_key = f"type_select_{i}"
        if type_key not in st.session_state:
            st.session_state[type_key] = "マンション"
            
        prop_type = st.radio("🏘️ 種別を選択", ["マンション", "戸建・土地"], 
                             key=type_key, index=["マンション", "戸建・土地"].index(st.session_state[type_key]))

        if prop_type == "マンション":
            check_items = [
                "外壁・共用廊下","エントランス・管理体制","宅配ボックス","エレベーター",
                "セキュリティ","耐震性能","共用施設","騒音・振動","管理人常駐","ゴミ出し動線",
                "長期修繕計画","資産価値","眺望","通風","日当たり"
            ]
        else:
            check_items = [
                "外壁・屋根","基礎・擁壁","排水溝・雨樋","越境・境界","駐車場","庭・外構",
                "前面道路幅員","前面道路方位","地型","断熱性能","防音性能",
                "上下水・ガス・電気設備","太陽光・オール電化","耐震性能","眺望・採光"
            ]

        # 内見チェックリストの項目入力
        for feat in check_items:
            col1, col2 = st.columns([1,3])
            # scoresにキーが存在しない場合の初期値設定
            if feat not in p["scores"]:
                p["scores"][feat] = 0
            if feat not in p["comments"]:
                p["comments"][feat] = ""
                
            with col1:
                p["scores"][feat] = st.number_input(
                    f"{feat} 点数 (0〜5)",
                    min_value=0, max_value=5,
                    value=int(p["scores"].get(feat, 0)),
                    key=f"insp_{prop_type}_{feat}_score_{i}_{p.get('id', str(i))}"
                )
            with col2:
                p["comments"][feat] = st.text_input(
                    f"{feat} コメント",
                    value=p["comments"].get(feat, ""),
                    key=f"insp_{prop_type}_{feat}_comment_{i}_{p.get('id', str(i))}"
                )

        # ================= その他の詳細情報入力（修正でここに移動） =================
        # 冗長なコードを削除し、タブ内に含めました。
        
        # ================= 基本情報 (続きの項目) =================
        st.subheader("基本情報（追加）")
        for feat in [
            "坪単価","所在階","総戸数","バルコニー向き","勤務先アクセス","子育て支援"
        ]: # 重複項目を除外
            col1, col2 = st.columns([1,3])
            if feat not in p["scores"]:
                p["scores"][feat] = 0
            if feat not in p["comments"]:
                p["comments"][feat] = ""
                
            with col1:
                p["scores"][feat] = st.number_input(
                    f"{feat} 点数 (0〜5)",
                    min_value=0,
                    max_value=5,
                    value=int(p["scores"].get(feat, 0)),
                    key=f"{feat}_score_{i}_{p.get('id', str(i))}_cont"
                )
            with col2:
                p["comments"][feat] = st.text_input(
                    f"{feat} コメント",
                    value=p["comments"].get(feat, ""),
                    key=f"{feat}_comment_{i}_{p.get('id', str(i))}_cont"
                )

        # ================= マンション専用 =================
        st.subheader("マンション専用チェック")
        for feat in [
            "エレベーター台数","共用施設","宅配ボックス","管理人常駐",
            "セキュリティ","耐震性能","免震・制震","タワーマンション",
            "ブランド力","管理体制","長期修繕計画","資産価値"
        ]:
            col1, col2 = st.columns([1,3])
            if feat not in p["scores"]:
                p["scores"][feat] = 0
            if feat not in p["comments"]:
                p["comments"][feat] = ""
                
            with col1:
                p["scores"][feat] = st.number_input(
                    f"{feat} 点数 (0〜5)",
                    min_value=0,
                    max_value=5,
                    value=int(p["scores"].get(feat, 0)),
                    key=f"mans_{feat}_score_{i}_{p.get('id', str(i))}"
                )
            with col2:
                p["comments"][feat] = st.text_input(
                    f"{feat} コメント",
                    value=p["comments"].get(feat, ""),
                    key=f"mans_{feat}_comment_{i}_{p.get('id', str(i))}"
                )

        # ================= 戸建て専用 =================
        st.subheader("戸建て専用チェック")
        for feat in [
            "越境","境界確認","駐車場台数","角地","前面道路幅員",
            "前面道路方位","地型","都市ガス/プロパン/オール電化",
            "太陽光発電","追加リフォーム","庭の広さ","外構"
        ]:
            col1, col2 = st.columns([1,3])
            if feat not in p["scores"]:
                p["scores"][feat] = 0
            if feat not in p["comments"]:
                p["comments"][feat] = ""
                
            with col1:
                p["scores"][feat] = st.number_input(
                    f"{feat} 点数 (0〜5)",
                    min_value=0, max_value=5,
                    value=int(p["scores"].get(feat, 0)),
                    key=f"house_{feat}_score_{i}"
                )
            with col2:
                p["comments"][feat] = st.text_input(
                    f"{feat} コメント",
                    value=p["comments"].get(feat, ""),
                    key=f"house_{feat}_comment_{i}"
                )

        # ================= プラスポイント / マイナスポイント =================
        st.subheader("プラスポイント / マイナスポイント")
        for feat in ["プラスポイント", "マイナスポイント"]:
            col1, col2 = st.columns([1,3])
            if feat not in p["scores"]:
                p["scores"][feat] = 0
            if feat not in p["comments"]:
                p["comments"][feat] = ""
                
            with col1:
                p["scores"][feat] = st.number_input(
                    f"{feat} 点数 (0〜5)",
                    min_value=0, max_value=5,
                    value=int(p["scores"].get(feat, 0)),
                    key=f"{feat}_score_{i}"
                )
            with col2:
                p["comments"][feat] = st.text_area(
                    f"{feat} コメント",
                    value=p["comments"].get(feat, ""),
                    key=f"{feat}_comment_{i}"
                )
                
        # ================= PDF出力（タブ内のボタン） =================
        if st.button(f"📄 {p['name']} のPDFを生成・ダウンロード", key=f"pdf_btn_{i}"):
            
            # PDF生成時に使用するチェックリスト項目を再計算
            current_prop_type = st.session_state.get(f"type_select_{i}", "マンション")

            if current_prop_type == "マンション":
                pdf_check_items = [
                    "外壁・共用廊下","エントランス・管理体制","宅配ボックス","エレベーター",
                    "セキュリティ","耐震性能","共用施設","騒音・振動","管理人常駐","ゴミ出し動線",
                    "長期修繕計画","資産価値","眺望","通風","日当たり"
                ]
            else:
                pdf_check_items = [
                    "外壁・屋根","基礎・擁壁","排水溝・雨樋","越境・境界","駐車場","庭・外構",
                    "前面道路幅員","前面道路方位","地型","断熱性能","防音性能",
                    "上下水・ガス・電気設備","太陽光・オール電化","耐震性能","眺望・採光"
                ]
            
            # フォント探索
            candidate_fonts = [
                os.path.join("fonts", "ipaexg.ttf"),
                os.path.join("fonts", "NotoSansJP-Regular.ttf"),
                "ipaexg.ttf",
                "NotoSansJP-Regular.ttf"
            ]
            font_path = next((path for path in candidate_fonts if os.path.exists(path)), None)

            # PDF生成
            pdf = FPDF(orientation="P", unit="mm", format="A4")
            pdf.set_auto_page_break(auto=True, margin=12)
            pdf.add_page()

            # フォント設定
            if font_path:
                try:
                    pdf.add_font("JP", "", font_path, uni=True)
                    pdf.set_font("JP", "", 12)
                except Exception as e:
                    st.warning(f"⚠️ フォント登録エラー ({e}) → Helveticaに切替。日本語非対応。")
                    pdf.set_font("Helvetica", "", 12)
            else:
                st.warning("⚠️ 日本語フォントが見つかりません。/fonts に ipaexg.ttf を配置してください。")
                pdf.set_font("Helvetica", "", 12)


            # タイトル
            pdf.cell(0, 10, f"{p['name']}（{current_prop_type}）内見チェックリスト", ln=True)
            pdf.ln(5)

            # テーブルヘッダー
            pdf.set_fill_color(230, 230, 230)
            pdf.cell(60, 8, "項目", border=1, fill=True)
            pdf.cell(20, 8, "点数", border=1, fill=True, align="C")
            pdf.cell(0, 8, "コメント", border=1, fill=True)
            pdf.ln(8)

            # 各項目
            for feat in pdf_check_items: # check_items の代わりに pdf_check_items を使用
                score = str(p["scores"].get(feat, ""))
                comment = p["comments"].get(feat, "")
                pdf.cell(60, 8, feat, border=1)
                pdf.cell(20, 8, score, border=1, align="C")
                pdf.cell(0, 8, comment, border=1)
                pdf.ln(8)

            # バイナリ出力
            try:
                pdf_data = pdf.output(dest="S").encode("latin1", "ignore")
            except Exception:
                # fpdf の output(dest="S") が str を返さない環境向け
                pdf_buffer = io.BytesIO()
                pdf.output(pdf_buffer)
                pdf_buffer.seek(0)
                pdf_data = pdf_buffer.read()

            st.download_button(
                label="📥 PDFダウンロード",
                data=pdf_data,
                file_name=f"{p['name']}_{current_prop_type}_内見チェックリスト.pdf",
                mime="application/pdf",
                key=f"dl_btn_{i}"
            )
        # 修正: ここにあった重複コードを削除

# ---------------- サマリー ----------------
st.header("③ 比較サマリー")
rows = []
for p in props:
    # 現在のスコア項目リストに存在する点数のみを合計
    # 現住のスコア項目と検討物件のスコア項目は必ずしも一致しないため、ここではその物件に入力された点数全てを合計
    total = sum(p["scores"].values())
    rel = to_hensachi_rel(total, cur_score)
    rows.append({
        "物件名": p["name"],
        "合計点": total,
        "偏差値(現住=50)": round(rel, 1)
    })

st.dataframe(rows, use_container_width=True)

# コメントまとめ
st.subheader("④ コメント一覧")
for p in props:
    with st.expander(f"💬 {p['name']} コメント一覧"):
        # 現住コメントも表示するなら、ここで cur["comments"] のループを追加
        for feat, comment in p["comments"].items():
            if comment:
                st.write(f"**{feat}**: {comment}")
            
# ---------------- 自動保存 ----------------
if client_id_in:
    prev = {"props": props, "current_home": cur}
    cur_hash = _hash_dict(prev)
    
    # セッションステートの初期化とチェック
    if "__last_hash__" not in st.session_state:
         st.session_state["__last_hash__"] = None

    if st.session_state.get("__last_hash__") != cur_hash:
        # DBに保存
        save_compare_state(client_id_in, prev)
        st.session_state["__last_hash__"] = cur_hash
        st.toast("💾 自動保存しました")
        # st.session_state["__last_hash__"] の再設定は不要（上の行で実行済み）

# ---------------- データエクスポート ----------------
st.header("⑤ データ出力")

col1, col2 = st.columns(2)
with col1:
    export = {"props": props, "current_home": cur}
    # ダウンロードボタンはボタンクリック時にのみデータ生成する方が好ましいため、外に移動（Streamlitの挙動に合わせる）
    st.download_button(
        "📥 JSONダウンロード",
        data=json.dumps(export, ensure_ascii=False, indent=2),
        file_name=f"compare_{client_id_in or 'noid'}.json",
        mime="application/json",
        key="json_dl_btn"
    )
with col2:
    lines = []
    # 現住のコメントを追加
    lines.append(f"=== {cur['name']} ===")
    for feat, cmt in cur["comments"].items():
        if cmt:
            lines.append(f"{feat}: {cmt}")
    lines.append("")
    # 各物件のコメント
    for p in props:
        lines.append(f"=== {p['name']} ===")
        for feat, cmt in p["comments"].items():
            if cmt:
                lines.append(f"{feat}: {cmt}")
        lines.append("")
    
    st.download_button(
        "📑 コメントTXTダウンロード",
        data="\n".join(lines),
        file_name=f"comments_{client_id_in or 'noid'}.txt",
        mime="text/plain",
        key="txt_dl_btn"
    )

# ---------------- DB操作 ----------------
st.header("⑥ データベース操作")
with st.expander("🔧 DB操作（手動）"):
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🛠 DB初期化"):
            init_db()
            st.success("DBを確認/作成しました")

    with col2:
        cid = client_id_in
        if st.button("🗑 データ削除", disabled=not bool(cid)):
            if not cid:
                st.warning("顧客IDが未設定です")
            else:
                with get_db() as conn:
                    if _table_exists(conn, "compare_states"):
                        conn.execute("DELETE FROM compare_states WHERE client_id=?", (cid,))
                        conn.commit()
                        st.success(f"顧客 `{cid}` のデータを削除しました")
                    else:
                        st.info("テーブルがまだ存在しません")

    with col3:
        if st.button("📂 全件確認"):
            with get_db() as conn:
                if _table_exists(conn, "compare_states"):
                    rows = conn.execute("SELECT client_id, updated_at FROM compare_states").fetchall()
                    if rows:
                        st.write("保存済み一覧:")
                        for r in rows:
                            st.write(f"- {r['client_id']} ({r['updated_at']})")
                    else:
                        st.info("保存データがありません")
                else:
                    st.info("テーブル未作成です")

# ---------------- 分析機能 ----------------
st.header("⑦ 追加分析")

if st.button("📊 スコアレーダーチャート表示"):
    # グラフライブラリはボタンクリック時にインポート
    import matplotlib.pyplot as plt
    import numpy as np

    # 現住と検討物件の共通のスコア項目を抽出（レーダーチャートの軸とする）
    # 現住のスコアキーと、各検討物件のスコアキーを統合したセット
    all_feats = set(cur["scores"].keys())
    for p in props:
        all_feats.update(p["scores"].keys())
        
    # スコア値が入っている項目のみを軸として採用（空の項目を避ける）
    feats = sorted([f for f in all_feats if cur["scores"].get(f, 0) > 0 or any(p["scores"].get(f, 0) > 0 for p in props)])
    
    if not feats:
        st.warning("レーダーチャートを表示するためのスコアデータがありません。（点数が全て0です）")
    else:
        N = len(feats)

        # 0 ~ 360度にN分割
        angles = np.linspace(0, 2*np.pi, N, endpoint=False).tolist()
        angles += angles[:1] # 閉じたグラフにするため最初の要素を最後に追加

        fig, ax = plt.subplots(subplot_kw={"polar": True}, figsize=(8,8))

        # 現住
        cur_values = [cur["scores"].get(f, 0) for f in feats]
        cur_values += cur_values[:1]
        ax.plot(angles, cur_values, label="現住", linewidth=2, color="blue")
        ax.fill(angles, cur_values, alpha=0.25, color="blue")

        # 各物件
        for i, p in enumerate(props):
            # 点数が全く入力されていない物件はスキップ
            if sum(p["scores"].values()) == 0:
                continue
            
            vals = [p["scores"].get(f, 0) for f in feats]
            vals += vals[:1]
            # 線の色を変える
            color = plt.cm.Set1(i % 9) 
            ax.plot(angles, vals, linewidth=1.5, linestyle="-", label=p["name"], color=color)
            ax.fill(angles, vals, alpha=0.15, color=color)

        ax.set_xticks(angles[:-1])
        # 軸ラベルの文字サイズを調整
        ax.set_xticklabels(feats, fontsize=8) 
        # スコアの最大値は5なので、目盛りは0から5
        ax.set_yticks(range(0,6))
        # 軸の最大値を5に固定
        ax.set_rlabel_position(0)
        ax.set_ylim(0, 5) 
        
        ax.legend(loc="upper right", bbox_to_anchor=(1.3,1.1))
        
        # タイトルを追加
        ax.set_title("物件スコア レーダーチャート", va='bottom', fontsize=14)
        
        st.pyplot(fig)

# ---------------- 完了 ----------------
st.success("✅ 物件比較アプリのフル機能ロードが完了しました。")
