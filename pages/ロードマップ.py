# pages/7_ロードマップ.py
# 縦=項目 / 横=日付 の横テーブル（購入 / 売却 / 買い替え）
# ヘッダーは「日付ピッカー（カレンダー）」で選択。PDFは Matplotlib 出力（ReportLab不要）。
from pathlib import Path
from datetime import datetime, date
from typing import Dict
import io

import streamlit as st
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle

# ========== 基本設定 ==========
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

# ========== 初期データ ==========
PURCHASE_ITEMS_DEFAULT = [
    "問合せ", "初回面談", "ライフプランニング", "条件整理", "事前審査",
    "内見①", "内見②", "内見③",
    "売買契約", "本申込", "金消契約", "決済（引渡し）",
]
SALE_ITEMS_DEFAULT = [
    "問合せ", "初回面談",
    "売出価格査定", "買取保証査定", "訪問査定",
    "媒介契約", "ポータルサイト掲載", "レインズ掲載",
    "内見",
    "売買契約", "本申込", "金消契約", "決済（引渡し）",
]
REPLACE_PURCHASE_ITEMS_DEFAULT = ["内見①", "内見②", "売買契約", "決済（引渡し）"]
REPLACE_SALE_ITEMS_DEFAULT     = ["媒介契約", "内見", "売買契約", "決済（引渡し）"]

DEFAULT_COLS = 13  # ★ デフォルト13列
MAX_COLS     = 50

# ========== ヘルパ ==========
def iso_or_empty(d: date | None) -> str:
    return d.isoformat() if isinstance(d, date) else ""

def parse_iso(s: str) -> date | None:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None

def fmt_md(s: str) -> str:
    """ヘッダー表示用（M/D）"""
    d = parse_iso(s)
    if not d:
        return ""
    # Linux/Mac: %-m/%-d, Windows: %#m/%#d
    try:
        return d.strftime("%-m/%-d")
    except Exception:
        return d.strftime("%#m/%#d")

