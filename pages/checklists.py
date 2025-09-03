# -*- coding: utf-8 -*-
# ファイル: pages/checklists.py
# 目的: 「購入4＋売却1」のチェックリストPDFをStreamlitで生成（フォント自動フォールバック）
# 仕様:
#  - 右端チェック欄がズレない固定幅3列テーブル
#  - フォント優先度: ローカルNotoSansJP → オンラインDL → 内蔵HeiseiKakuGo-W5（ReportLab）
#  - 住民票表記は「マイナンバー省略・本籍省略」に統一
#  - 左列（必要なもの）幅を30mmに拡大 → 二段落ち防止
#  - Python 3.13 / Streamlit Cloud 対応

import io
from pathlib import Path
from typing import List

import streamlit as st
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont  # 内蔵日本語フォント

# ========= 画面設定 =========
st.set_page_config(page_title="チェックリストPDF", page_icon="✅", layout="wide")
st.title("購入・売却チェックリスト（PDF出力）")

# ========= フォント設定 =========
CANDIDATE_TTF = [
    Path("NotoSansJP-Regular.ttf"),
    Path("assets/fonts/NotoSansJP-Regular.ttf"),
]

FONT_NAME = "AppJPFont"
FONT_READY = False
FALLBACK_USED = False

def ensure_jp_font():
    global FONT_NAME, FONT_READY, FALLBACK_USED

    # 1) ローカル探索
    for p in CANDIDATE_TTF:
        if p.exists():
            pdfmetrics.registerFont(TTFont(FONT_NAME, str(p)))
            FONT_READY = True
            return

    # 2) オンラインDL（失敗してもOK）
    try:
        import requests
        urls = [
            "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansJP-Regular.otf",
            "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansJP-Regular.otf",
        ]
        save_to = Path("NotoSansJP-Regular.otf")
        for url in urls:
            try:
                r = requests.get(url, timeout=15)
                if r.status_code == 200 and r.content:
                    save_to.write_bytes(r.content)
                    pdfmetrics.registerFont(TTFont(FONT_NAME, str(save_to)))
                    FONT_READY = True
                    return
            except Exception:
                continue
    except Exception:
        pass

    # 3) フォールバック（内蔵CIDフォント）
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
    FONT_NAME = "HeiseiKakuGo-W5"
    FONT_READY = True
    FALLBACK_USED = True

ensure_jp_font()

CHECK = "□"

def build_styles():
    styles = getSampleStyleSheet()
    base = ParagraphStyle(
        "jp_base",
        parent=styles["Normal"],
        fontName=FONT_NAME,
        fontSize=11,
        leading=15,
        textColor=colors.black,
    )
    title = ParagraphStyle(
        "title",
        parent=base,
        fontSize=16,
        leading=22,
        spaceAfter=6,
        alignment=1,
    )
    h1 = ParagraphStyle(
        "h1",
        parent=base,
        fontSize=13,
        leading=18,
        spaceBefore=6,
        spaceAfter=4,
    )
    cell_left  = ParagraphStyle("cell_left",  parent=base, alignment=0)
    cell_center= ParagraphStyle("cell_center",parent=base, alignment=1)
    cell_right = ParagraphStyle("cell_right", parent=base, alignment=2)
    return dict(base=base, title=title, h1=h1,
                cell_left=cell_left, cell_center=cell_center, cell_right=cell_right)

def make_table(data_rows: List[str], doc_width, styles, add_header=True):
    """3列固定幅テーブル（左□ / 中央テキスト / 右□）で右端チェックを綺麗に縦揃え。"""
    left_w  = 30 * mm   # 必要なもの
    right_w = 18 * mm   # チェック
    middle_w = doc_width - left_w - right_w

    table_data = []
    if add_header:
        table_data.append([
            Paragraph("必要なもの", styles["cell_center"]),
            Paragraph("書類",       styles["cell_left"]),
            Paragraph("チェック",   styles["cell_right"]),
        ])

    for txt in data_rows:
        table_data.append([
            Paragraph(CHECK, styles["cell_center"]),
            Paragraph(txt,   styles["cell_left"]),
            Paragraph(CHECK, styles["cell_right"]),
        ])

    tbl = Table(table_data, colWidths=[left_w, middle_w, right_w], repeatRows=1 if add_header else 0)
    cmds = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONT",   (0, 0), (-1, -1), FONT_NAME, 11),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E3A59")) if add_header else (),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white) if add_header else (),
        ("LINEBELOW",  (0, 0), (-1, 0), 1, colors.HexColor("#444444")) if add_header else (),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#BBBBBB")),
        ("ALIGN", (0, 1 if add_header else 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 1 if add_header else 0), (2, -1), "RIGHT"),
    ]
    tbl.setStyle(TableStyle([c for c in cmds if c]))
    return tbl

