# pages/compare.py
# -*- coding: utf-8 -*-

import streamlit as st
import json, os, datetime, hashlib, sqlite3
from typing import Dict, Any, List
from contextlib import contextmanager

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
    pth = _compare_json_path(client_id)
    if os.path.exists(pth):
        try:
            return json.load(open(pth, "r", encoding="utf-8"))
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
    client_id_in = st.text_input("顧客ID", value=client_id or "")
with colB:
    if st.button("URL固定"):
        if client_id_in:
            _set_client_query(client_id_in)
            st.rerun()

# ---------------- 現在の住まい ----------------
st.header("① 現在の住まい（基準=偏差値50）")
if "curhome" not in st.session_state:
    st.session_state.curhome = {"name": "現住", "scores": {}, "comments": {}}
cur = st.session_state.curhome

with st.container(border=True):
    st.markdown("### 現在の住まいスコア（点数＋コメント入力）")
    for feat in [
        "価格","専有面積/建物面積","土地面積","間取り","築年数",
        "駅徒歩","通勤","周辺環境","管理費/修繕費","眺望",
        "ペット飼育","共用施設","戸数","インターネット環境","修繕積立金㎡単価"
    ]:
        col1, col2 = st.columns([1,3])
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
        p["name"] = st.text_input(
    "物件名",
    value=p.get("name", f"物件{i+1}"),
    key=f"name_{i}_{p.get('id', str(i))}"
)
        if "scores" not in p:
            p["scores"] = {}
        if "comments" not in p:
            p["comments"] = {}

        # ---------------- 基本情報・スペック ----------------
        st.markdown("### 基本情報・スペック")
        for feat in [
            "価格","専有面積/建物面積","土地面積","間取り","築年数",
            "駅徒歩","通勤","周辺環境","管理費/修繕費","眺望",
            "ペット飼育","共用施設","戸数","インターネット環境","修繕積立金㎡単価"
        ]:
            col1, col2 = st.columns([1,3])
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
prop_type = st.radio("🏘️ 種別を選択", ["マンション", "戸建・土地"], key=f"type_select_{i}")

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

# 表示
for feat in check_items:
    col1, col2 = st.columns([1,3])
    with col1:
        p["scores"][feat] = st.number_input(
            f"{feat} 点数 (0〜5)",
            min_value=0,
            max_value=5,
            value=int(p["scores"].get(feat, 0)),
            key=f"insp_{prop_type}_{feat}_score_{i}_{p.get('id', str(i))}"
        )
    with col2:
        p["comments"][feat] = st.text_input(
            f"{feat} コメント",
            value=p["comments"].get(feat, ""),
            key=f"insp_{prop_type}_{feat}_comment_{i}_{p.get('id', str(i))}"
        )

# ================= PDF出力 =================
st.markdown("### 🖨️ チェックリストPDF出力")
from fpdf import FPDF
import io

if st.button("📄 PDFを生成・ダウンロード"):
    pdf = FPDF()
    pdf.add_page()
    font_path = os.path.join("fonts", "ipaexg.ttf")
if os.path.exists(font_path):
    pdf.add_font("IPAexGothic", "", font_path, uni=True)
    pdf.set_font("IPAexGothic", "", 12)
else:
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, f"{p['name']} {prop_type} 内見チェックリスト", ln=True)

    for feat in check_items:
        score = p["scores"].get(feat, "")
        comment = p["comments"].get(feat, "")
        pdf.multi_cell(0, 8, f"{feat}：{score}点　{comment}")

    pdf_output = io.BytesIO()
    pdf.output(pdf_output)
    st.download_button(
        label="📥 PDFダウンロード",
        data=pdf_output.getvalue(),
        file_name=f"{p['name']}_{prop_type}_内見チェックリスト.pdf",
        mime="application/pdf"
    )
                # ---------------- 物件入力タブ（続き） ----------------
tabs = st.tabs([p["name"] for p in props])

for i, tab in enumerate(tabs):
    with tab:
        p = props[i]
        p["name"] = st.text_input(
            "物件名", value=p.get("name", f"物件{i+1}"), key=f"name_{i}"
        )
        if "scores" not in p:
            p["scores"] = {}
        if "comments" not in p:
            p["comments"] = {}

       # ================= 基本情報 =================