# ========== State ==========
def init_state_once():
    if "roadmap" in st.session_state:
        return
    def _block(rows_src):
        return dict(
            col_count=DEFAULT_COLS,
            headers=[""] * DEFAULT_COLS,  # ISO文字列 "YYYY-MM-DD" を保持（空なら未設定）
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

# ========== 共通UI ==========
def resize_columns(block: Dict, new_count: int):
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

def render_editor(block: Dict, key_prefix: str, caption_text: str = ""):
    # 列数
    c1, c2, c3 = st.columns([2, 2, 6])
    with c1:
        desired = st.number_input("列数（日付の数）", 1, MAX_COLS, int(block["col_count"]), 1, key=f"{key_prefix}_cols")
    with c2:
        if st.button("列数を反映", key=f"{key_prefix}_cols_apply"):
            resize_columns(block, desired)
            st.rerun()
    with c3:
        st.caption(caption_text or "ヘッダーは日付ピッカー（クリックでカレンダー）。セルは「■」「10:00」など自由記入。")

    # ヘッダー（日付ピッカー）
    st.markdown("**ヘッダー（日付）**")
    heads = st.columns([2] + [1] * block["col_count"])
    heads[0].markdown("**項目**")
    for i in range(block["col_count"]):
        cur = parse_iso(block["headers"][i]) or date.today()
        picked = heads[i+1].date_input(
            " ", value=cur, key=f"{key_prefix}_hdr_{i},date", format="YYYY-MM-DD"
        )
        # クリアボタン
        if heads[i+1].button("×", key=f"{key_prefix}_hdr_clear_{i}"):
            block["headers"][i] = ""
        else:
            block["headers"][i] = iso_or_empty(picked)

    st.write("---")

    # 行追加/削除
    a1, a2, _ = st.columns([1,1,8])
    with a1:
        if st.button("＋行追加", key=f"{key_prefix}_addrow"):
            add_row(block)
    with a2:
        st.caption("行末の🗑で削除")

    # 本体（縦=項目、横=日付）
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
    headers = ["項目"] + [fmt_md(h) for h in block["headers"]]
    data = [[r["項目"], *r["cells"]] for r in block["rows"]]
    return pd.DataFrame(data, columns=headers)

# ========== PDF化（Matplotlib） ==========
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
    y = 1 - row_h
    ax.add_patch(Rectangle((0, y), item_w, row_h, fc=(0.92,0.92,0.92), ec="black", lw=1))
    ax.text(0.01, y + row_h/2, str(df.columns[0]), va="center", ha="left", fontsize=9, transform=ax.transAxes)
    x = item_w
    for j in range(1, n_cols):
        ax.add_patch(Rectangle((x, y), date_w, row_h, fc=(0.92,0.92,0.92), ec="black", lw=1))
        hdr = "" if pd.isna(df.columns[j]) else str(df.columns[j])
        ax.text(x + date_w/2, y + row_h/2, hdr, va="center", ha="center", fontsize=9, transform=ax.transAxes)
        x += date_w

    # 本体
    for i in range(len(df)):
        y = 1 - row_h*(i+2)
        ax.add_patch(Rectangle((0, y), item_w, row_h, fc="white", ec="black", lw=1))
        ax.text(0.01, y + row_h/2, str(df.iloc[i, 0]), va="center", ha="left", fontsize=9, transform=ax.transAxes)
        x = item_w
        for j in range(1, n_cols):
            ax.add_patch(Rectangle((x, y), date_w, row_h, fc="white", ec="black", lw=1))
            val = df.iloc[i, j]
            txt = "" if (pd.isna(val) or str(val) == "nan") else str(val)
            ax.text(x + date_w/2, y + row_h/2, txt, va="center", ha="center", fontsize=9, transform=ax.transAxes)
            x += date_w

def fig_from_table(df: pd.DataFrame, title: str):
    n_cols = len(df.columns)
    n_rows = len(df) + 1
    w = max(14, n_cols * 0.7)      # 列数に応じて横幅可変
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

# ========== 画面 ==========
init_state_once()
st.title(APP_TITLE)

left, right = st.columns([3, 2])
with left:
    project_name = st.text_input("案件名（PDFタイトル）", value="")
with right:
    st.caption("デフォルト13列。ヘッダーはクリックでカレンダー選択（M/D表示）。")

tab_p, tab_s, tab_r = st.tabs(["🏠 購入", "🏢 売却", "🔄 買い替え（上下2段）"])

# --- 購入 ---
with tab_p:
    st.subheader("購入：横テーブル編集（ヘッダーは日付ピッカー）")
    render_editor(st.session_state.roadmap["purchase"], key_prefix="p")
    if st.button("📄 PDF出力（購入）", use_container_width=True, key="btn_pdf_p"):
        df = to_dataframe(st.session_state.roadmap["purchase"])
        pdf_data = pdf_bytes_single(df, (project_name or "購入ロードマップ（購入）"))
        st.download_button("📥 ダウンロード（購入PDF）", data=pdf_data,
                           file_name=f"{(project_name or '購入ロードマップ')}_購入.pdf",
                           mime="application/pdf", use_container_width=True)

# --- 売却 ---
with tab_s:
    st.subheader("売却：横テーブル編集（ヘッダーは日付ピッカー）")
    render_editor(st.session_state.roadmap["sale"], key_prefix="s")
    if st.button("📄 PDF出力（売却）", use_container_width=True, key="btn_pdf_s"):
        df = to_dataframe(st.session_state.roadmap["sale"])
        pdf_data = pdf_bytes_single(df, (project_name or "売却ロードマップ（売却）"))
        st.download_button("📥 ダウンロード（売却PDF）", data=pdf_data,
                           file_name=f"{(project_name or '売却ロードマップ')}_売却.pdf",
                           mime="application/pdf", use_container_width=True)

# --- 買い替え（上下2段） ---
with tab_r:
    st.subheader("買い替え：上＝購入／下＝売却（2表を同ページにPDF化）")
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