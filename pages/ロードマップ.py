# pages/7_ロードマップ.py
# 縦=項目 / 横=日付 の横テーブル編集＋PDF出力（購入 / 売却 / 買い替え）
# 依存: streamlit, pandas, matplotlib（ReportLab不要）
from pathlib import Path
from typing import Dict
import io

import streamlit as st
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle

# ===== 基本設定 =====
st.set_page_config(page_title="ロードマップ（横テーブル）", page_icon="🗓️", layout="wide")
APP_TITLE = "不動産ロードマップ（横テーブル：縦=項目／横=日付）"

# 日本語フォント（任意）
FONT_PATH = Path("fonts/NotoSansJP-Regular.ttf")
if FONT_PATH.exists():
    try:
        matplotlib.font_manager.fontManager.addfont(str(FONT_PATH))
        plt.rcParams["font.family"] = matplotlib.font_manager.FontProperties(fname=str(FONT_PATH)).get_name()
    except Exception:
        pass

# ===== 初期行 =====
PURCHASE_ITEMS_DEFAULT = [
    "問合せ", "初回面談", "ライフプランニング", "条件整理", "事前審査",
    "内見①", "内見②", "内見③", "売買契約", "本申込", "金消契約", "決済（引渡し）",
]
SALE_ITEMS_DEFAULT = [
    "問合せ", "初回面談", "売出価格査定", "買取保証査定", "訪問査定",
    "媒介契約", "ポータルサイト掲載", "レインズ掲載", "内見",
    "売買契約", "本申込", "金消契約", "決済（引渡し）",
]
REPLACE_PURCHASE_ITEMS_DEFAULT = ["内見①", "内見②", "売買契約", "決済（引渡し）"]
REPLACE_SALE_ITEMS_DEFAULT     = ["媒介契約", "内見", "売買契約", "決済（引渡し）"]

DEFAULT_COLS = 20           # ★ 初期列数を20に拡張（必要に応じてUIで変更可）
MAX_COLS     = 50           # ★ 上限50列

# ===== State =====
def init_state_once():
    if "roadmap" in st.session_state:
        return
    def _block(rows_src):
        return dict(
            col_count=DEFAULT_COLS,
            headers=[""] * DEFAULT_COLS,
            rows=[{"項目": name, "cells": [""] * DEFAULT_COLS} for name in rows_src],
        )
    st.session_state.roadmap = dict(
        purchase=_block(PURCHASE_ITEMS_DEFAULT),
        sale=_block(SALE_ITEMS_DEFAULT),
        replace=dict(
            up=_block(REPLACE_PURCHASE_ITEMS_DEFAULT),
            down=_block(REPLACE_SALE_ITEMS_DEFAULT),
        ),
    )

# ===== 共通ユーティリティ =====
def resize_columns(block: Dict, new_count: int):
    """列数を増減（既存値は可能な限り保持）"""
    new_count = max(1, min(MAX_COLS, int(new_count)))
    cur = block["col_count"]
    if new_count == cur:
        return
    # headers
    if new_count > cur:
        block["headers"].extend([""] * (new_count - cur))
    else:
        block["headers"] = block["headers"][:new_count]
    # rows
    for r in block["rows"]:
        if new_count > cur:
            r["cells"].extend([""] * (new_count - cur))
        else:
            r["cells"] = r["cells"][:new_count]
    block["col_count"] = new_count

def add_row(block: Dict, label_default="新規項目"):
    block["rows"].append({"項目": label_default, "cells": [""] * block["col_count"]})

def delete_row(block: Dict, idx: int):
    if 0 <= idx < len(block["rows"]):
        block["rows"].pop(idx)

