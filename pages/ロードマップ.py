# pages/7_ロードマップ.py
# 縦=項目 / 横=日付 の横テーブル編集＋PDF出力（購入 / 売却 / 買い替え）
# 依存: streamlit, pandas, matplotlib のみ（ReportLab不要）
from pathlib import Path
from datetime import datetime
from typing import Dict
import io

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle

# ========== 基本設定 ==========
st.set_page_config(page_title="ロードマップ（横テーブル）", page_icon="🗓️", layout="wide")
APP_TITLE = "不動産ロードマップ（横テーブル：縦=項目／横=日付）"

# 日本語フォント（任意配置）
FONT_PATH = Path("fonts/NotoSansJP-Regular.ttf")
if FONT_PATH.exists():
    try:
        matplotlib.font_manager.fontManager.addfont(str(FONT_PATH))
        plt.rcParams["font.family"] = matplotlib.font_manager.FontProperties(fname=str(FONT_PATH)).get_name()
    except Exception:
        pass  # 失敗しても英字フォントで継続

# ========== 初期行 ==========
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

# ========== State ==========
def init_state_once():
    if "roadmap" in st.session_state:
        return
    st.session_state.roadmap = dict(
        purchase=dict(
            col_count=6,
            headers=[""] * 6,  # 例: 9/5, 9/7, 9/10 …
            rows=[{"項目": x, "cells": [""] * 6} for x in PURCHASE_ITEMS_DEFAULT],
        ),
        sale=dict(
            col_count=6,
            headers=[""] * 6,
            rows=[{"項目": x, "cells": [""] * 6} for x in SALE_ITEMS_DEFAULT],
        ),
        replace=dict(  # 買い替え：上下2段（別表）
            up=dict(
                col_count=6, headers=[""] * 6,
                rows=[{"項目": x, "cells": [""] * 6} for x in REPLACE_PURCHASE_ITEMS_DEFAULT],
            ),
            down=dict(
                col_count=6, headers=[""] * 6,
                rows=[{"項目": x, "cells": [""] * 6} for x in REPLACE_SALE_ITEMS_DEFAULT],
            ),
        )
    )

# ========== 共通：編集UI ==========
def add_column(block: Dict):
    block["col_count"] += 1
    block["headers"].append("")
    for r in block["rows"]:
        r["cells"].append("")

def remove_last_column(block: Dict):
    if block["col_count"] <= 1:
        return
    block["col_count"] -= 1
    block["headers"] = block["headers"][: block["col_count"]]
    for r in block["rows"]:
        r["cells"] = r["cells"][: block["col_count"]]

def add_row(block: Dict, label_default="新規項目"):
    block["rows"].append({"項目": label_default, "cells": [""] * block["col_count"]})

def delete_row(block: Dict, idx: int):
    if 0 <= idx < len(block["rows"]):
        block["rows"].pop(idx)

def render_editor(block: Dict, key_prefix: str):
    # 列操作
    c1, c2, c3 = st.columns([1,1,8])
    with c1:
        if st.button("＋列追加", key=f"{key_prefix}_addcol"):
            add_column(block)
    with c2:
        if st.button("－列削除", key=f"{key_prefix}_delcol"):
            remove_last_column(block)
    with c3:
        st.caption("ヘッダー（日付）は自由入力：例 9/5, 9/7, 9/10。セルは「■」「10:00」等を記入。")

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

