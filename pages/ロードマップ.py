# pages/7_ロードマップ.py
# 5W2H：What=横テーブル型ロードマップ（縦=項目／横=日付）, Why=初回面談で次回以降を即確定→PDF共有, Who=なおき×顧客,
# When=面談時〜更新, Where=Streamlit, How=タブ編集→PDF出力, How much=費用管理なし
from pathlib import Path
from datetime import datetime
from typing import List, Dict

import streamlit as st
import pandas as pd

# --- PDF（ReportLab） ---
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ==============================
# 基本設定
# ==============================
st.set_page_config(page_title="ロードマップ（横テーブル）", page_icon="🗓️", layout="wide")

APP_TITLE = "不動産ロードマップ（横テーブル：縦=項目／横=日付）"
FONT_PATH = Path("fonts/NotoSansJP-Regular.ttf")
FONT_NAME = "NotoSansJP"

# フォント登録（無ければデフォルト）
if FONT_PATH.exists():
    try:
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))
        DEFAULT_FONT = FONT_NAME
    except Exception:
        DEFAULT_FONT = "Helvetica"
else:
    DEFAULT_FONT = "Helvetica"

# ==============================
# 初期データ
# ==============================
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

REPLACE_PURCHASE_ITEMS_DEFAULT = [
    "内見①", "内見②", "売買契約", "決済（引渡し）",
]
REPLACE_SALE_ITEMS_DEFAULT = [
    "媒介契約", "内見", "売買契約", "決済（引渡し）",
]

# ==============================
# ユーティリティ
# ==============================
def init_state_once():
    if "roadmap" not in st.session_state:
        st.session_state.roadmap = dict(
            purchase=dict(
                title="購入ロードマップ",
                col_count=6,
                headers=[""] * 6,  # 横の日付列（自由入力：例 9/5, 9/7, 9/10 …）
                rows=[{"項目": x, "cells": [""] * 6} for x in PURCHASE_ITEMS_DEFAULT],
            ),
            sale=dict(
                title="売却ロードマップ",
                col_count=6,
                headers=[""] * 6,
                rows=[{"項目": x, "cells": [""] * 6} for x in SALE_ITEMS_DEFAULT],
            ),
            replace=dict(
                title="買い替えロードマップ（上下2段：購入／売却）",
                # 上段（購入）
                up=dict(
                    label="購入",
                    col_count=6,
                    headers=[""] * 6,
                    rows=[{"項目": x, "cells": [""] * 6} for x in REPLACE_PURCHASE_ITEMS_DEFAULT],
                ),
                # 下段（売却）
                down=dict(
                    label="売却",
                    col_count=6,
                    headers=[""] * 6,
                    rows=[{"項目": x, "cells": [""] * 6} for x in REPLACE_SALE_ITEMS_DEFAULT],
                ),
            ),
        )

def add_column(block: Dict):
    block["col_count"] += 1
    block["headers"].append("")
    for r in block["rows"]:
        r["cells"].append("")

def remove_last_column(block: Dict):
    if block["col_count"] > 1:
        block["col_count"] -= 1
        block["headers"] = block["headers"][: block["col_count"]]
        for r in block["rows"]:
            r["cells"] = r["cells"][: block["col_count"]]

def add_row(block: Dict, label_default: str = "新規項目"):
    block["rows"].append({"項目": label_default, "cells": [""] * block["col_count"]})

def delete_row(block: Dict, idx: int):
    if 0 <= idx < len(block["rows"]):
        block["rows"].pop(idx)

def render_horizontal_table_editor(block: Dict, key_prefix: str):
    """
    横テーブル編集UI（縦＝項目、横＝日付ヘッダ）。セルは自由入力（■/時間/メモなど）。
    """
    colA, colB, colC = st.columns([1, 1, 8], vertical_alignment="center")
    with colA:
        if st.button("＋列追加", key=f"{key_prefix}_addcol"):
            add_column(block)
    with colB:
        if st.button("－列削除", key=f"{key_prefix}_delcol"):
            remove_last_column(block)
    with colC:
        st.caption("※ ヘッダー（日付）は自由入力：例 `9/5`, `9/7`, `9/10` など。セルは「■」「10:00」など自由記入。")

    # ヘッダー編集（横に日付を並べる）
    st.write("**ヘッダー（日付）**")
    header_cols = st.columns([2] + [1] * block["col_count"])
    header_cols[0].markdown("**項目**")
    for i in range(block["col_count"]):
        block["headers"][i] = header_cols[i + 1].text_input(
            label=" ",
            value=block["headers"][i],
            key=f"{key_prefix}_hdr_{i}",
            placeholder=f"9/{5+i}",
        )

    st.write("---")

    # 本体テーブル（縦＝項目、横＝日付）
    # 行追加・削除ボタン
    act_cols = st.columns([1, 1, 8])
    with act_cols[0]:
        if st.button("＋行追加", key=f"{key_prefix}_addrow"):
            add_row(block)
    with act_cols[1]:
        st.caption("行末の🗑で削除")

    # 各行レンダリング
    for r_idx, row in enumerate(block["rows"]):
        row_cols = st.columns([2] + [1] * block["col_count"] + [0.5])
        # 項目名
        row["項目"] = row_cols[0].text_input(" ", value=row["項目"], key=f"{key_prefix}_item_{r_idx}")
        # セル群（横方向）
        for c_idx in range(block["col_count"]):
            row["cells"][c_idx] = row_cols[c_idx + 1].text_input(
                " ",
                value=row["cells"][c_idx],
                key=f"{key_prefix}_cell_{r_idx}_{c_idx}",
                placeholder="",
            )
        # 削除
        if row_cols[-1].button("🗑", key=f"{key_prefix}_delrow_{r_idx}"):
            delete_row(block, r_idx)
            st.experimental_rerun()

