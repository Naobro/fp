# pages/7_ロードマップ.py
# 縦=項目 / 横=日付セル（セル=カレンダーのみ／クリアボタンなし）
# 購入(20行) / 売却(30行) / 買い替え(30行×2段)
# 依存: streamlit, pandas, matplotlib
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

# ---------- 基本 ----------
st.set_page_config(page_title="ロードマップ（横テーブル）", page_icon="🗓️", layout="wide")
APP_TITLE = "不動産ロードマップ（縦=項目／横=日付セル）"

# 日本語フォント（任意配置：fonts/NotoSansJP-Regular.ttf）
FONT_PATH = Path("fonts/NotoSansJP-Regular.ttf")
if FONT_PATH.exists():
    try:
        matplotlib.font_manager.fontManager.addfont(str(FONT_PATH))
        plt.rcParams["font.family"] = matplotlib.font_manager.FontProperties(
            fname=str(FONT_PATH)
        ).get_name()
    except Exception:
        pass

# ---------- 初期データ ----------
# 購入：20行
PURCHASE_ITEMS_DEFAULT_20 = [
    "問合せ",
    "初回面談",
    "ライフプランニング",
    "条件整理",
    "事前審査",
    "物件提案",
    "内見①",
    "内見②",
    "内見③",
    "価格交渉",
    "購入申込（買付証明）",
    "事前承認確認（ローン）",
    "売買契約",
    "本申込（ローン）",
    "ローン審査承認",
    "金消契約",
    "引越し準備・火災保険見積",
    "最終確認・立会い",
    "決済（引渡し）",
    "アフター手続き",
]

# 売却：指示（28）＋ 予備2件 ＝ 30行
SALE_ITEMS_DEFAULT_30 = [
    "相談",
    "物件情報整理　",
    "相続・共有・抵当権など権利関係の整理",
    "境界・測量・解体",
    "付帯設備表・物件状況確認",
    "机上査定",
    "訪問査定",
    "写真撮影",
    "売出価格確定",
    "買取保証価格確定",
    "販売戦略",
    "媒介契約",
    "抵当権抹消書類の準備",
    "精算金確認",
    "固定資産税・管理費等",
    "販売活動",
    "TERASS内　共有",
    "ポータルサイト掲載",
    "レインズ掲載",
    "内見可能日",
    "購入申込",
    "条件整理",
    "売買契約",
    "必要書類準備　",
    "ライフライン解約・郵便転送・火災保険解約手続スケジュール",
    "引越し",
    "決済引き渡し",
    "税務相談案内（譲渡所得・3,000万円控除 等に該当する場合）",
    "（予備）1",
    "（予備）2",
]

# 買い替え：上段=購入30行、下段=売却30行
REPLACE_PURCHASE_ITEMS_DEFAULT_30 = PURCHASE_ITEMS_DEFAULT_20 + [
    "（予備）21", "（予備）22", "（予備）23", "（予備）24", "（予備）25",
    "（予備）26", "（予備）27", "（予備）28", "（予備）29", "（予備）30",
]
REPLACE_SALE_ITEMS_DEFAULT_30 = SALE_ITEMS_DEFAULT_30.copy()

DEFAULT_COLS = 13      # 横の“日付枠”デフォルト
MAX_COLS     = 50

# ---------- ヘルパ ----------
def iso_or_empty(d: date | None) -> str:
    return d.isoformat() if isinstance(d, date) else ""

def parse_iso(s: str) -> date | None:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None

def md_jp(s: str) -> str:
    """PDF/表の表示: '9月12日'"""
    d = parse_iso(s)
    if not d:
        return ""
    return f"{d.month}月{d.day}日"