def render_editor(block: Dict, key_prefix: str, title_help: str = ""):
    # 列数コントロール（数値指定）
    cc1, cc2, cc3 = st.columns([2, 2, 6])
    with cc1:
        new_cols = st.number_input(
            "列数（日付の数）", min_value=1, max_value=MAX_COLS,
            value=int(block["col_count"]), step=1, key=f"{key_prefix}_colnum"
        )
    with cc2:
        if st.button("列数を反映", key=f"{key_prefix}_applycols"):
            resize_columns(block, new_cols)
            st.rerun()
    with cc3:
        st.caption(title_help or "ヘッダー（日付）は自由入力：例 9/5, 9/7, 9/10…。セルは「■」「10:00」等を記入。")

    # ヘッダー（日付）
    head_cols = st.columns([2] + [1] * block["col_count"])
    head_cols[0].markdown("**項目**")
    for i in range(block["col_count"]):
        block["headers"][i] = head_cols[i+1].text_input(
            " ", value=block["headers"][i],
            key=f"{key_prefix}_hdr_{i}", placeholder=f"9/{5+i}"
        )

    st.write("---")

    # 行追加/削除
    a1, a2, _ = st.columns([1,1,8])
    with a1:
        if st.button("＋行追加", key=f"{key_prefix}_addrow"):
            add_row(block)
    with a2:
        st.caption("行末の🗑で削除")

    # 本体
    for r_idx, row in enumerate(block["rows"]):
        cols = st.columns([2] + [1]*block["col_count"] + [0.5])
        row["項目"] = cols[0].text_input(" ", value=row["項目"], key=f"{key_prefix}_item_{r_idx}")
        for c_idx in range(block["col_count"]):
            row["cells"][c_idx] = cols[c_idx+1].text_input(
                " ", value=row["cells"][c_idx], key=f"{key_prefix}_cell_{r_idx}_{c_idx}"
            )
        if cols[-1].button("🗑", key=f"{key_prefix}_delrow_{r_idx}"):
            delete_row(block, r_idx)
            st.rerun()

def to_dataframe(block: Dict) -> pd.DataFrame:
    headers = ["項目"] + block["headers"]
    data = [[r["項目"], *r["cells"]] for r in block["rows"]]
    return pd.DataFrame(data, columns=headers)

# ===== Matplotlib でPDF化 =====
def draw_table(ax, df: pd.DataFrame, title: str):
    ax.clear(); ax.axis("off")
    n_rows = len(df) + 1
    n_cols = len(df.columns)

    # レイアウト
    item_w_ratio = 0.22
    width = 1.0
    item_w = item_w_ratio * width
    date_w = (width - item_w) / max(1, n_cols-1)
    row_h = 1.0 / n_rows

    # タイトル
    ax.text(0, 1.02, title, ha="left", va="bottom", fontsize=12, transform=ax.transAxes)

    # ヘッダー
    from matplotlib.patches import Rectangle
    y = 1 - row_h
    ax.add_patch(Rectangle((0, y), item_w, row_h, fc=(0.92,0.92,0.92), ec="black", lw=1))
    ax.text(0.01, y+row_h/2, str(df.columns[0]), va="center", ha="left", fontsize=9, transform=ax.transAxes)
    x = item_w
    for j in range(1, n_cols):
        ax.add_patch(Rectangle((x, y), date_w, row_h, fc=(0.92,0.92,0.92), ec="black", lw=1))
        hdr = "" if pd.isna(df.columns[j]) else str(df.columns[j])
        ax.text(x+date_w/2, y+row_h/2, hdr, va="center", ha="center", fontsize=9, transform=ax.transAxes)
        x += date_w

    # 本体
    for i in range(len(df)):
        y = 1 - row_h*(i+2)
        ax.add_patch(Rectangle((0, y), item_w, row_h, fc="white", ec="black", lw=1))
        ax.text(0.01, y+row_h/2, str(df.iloc[i,0]), va="center", ha="left", fontsize=9, transform=ax.transAxes)
        x = item_w
        for j in range(1, n_cols):
            ax.add_patch(Rectangle((x, y), date_w, row_h, fc="white", ec="black", lw=1))
            val = df.iloc[i, j]
            txt = "" if (pd.isna(val) or str(val)=="nan") else str(val)
            ax.text(x+date_w/2, y+row_h/2, txt, va="center", ha="center", fontsize=9, transform=ax.transAxes)
            x += date_w