def to_dataframe(block: Dict]) -> pd.DataFrame:
    """ReportLab描画用に DataFrame 化（1行目ヘッダ：項目 + 日付ヘッダ）"""
    headers = ["項目"] + block["headers"]
    data = []
    for row in block["rows"]:
        data.append([row["項目"]] + row["cells"])
    df = pd.DataFrame(data, columns=headers)
    return df

def draw_table_on_canvas(c: canvas.Canvas, df: pd.DataFrame, title: str, x_margin=28, y_start=520, row_h=20, font_size=9):
    """
    ReportLabで横テーブルを描画。
    - df列：1列目=「項目」、以降=日付ヘッダ
    - セルは文字列のまま（塗り無し）
    """
    page_w, page_h = landscape(A4)

    # タイトル
    c.setFont(DEFAULT_FONT, 12 if DEFAULT_FONT != "Helvetica" else 11)
    c.drawString(x_margin, y_start + 30, title)

    # テーブル領域計算
    col_count = len(df.columns)
    usable_w = page_w - x_margin * 2
    # 項目列は広め、日付列は均等
    item_col_w = max(120, int(usable_w * 0.22))
    other_w = usable_w - item_col_w
    date_col_w = max(60, int(other_w / (col_count - 1))) if col_count > 1 else 80

    # ヘッダ行
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.setFont(DEFAULT_FONT, font_size)
    # ヘッダ背景（薄グレー）
    c.setFillColorRGB(0.92, 0.92, 0.92)
    c.rect(x_margin, y_start, item_col_w, row_h, stroke=1, fill=1)
    c.setFillColor(colors.black)
    c.drawString(x_margin + 4, y_start + 5, str(df.columns[0]))

    x = x_margin + item_col_w
    for j in range(1, col_count):
        c.setFillColorRGB(0.92, 0.92, 0.92)
        c.rect(x, y_start, date_col_w, row_h, stroke=1, fill=1)
        c.setFillColor(colors.black)
        hdr = str(df.columns[j]) if df.columns[j] else ""
        c.drawString(x + 4, y_start + 5, hdr)
        x += date_col_w

    # 本体行
    y = y_start - row_h
    for i in range(len(df)):
        # 項目セル
        c.setFillColor(colors.white)
        c.rect(x_margin, y, item_col_w, row_h, stroke=1, fill=1)
        c.setFillColor(colors.black)
        c.drawString(x_margin + 4, y + 5, str(df.iloc[i, 0]))

        # 日付セル群
        x = x_margin + item_col_w
        for j in range(1, col_count):
            c.setFillColor(colors.white)
            c.rect(x, y, date_col_w, row_h, stroke=1, fill=1)
            c.setFillColor(colors.black)
            txt = str(df.iloc[i, j]) if pd.notna(df.iloc[i, j]) else ""
            if txt == "nan":
                txt = ""
            c.drawString(x + 4, y + 5, txt)
            x += date_col_w

        y -= row_h

def export_pdf_purchase(roadmap: Dict, filename: str, project_name: str):
    """購入タブPDF：1ページ"""
    page_w, page_h = landscape(A4)
    c = canvas.Canvas(filename, pagesize=landscape(A4))
    c.setTitle(project_name or "購入ロードマップ")

    # ヘッダ
    c.setFont(DEFAULT_FONT, 13 if DEFAULT_FONT != "Helvetica" else 12)
    c.drawString(28, page_h - 30, f"{project_name or '購入ロードマップ'}（購入）")
    c.setFont(DEFAULT_FONT, 9)
    c.drawRightString(page_w - 28, page_h - 30, datetime.now().strftime("%Y-%m-%d %H:%M"))

    df = to_dataframe(roadmap["purchase"])
    draw_table_on_canvas(c, df, title="", x_margin=28, y_start=page_h - 70, row_h=22, font_size=9)

    c.showPage()
    c.save()