st.subheader("基本情報")
for feat in [
    "価格","専有面積","建物面積","土地面積","坪単価",
    "間取り","築年数","所在階","総戸数","バルコニー向き",
    "駅徒歩","勤務先アクセス","周辺環境","子育て支援",
    "管理費","修繕積立金","戸数","眺望","角部屋","日当たり"
]:
    col1, col2 = st.columns([1,3])
    with col1:
        p["scores"][feat] = st.number_input(
            f"{feat} 点数 (0〜5)",
            min_value=0,
            max_value=5,
            value=int(p["scores"].get(feat, 0)),
            key=f"{feat}_score_{i}_{p.get('id', str(i))}"
        )
    with col2:
        p["comments"][feat] = st.text_input(
            f"{feat} コメント",
            value=p["comments"].get(feat, ""),
            key=f"{feat}_comment_{i}_{p.get('id', str(i))}"
        )
     

        # ================= マンション専用 =================
st.subheader("マンション専用チェック")
for feat in [
    "エレベーター台数","共用施設","宅配ボックス","管理人常駐",
    "セキュリティ","耐震性能","免震・制震","タワーマンション",
    "ブランド力","管理体制","長期修繕計画","資産価値"
]:
    col1, col2 = st.columns([1,3])
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

# ---------------- サマリー ----------------
st.header("③ 比較サマリー")
rows = []
for p in props:
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
        for feat, comment in p["comments"].items():
            if comment:
                st.write(f"**{feat}**: {comment}")
                # ---------------- 自動保存 ----------------
if client_id_in:
    prev = {"props": props, "current_home": cur}
    cur_hash = _hash_dict(prev)
    if st.session_state.get("__last_hash__") != cur_hash:
        save_compare_state(client_id_in, prev)
        st.session_state["__last_hash__"] = cur_hash
        st.toast("💾 自動保存しました")
        st.session_state["__last_hash__"] = cur_hash

# ---------------- データエクスポート ----------------
st.header("⑤ データ出力")

col1, col2 = st.columns(2)
with col1:
    if st.button("📤 JSONエクスポート"):
        export = {"props": props, "current_home": cur}
        st.download_button(
            "JSONダウンロード",
            data=json.dumps(export, ensure_ascii=False, indent=2),
            file_name=f"compare_{client_id_in or 'noid'}.json",
            mime="application/json"
        )
with col2:
    if st.button("📑 コメント一覧エクスポート"):
        lines = []
        for p in props:
            lines.append(f"=== {p['name']} ===")
            for feat, cmt in p["comments"].items():
                if cmt:
                    lines.append(f"{feat}: {cmt}")
            lines.append("")
        st.download_button(
            "コメントTXTダウンロード",
            data="\n".join(lines),
            file_name=f"comments_{client_id_in or 'noid'}.txt",
            mime="text/plain"
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
    import matplotlib.pyplot as plt
    import numpy as np

    feats = list(cur["scores"].keys())
    N = len(feats)

    fig, ax = plt.subplots(subplot_kw={"polar": True}, figsize=(8,8))

    # 現住
    cur_values = [cur["scores"].get(f, 0) for f in feats]
    cur_values += cur_values[:1]
    angles = np.linspace(0, 2*np.pi, N, endpoint=False).tolist()
    angles += angles[:1]
    ax.plot(angles, cur_values, label="現住", linewidth=2)
    ax.fill(angles, cur_values, alpha=0.25)

    # 各物件
    for p in props:
        vals = [p["scores"].get(f, 0) for f in feats]
        vals += vals[:1]
        ax.plot(angles, vals, linewidth=1, linestyle="--", label=p["name"])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(feats, fontsize=8)
    ax.set_yticks(range(0,6))
    ax.legend(loc="upper right", bbox_to_anchor=(1.3,1.1))
    st.pyplot(fig)

# ---------------- 完了 ----------------
st.success("✅ 物件比較アプリのフル機能ロードが完了しました。")