def fig_from_table(df: pd.DataFrame, title: str):
    n_cols = len(df.columns)
    n_rows = len(df) + 1
    w = max(14, n_cols * 0.7)      # 列数に応じて横幅拡張
    h = max(3.5, n_rows * 0.35)
    fig, ax = plt.subplots(figsize=(w, h))
    draw_table(ax, df, title)
    fig.tight_layout(rect=[0.02, 0.02, 0.98, 0.98])
    return fig

def pdf_bytes_single(df: pd.DataFrame, title: str) -> bytes:
    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        fig = fig_from_table(df, title)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)
    return buf.getvalue()

def pdf_bytes_two(df_top: pd.DataFrame, title_top: str, df_bottom: pd.DataFrame, title_bottom: str) -> bytes:
    # 1ページに上下2表
    n_cols = max(len(df_top.columns), len(df_bottom.columns))
    w = max(14, n_cols * 0.7)
    h = 8
    fig, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, figsize=(w, h))
    draw_table(ax1, df_top, title_top)
    draw_table(ax2, df_bottom, title_bottom)
    fig.tight_layout(rect=[0.02, 0.02, 0.98, 0.98])

    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)
    return buf.getvalue()

# ===== 画面 =====
init_state_once()
st.title(APP_TITLE)

left, right = st.columns([3,2])
with left:
    project_name = st.text_input("案件名（PDFタイトルに使用）", value="")
with right:
    st.caption("列数は自由。ヘッダーに日付（例: 9/5, 9/7, 9/10…）を横に入力 → セルへ「■」「10:00」等を記入 → PDF出力")

tab_p, tab_s, tab_r = st.tabs(["🏠 購入", "🏢 売却", "🔄 買い替え（上下2段）"])

# --- 購入 ---
with tab_p:
    st.subheader("購入：横テーブル編集（列数は数値で調整可 / 上限50）")
    render_editor(st.session_state.roadmap["purchase"], key_prefix="p")
    if st.button("📄 PDF出力（購入）", use_container_width=True, key="btn_pdf_p"):
        df = to_dataframe(st.session_state.roadmap["purchase"])
        pdf_data = pdf_bytes_single(df, (project_name or "購入ロードマップ（購入）"))
        st.download_button("📥 ダウンロード（購入PDF）", data=pdf_data,
                           file_name=f"{(project_name or '購入ロードマップ')}_購入.pdf",
                           mime="application/pdf", use_container_width=True)

# --- 売却 ---
with tab_s:
    st.subheader("売却：横テーブル編集（列数は数値で調整可 / 上限50）")
    render_editor(st.session_state.roadmap["sale"], key_prefix="s")
    if st.button("📄 PDF出力（売却）", use_container_width=True, key="btn_pdf_s"):
        df = to_dataframe(st.session_state.roadmap["sale"])
        pdf_data = pdf_bytes_single(df, (project_name or "売却ロードマップ（売却）"))
        st.download_button("📥 ダウンロード（売却PDF）", data=pdf_data,
                           file_name=f"{(project_name or '売却ロードマップ')}_売却.pdf",
                           mime="application/pdf", use_container_width=True)

# --- 買い替え ---
with tab_r:
    st.subheader("買い替え：上＝購入／下＝売却（2表を同ページ）※列数は各表で独立調整")
    st.markdown("**上段：購入**")
    render_editor(st.session_state.roadmap["replace"]["up"], key_prefix="r_up")
    st.markdown("---")
    st.markdown("**下段：売却**")
    render_editor(st.session_state.roadmap["replace"]["down"], key_prefix="r_down")
    if st.button("📄 PDF出力（買い替え・上下2段）", use_container_width=True, key="btn_pdf_r"):
        df_top    = to_dataframe(st.session_state.roadmap["replace"]["up"])
        df_bottom = to_dataframe(st.session_state.roadmap["replace"]["down"])
        pdf_data = pdf_bytes_two(df_top, "購入", df_bottom, "売却")
        st.download_button("📥 ダウンロード（買い替えPDF）", data=pdf_data,
                           file_name=f"{(project_name or '買い替えロードマップ')}_購入_売却.pdf",
                           mime="application/pdf", use_container_width=True)