# ========== 描画（Matplotlib でPDF） ==========
def draw_table(ax, df: pd.DataFrame, title: str):
    """
    Matplotlibで表を手描き（日本語対応／塗り無し）
    - 1列目が『項目』。以降はヘッダー（日付）
    """
    ax.clear()
    ax.axis("off")

    n_rows = len(df) + 1          # +1 = ヘッダー行
    n_cols = len(df.columns)

    # レイアウト
    item_w_ratio = 0.22
    width = 1.0
    item_w = item_w_ratio * width
    date_w = (width - item_w) / max(1, n_cols-1)
    row_h = 1.0 / n_rows

    # タイトル
    ax.text(0, 1.02, title, ha="left", va="bottom", fontsize=12, transform=ax.transAxes)

    # ヘッダー背景
    y = 1 - row_h
    # 項目ヘッダー
    ax.add_patch(Rectangle((0, y), item_w, row_h, fill=True, fc=(0.92,0.92,0.92), ec="black", lw=1))
    ax.text(0.01, y + row_h/2, str(df.columns[0]), va="center", ha="left", fontsize=9, transform=ax.transAxes)
    # 日付ヘッダー
    x = item_w
    for j in range(1, n_cols):
        ax.add_patch(Rectangle((x, y), date_w, row_h, fill=True, fc=(0.92,0.92,0.92), ec="black", lw=1))
        hdr = "" if pd.isna(df.columns[j]) else str(df.columns[j])
        ax.text(x + 0.01, y + row_h/2, hdr, va="center", ha="left", fontsize=9, transform=ax.transAxes)
        x += date_w

    # 本体
    for i in range(len(df)):
        y = 1 - row_h*(i+2)
        # 項目セル
        ax.add_patch(Rectangle((0, y), item_w, row_h, fill=False, ec="black", lw=1))
        ax.text(0.01, y + row_h/2, str(df.iloc[i,0]), va="center", ha="left", fontsize=9, transform=ax.transAxes)
        # 日付セル
        x = item_w
        for j in range(1, n_cols):
            ax.add_patch(Rectangle((x, y), date_w, row_h, fill=False, ec="black", lw=1))
            val = df.iloc[i, j]
            txt = "" if (pd.isna(val) or str(val)=="nan") else str(val)
            # 中央配置（短い文字想定：■/時刻/短文）
            ax.text(x + date_w/2, y + row_h/2, txt, va="center", ha="center", fontsize=9, transform=ax.transAxes)
            x += date_w

def fig_from_table(df: pd.DataFrame, title: str):
    # 見やすさ：列×行に応じてサイズ可変
    n_cols = len(df.columns)
    n_rows = len(df) + 1
    w = max(12, n_cols * 1.0)
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
    # 1ページに上下2表を配置
    top_rows = len(df_top) + 1
    bottom_rows = len(df_bottom) + 1
    n_cols = max(len(df_top.columns), len(df_bottom.columns))
    w = max(12, n_cols * 1.0)
    h = max(6, (top_rows + bottom_rows) * 0.28 + 1.0)  # ざっくり
    fig, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, figsize=(w, h))
    draw_table(ax1, df_top, title_top)
    draw_table(ax2, df_bottom, title_bottom)
    fig.tight_layout(rect=[0.02, 0.02, 0.98, 0.98])

    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)
    return buf.getvalue()

# ========== 画面 ==========
init_state_once()
st.title(APP_TITLE)

left, right = st.columns([3,2])
with left:
    project_name = st.text_input("案件名（PDFタイトルに使用）", value="")
with right:
    st.caption("ヘッダーに日付（例: 9/5, 9/7, 9/10…）を横に入力 → セルへ「■」「10:00」等を記入 → PDF出力")

tab_p, tab_s, tab_r = st.tabs(["🏠 購入", "🏢 売却", "🔄 買い替え（上下2段）"])

# --- 購入 ---
with tab_p:
    st.subheader("購入：横テーブル編集")
    render_editor(st.session_state.roadmap["purchase"], key_prefix="p")
    if st.button("📄 PDF出力（購入）", use_container_width=True, key="btn_pdf_p"):
        df = to_dataframe(st.session_state.roadmap["purchase"])
        pdf_data = pdf_bytes_single(df, (project_name or "購入ロードマップ（購入）"))
        st.download_button("📥 ダウンロード（購入PDF）", data=pdf_data,
                           file_name=f"{(project_name or '購入ロードマップ')}_購入.pdf",
                           mime="application/pdf", use_container_width=True)

# --- 売却 ---
with tab_s:
    st.subheader("売却：横テーブル編集")
    render_editor(st.session_state.roadmap["sale"], key_prefix="s")
    if st.button("📄 PDF出力（売却）", use_container_width=True, key="btn_pdf_s"):
        df = to_dataframe(st.session_state.roadmap["sale"])
        pdf_data = pdf_bytes_single(df, (project_name or "売却ロードマップ（売却）"))
        st.download_button("📥 ダウンロード（売却PDF）", data=pdf_data,
                           file_name=f"{(project_name or '売却ロードマップ')}_売却.pdf",
                           mime="application/pdf", use_container_width=True)

# --- 買い替え（上下2段・別表を同一ページに配置） ---
with tab_r:
    st.subheader("買い替え：上＝購入／下＝売却（別テーブル・同一ページ）")
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