# ---------- State ----------
def init_state_once():
    if "roadmap" in st.session_state:
        return

    def _block(rows_src):
        return dict(
            col_count=DEFAULT_COLS,
            headers=[""] * DEFAULT_COLS,  # 見出しは使わない（空のまま）
            rows=[{"項目": name, "cells": [""] * DEFAULT_COLS} for name in rows_src],  # 各セル=ISO日付文字列
        )

    st.session_state.roadmap = dict(
        purchase=_block(PURCHASE_ITEMS_DEFAULT_20),
        sale=_block(SALE_ITEMS_DEFAULT_30),
        replace=dict(
            up=_block(REPLACE_PURCHASE_ITEMS_DEFAULT_30),
            down=_block(REPLACE_SALE_ITEMS_DEFAULT_30),
        ),
    )

# ---------- 共通UI ----------
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

def render_editor(block: Dict, key_prefix: str, note: str = ""):
    # 列数
    c1, c2, c3 = st.columns([2, 2, 6])
    with c1:
        desired = st.number_input("列数（横の枠の数）", 1, MAX_COLS, int(block["col_count"]), 1, key=f"{key_prefix}_cols")
    with c2:
        if st.button("列数を反映", key=f"{key_prefix}_cols_apply"):
            resize_columns(block, desired)
            st.rerun()
    with c3:
        st.caption(note or "各セルをクリック→カレンダーで日付を選ぶ（×は表示しません）。")

    st.write("---")

    # 行の追加/削除
    a1, a2, _ = st.columns([1, 1, 8])
    with a1:
        if st.button("＋行追加", key=f"{key_prefix}_addrow"):
            add_row(block)
    with a2:
        st.caption("行末の🗑で削除")

    # 本体（セル= date_input のみ）
    for r_idx, row in enumerate(block["rows"]):
        cols = st.columns([2] + [1] * block["col_count"] + [0.6])
        # 左端：項目名
        row["項目"] = cols[0].text_input(" ", value=row["項目"], key=f"{key_prefix}_item_{r_idx}")

        # 右側：各セル= date_input（クリアボタンなし）
        for c_idx in range(block["col_count"]):
            with cols[c_idx + 1]:
                cur = parse_iso(row["cells"][c_idx])  # Noneなら空欄（内部は空文字）
                picked = st.date_input(
                    " ", value=cur, key=f"{key_prefix}_cell_date_{r_idx}_{c_idx}",
                    format="YYYY-MM-DD"
                )
                row["cells"][c_idx] = iso_or_empty(picked)

        # 行削除
        if cols[-1].button("🗑", key=f"{key_prefix}_delrow_{r_idx}"):
            delete_row(block, r_idx)
            st.rerun()

def to_dataframe(block: Dict) -> pd.DataFrame:
    # ヘッダーは空欄列（左端は「項目」）
    headers = ["項目"] + [""] * block["col_count"]
    data = [[r["項目"], *[md_jp(x) for x in r["cells"]]] for r in block["rows"]]
    return pd.DataFrame(data, columns=headers)

# ---------- PDF（Matplotlib） ----------
def draw_table(ax, df: pd.DataFrame, title: str):
    ax.clear(); ax.axis("off")
    n_rows = len(df) + 1
    n_cols = len(df.columns)

    # レイアウト
    item_w_ratio = 0.22
    width = 1.0
    item_w = item_w_ratio * width
    date_w = (width - item_w) / max(1, n_cols - 1)
    row_h = 1.0 / n_rows

    # タイトル
    ax.text(0, 1.02, title, ha="left", va="bottom", fontsize=12, transform=ax.transAxes)

    # ヘッダー（空欄）
    y = 1 - row_h
    ax.add_patch(Rectangle((0, y), item_w, row_h, fc=(0.92, 0.92, 0.92), ec="black", lw=1))
    ax.text(0.01, y + row_h / 2, str(df.columns[0] or "項目"), va="center", ha="left", fontsize=9, transform=ax.transAxes)
    x = item_w
    for j in range(1, n_cols):
        ax.add_patch(Rectangle((x, y), date_w, row_h, fc=(0.92, 0.92, 0.92), ec="black", lw=1))
        x += date_w

    # 本体
    for i in range(len(df)):
        y = 1 - row_h * (i + 2)
        ax.add_patch(Rectangle((0, y), item_w, row_h, fc="white", ec="black", lw=1))
        ax.text(0.01, y + row_h / 2, str(df.iloc[i, 0]), va="center", ha="left", fontsize=9, transform=ax.transAxes)
        x = item_w
        for j in range(1, n_cols):
            ax.add_patch(Rectangle((x, y), date_w, row_h, fc="white", ec="black", lw=1))
            txt = str(df.iloc[i, j]) if pd.notna(df.iloc[i, j]) else ""
            if txt == "nan":
                txt = ""
            ax.text(x + date_w / 2, y + row_h / 2, txt, va="center", ha="center", fontsize=9, transform=ax.transAxes)
            x += date_w