def add_section(flow, title, rows, styles, doc_width):
    flow.append(Spacer(1, 2 * mm))
    flow.append(Paragraph(title, styles["h1"]))
    flow.append(Spacer(1, 1 * mm))
    flow.append(make_table(rows, doc_width, styles, add_header=True))
    flow.append(Spacer(1, 4 * mm))

def build_pdf() -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )
    styles = build_styles()
    doc_width = doc.width
    flow = []

    # ページ1：購入① 事前審査
    flow.append(Paragraph("購入① 事前審査", styles["title"]))
    add_section(flow, "基本書類", [
        "運転免許証（表・裏）",
        "健康保険証（表・裏）",
        "源泉徴収票（会社員）",
        "確定申告書（自営業）",
    ], styles, doc_width)
    add_section(flow, "ケース別追加", [
        "返済予定表（その他借入あり）",
        "職務経歴書（転職1年未満）",
        "雇用契約書 または 労働条件通知書（転職1年未満）",
        "給与明細（直近3か月分）",
        "賞与明細（転職1年未満／支給分）",
        "満額時の直近源泉徴収票（産休・育休中）",
        "満額時の直近源泉徴収票＋復帰後の給与明細1か月＋賞与明細1年分（産休復帰1年未満）",
        "在留カード または 特別永住者証明書（外国籍）",
        "建築工事請負契約書＋建築見積書（注文住宅）",
        "諸費用明細（諸費用借入時／仲介が準備）",
        "リフォーム見積書（リフォーム借入時）",
    ], styles, doc_width)
    flow.append(PageBreak())

    # ページ2：購入② 売買契約・住宅ローン本申込
    flow.append(Paragraph("購入② 売買契約・住宅ローン本申込", styles["title"]))
    add_section(flow, "提出書類", [
        "身分証明書",
        "実印",
        "住民票（世帯全員・マイナンバー省略・本籍省略）",
        "印鑑証明書",
        "住民税決定通知書 または 課税証明書",
    ], styles, doc_width)
    flow.append(PageBreak())

    # ページ3：購入③ 金消契約
    flow.append(Paragraph("購入③ 金消契約（金融機関契約）", styles["title"]))
    add_section(flow, "提出書類", [
        "新住所の住民票（世帯全員・マイナンバー省略・本籍省略）",
        "（旧住所の場合）媒介契約書 または 賃貸借契約書 等の住所証明",
    ], styles, doc_width)
    flow.append(PageBreak())

    # ページ4：購入④ 決済時
    flow.append(Paragraph("購入④ 決済時", styles["title"]))
    add_section(flow, "当日持参", [
        "身分証明書",
        "実印",
        "住民票（マイナンバー省略・本籍省略）",
        "印鑑証明書",
        "通帳・銀行印（必要に応じて）",
    ], styles, doc_width)
    flow.append(PageBreak())

    # ページ5：売却
    flow.append(Paragraph("売却チェックリスト", styles["title"]))
    add_section(flow, "媒介契約前", [
        "建築時の資料（設計図・確認申請書 など）",
        "リフォーム履歴",
        "間取り図",
    ], styles, doc_width)
    add_section(flow, "売買契約前確認", [
        "登記識別情報（権利証）の有無",
        "固定資産税納税通知書（年税額の確認）",
        "評価証明書（媒介契約で代理取得可）",
        "測量・解体の有無 と 費用負担",
    ], styles, doc_width)
    add_section(flow, "決済時", [
        "登記識別情報（原本）",
        "印鑑証明書",
    ], styles, doc_width)

    doc.build(flow)
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes

# ========== UI ==========
col1, col2 = st.columns(2)
with col1:
    st.markdown("**フォント状態**")
    if FALLBACK_USED:
        st.info("NotoSansJPが見つからなかったため、内蔵日本語フォント（HeiseiKakuGo-W5）で生成します。")
    else:
        st.success("NotoSansJPを使用します。")

with col2:
    st.markdown("**テーブル仕様**")
    st.write("固定幅3列（左30mm / 中央残り / 右18mm）。右端チェック欄は右寄せで整列。")

if st.button("PDFを作成する", type="primary"):
    pdf = build_pdf()
    st.download_button(
        label="チェックリスト（購入4＋売却1）をダウンロード",
        data=pdf,
        file_name="チェックリスト_購入4＋売却1.pdf",
        mime="application/pdf",
    )
    st.success("PDFを生成しました。右のボタンからダウンロードできます。")