def export_pdf_sale(roadmap: Dict, filename: str, project_name: str):
    """売却タブPDF：1ページ"""
    page_w, page_h = landscape(A4)
    c = canvas.Canvas(filename, pagesize=landscape(A4))
    c.setTitle(project_name or "売却ロードマップ")

    c.setFont(DEFAULT_FONT, 13 if DEFAULT_FONT != "Helvetica" else 12)
    c.drawString(28, page_h - 30, f"{project_name or '売却ロードマップ'}（売却）")
    c.setFont(DEFAULT_FONT, 9)
    c.drawRightString(page_w - 28, page_h - 30, datetime.now().strftime("%Y-%m-%d %H:%M"))

    df = to_dataframe(roadmap["sale"])
    draw_table_on_canvas(c, df, title="", x_margin=28, y_start=page_h - 70, row_h=22, font_size=9)

    c.showPage()
    c.save()

def export_pdf_replace(roadmap: Dict, filename: str, project_name: str):
    """買い替えPDF：1ページ内に 上=購入 下=売却 を上下2段で描画"""
    page_w, page_h = landscape(A4)
    c = canvas.Canvas(filename, pagesize=landscape(A4))
    c.setTitle(project_name or "買い替えロードマップ")

    c.setFont(DEFAULT_FONT, 13 if DEFAULT_FONT != "Helvetica" else 12)
    c.drawString(28, page_h - 30, f"{project_name or '買い替えロードマップ'}（購入・売却）")
    c.setFont(DEFAULT_FONT, 9)
    c.drawRightString(page_w - 28, page_h - 30, datetime.now().strftime("%Y-%m-%d %H:%M"))

    # 上段：購入
    up_df = to_dataframe(st.session_state.roadmap["replace"]["up"])
    draw_table_on_canvas(c, up_df, title="購入", x_margin=28, y_start=page_h - 80, row_h=20, font_size=9)

    # 下段：売却
    down_df = to_dataframe(st.session_state.roadmap["replace"]["down"])
    draw_table_on_canvas(c, down_df, title="売却", x_margin=28, y_start=page_h - 280, row_h=20, font_size=9)

    c.showPage()
    c.save()

# ==============================
# 画面
# ==============================
init_state_once()
st.title(APP_TITLE)

col_top1, col_top2 = st.columns([3, 2])
with col_top1:
    project_name = st.text_input("案件名（PDFタイトルに使用）", value="")
with col_top2:
    st.caption("操作：ヘッダーに日付（例 9/5, 9/7, 9/10 …）を入力 → セルに「■」「10:00」など自由記入 → PDF出力")

tab1, tab2, tab3 = st.tabs(["🏠 購入", "🏢 売却", "🔄 買い替え（上下2段）"])

# --- 購入 ---
with tab1:
    st.subheader("購入：横テーブル編集")
    render_horizontal_table_editor(st.session_state.roadmap["purchase"], key_prefix="p")
    pdf_name = f"{project_name or '購入ロードマップ'}_購入.pdf"
    if st.button("📄 PDF出力（購入）", use_container_width=True, key="btn_pdf_purchase"):
        tmp = Path(st.runtime.scriptrunner.script_run_context.get_script_run_ctx().session_id + "_purchase.pdf") if hasattr(st, "runtime") else Path("purchase.pdf")
        filename = str(Path("purchase.pdf"))
        export_pdf_purchase(st.session_state.roadmap, filename, project_name or "購入ロードマップ")
        with open(filename, "rb") as f:
            st.download_button("📥 ダウンロード（購入PDF）", data=f.read(), file_name=pdf_name, mime="application/pdf", use_container_width=True)

# --- 売却 ---
with tab2:
    st.subheader("売却：横テーブル編集")
    render_horizontal_table_editor(st.session_state.roadmap["sale"], key_prefix="s")
    pdf_name = f"{project_name or '売却ロードマップ'}_売却.pdf"
    if st.button("📄 PDF出力（売却）", use_container_width=True, key="btn_pdf_sale"):
        filename = str(Path("sale.pdf"))
        export_pdf_sale(st.session_state.roadmap, filename, project_name or "売却ロードマップ")
        with open(filename, "rb") as f:
            st.download_button("📥 ダウンロード（売却PDF）", data=f.read(), file_name=pdf_name, mime="application/pdf", use_container_width=True)

# --- 買い替え ---
with tab3:
    st.subheader("買い替え：上＝購入／下＝売却（別テーブル・同ページ）")
    st.markdown("**上段：購入**")
    render_horizontal_table_editor(st.session_state.roadmap["replace"]["up"], key_prefix="r_up")
    st.markdown("---")
    st.markdown("**下段：売却**")
    render_horizontal_table_editor(st.session_state.roadmap["replace"]["down"], key_prefix="r_down")

    pdf_name = f"{project_name or '買い替えロードマップ'}_購入_売却.pdf"
    if st.button("📄 PDF出力（買い替え・上下2段）", use_container_width=True, key="btn_pdf_replace"):
        filename = str(Path("replace.pdf"))
        export_pdf_replace(st.session_state.roadmap, filename, project_name or "買い替えロードマップ")
        with open(filename, "rb") as f:
            st.download_button("📥 ダウンロード（買い替えPDF）", data=f.read(), file_name=pdf_name, mime="application/pdf", use_container_width=True)