def fig_from_table(df: pd.DataFrame, title: str):
    n_cols = len(df.columns)
    n_rows = len(df) + 1
    w = max(14, n_cols * 0.7)
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

# ---------- 画面 ----------
init_state_once()
st.title(APP_TITLE)

left, right = st.columns([3, 2])
with left:
    project_name = st.text_input("案件名（PDFタイトル）", value="")
with right:
    st.caption("購入=20行／売却=30行／買い替え=30行×2段。セルは日付入力のみ（×なし）。")

tab_p, tab_s, tab_r = st.tabs(["🏠 購入（20行）", "🏢 売却（30行）", "🔄 買い替え（30行×2段）"])

# --- 購入（20行） ---
with tab_p:
    st.subheader("購入：横テーブル（セル=カレンダー）")
    render_editor(st.session_state.roadmap["purchase"], key_prefix="p")
    if st.button("📄 PDF出力（購入）", use_container_width=True, key="btn_pdf_p"):
        df = to_dataframe(st.session_state.roadmap["purchase"])
        pdf_data = pdf_bytes_single(df, (project_name or "購入ロードマップ（購入）"))
        st.download_button("📥 ダウンロード（購入PDF）", data=pdf_data,
                           file_name=f"{(project_name or '購入ロードマップ')}_購入.pdf",
                           mime="application/pdf", use_container_width=True)

# --- 売却（30行） ---
with tab_s:
    st.subheader("売却：横テーブル（セル=カレンダー）")
    render_editor(st.session_state.roadmap["sale"], key_prefix="s")
    if st.button("📄 PDF出力（売却）", use_container_width=True, key="btn_pdf_s"):
        df = to_dataframe(st.session_state.roadmap["sale"])
        pdf_data = pdf_bytes_single(df, (project_name or "売却ロードマップ（売却）"))
        st.download_button("📥 ダウンロード（売却PDF）", data=pdf_data,
                           file_name=f"{(project_name or '売却ロードマップ')}_売却.pdf",
                           mime="application/pdf", use_container_width=True)

# --- 買い替え（30行×2段） ---
with tab_r:
    st.subheader("買い替え：上＝購入30行／下＝売却30行（同一ページPDF）")
    st.markdown("**上段：購入（30行）**")
    render_editor(st.session_state.roadmap["replace"]["up"], key_prefix="r_up")
    st.markdown("---")
    st.markdown("**下段：売却（30行）**")
    render_editor(st.session_state.roadmap["replace"]["down"], key_prefix="r_down")
    if st.button("📄 PDF出力（買い替え・上下2段）", use_container_width=True, key="btn_pdf_r"):
        df_up = to_dataframe(st.session_state.roadmap["replace"]["up"])
        df_dn = to_dataframe(st.session_state.roadmap["replace"]["down"])
        pdf_data = pdf_bytes_two(df_up, "購入（買い替え）", df_dn, "売却（買い替え）")
        st.download_button("📥 ダウンロード（買い替えPDF）", data=pdf_data,
                           file_name=f"{(project_name or '買い替えロードマップ')}_購入_売却.pdf",
                           mime="application/pdf", use_container_width=True)