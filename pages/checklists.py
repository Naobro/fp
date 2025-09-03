# -*- coding: utf-8 -*-
# 目的：
#  - 画面で「購入」と「売却」を分けて一覧表示（左=あなたの選定/右=お客様用）
#  - PDFは「購入PDF」「売却PDF」を別々に作成
# デザイン：
#  - ヘッダー：薄い黄色（#FFF7CC）× 黒文字
#  - 記号：■（選定済）/ □（未選定・お客様用） ※フォント依存の✅は不使用
#  - 列幅：左30mm / 右26mm / 中央は残り（「チェック」が折返さない）
# 安定化：
#  - フォントDLなし。ローカル NotoSansJP-Regular.ttf があれば使用、無ければ内蔵 HeiseiKakuGo-W5
#  - 追加依存なし（requests等 未使用）

import io
from pathlib import Path
from typing import Dict, List

import streamlit as st
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# ========== 画面設定 ==========
st.set_page_config(page_title="チェックリストPDF", page_icon="✅", layout="wide")

# ========== フォント（ローカル→内蔵。DLしない） ==========
FONT_NAME = "AppJPFont"
def ensure_jp_font():
    global FONT_NAME
    local_ttf = Path("NotoSansJP-Regular.ttf")
    if local_ttf.exists():
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(local_ttf)))
    else:
        pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
        FONT_NAME = "HeiseiKakuGo-W5"
ensure_jp_font()

# 記号
BOX_EMPTY = "□"
BOX_FULL  = "■"

# ヘッダー色
HEADER_BG = colors.HexColor("#FFF7CC")  # 薄い黄色
HEADER_FG = colors.black

# ========== マスタ（文言・順序・要望反映） ==========
# 購入：①は「基本書類」「追加書類」に分割。④は注記（提出不要）を明記。
PURCHASE_MASTER: Dict[str, Dict[str, List[str]]] = {
    "① 事前審査": {
        "基本書類": [
            "運転免許証（表・裏）",
            "健康保険証（表・裏）",
            "源泉徴収票（会社員）",
            "確定申告書（自営業）",
        ],
        "追加書類": [
            "返済予定表（その他借入あり）",
            "職務経歴書（転職1年未満）",
            "雇用契約書／労働条件通知書（転職1年未満）",
            "給与明細（直近3か月分）",
            "賞与明細（転職1年未満／支給分）",
            "満額時の直近源泉徴収票（産休・育休中）",
            "満額時の直近源泉徴収票＋復帰後給与明細1か月＋賞与明細1年分（産休復帰1年未満）",
            "在留カード または 特別永住者証明書（外国籍）",
            "建築工事請負契約書＋建築見積書（注文住宅）",
            "諸費用明細（諸費用借入／仲介準備）",
            "リフォーム見積書（リフォーム借入）",
        ],
    },
    "② 売買契約・住宅ローン本申込": {
        "提出書類": [
            "身分証明書",
            "実印",
            "住民票（世帯全員・マイナンバー省略・本籍省略）",
            "印鑑証明書",
            "住民税決定通知書 または 課税証明書",
        ],
    },
    "③ 金消契約（金融機関契約）": {
        "提出書類": [
            "新住所の住民票（世帯全員・マイナンバー省略・本籍省略）",
            "（旧住所の場合 → 媒介契約書／賃貸借契約書 等 住所証明）",
        ],
    },
    "④ 決済時": {
        "当日持参": [
            "身分証明書",
            "実印",
            "住民票（提出不要）",
            "印鑑証明書（提出不要）",
            "通帳・銀行印（必要に応じて）",
        ],
    },
}

# 売却：要望を追加
#  - 媒介契約前：不具合など伝達事項
#  - 売買契約前確認：抵当権抹消書類（準備期間の確認：今日の明日では不可）
SALE_MASTER: Dict[str, Dict[str, List[str]]] = {
    "媒介契約前": {
        "確認項目": [
            "建築時の資料（設計図・確認申請書 など）",
            "リフォーム履歴",
            "間取り図",
            "不具合など伝達事項",
        ],
    },
    "売買契約前確認": {
        "確認項目": [
            "登記識別情報（権利証）の有無",
            "固定資産税納税通知書（年税額確認）",
            "評価証明書（媒介契約で代理取得可）",
            "測量・解体の有無と費用負担",
            "抵当権抹消書類（準備期間の確認：今日の明日では不可）",
        ],
    },
    "決済時": {
        "当日持参": [
            "登記識別情報（原本）",
            "印鑑証明書",
        ],
    },
}

# ========== 共通：PDFスタイル & テーブル ==========
def build_styles():
    s = getSampleStyleSheet()
    base = ParagraphStyle("base", parent=s["Normal"], fontName=FONT_NAME, fontSize=11, leading=15, textColor=colors.black)
    h_title = ParagraphStyle("h_title", parent=base, fontSize=16, leading=22, alignment=1, spaceAfter=8)
    h_group = ParagraphStyle("h_group", parent=base, fontSize=13, leading=18, spaceBefore=6, spaceAfter=4)
    h_sub   = ParagraphStyle("h_sub",   parent=base, fontSize=11.5, leading=16, spaceBefore=2, spaceAfter=2)
    cell_left   = ParagraphStyle("cell_left",   parent=base, alignment=0)
    cell_center = ParagraphStyle("cell_center", parent=base, alignment=1)
    cell_right  = ParagraphStyle("cell_right",  parent=base, alignment=2)
    return dict(base=base, h_title=h_title, h_group=h_group, h_sub=h_sub,
                cell_left=cell_left, cell_center=cell_center, cell_right=cell_right)

def make_table(rows: List[str], flags: Dict[int, bool], doc_width: float, stl: dict) -> Table:
    left_w  = 30 * mm
    right_w = 26 * mm  # 「チェック」が折返さない幅
    middle_w = doc_width - left_w - right_w
    data = [[Paragraph("必要なもの", stl["cell_center"]),
             Paragraph("書類",       stl["cell_left"]),
             Paragraph("チェック",   stl["cell_right"])]]
    for i, txt in enumerate(rows):
        left_mark = BOX_FULL if flags.get(i, False) else BOX_EMPTY
        data.append([
            Paragraph(left_mark, stl["cell_center"]),
            Paragraph(txt, stl["cell_left"]),
            Paragraph(BOX_EMPTY, stl["cell_right"]),  # 右はお客様用の空欄
        ])
    t = Table(data, colWidths=[left_w, middle_w, right_w], repeatRows=1)
    t.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("FONT", (0,0), (-1,-1), FONT_NAME, 11),
        # ヘッダー：薄い黄色×黒文字
        ("BACKGROUND", (0,0), (-1,0), HEADER_BG),
        ("TEXTCOLOR", (0,0), (-1,0), HEADER_FG),
        ("LINEBELOW", (0,0), (-1,0), 0.8, colors.HexColor("#555555")),
        # 罫線：薄いグレー
        ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#CCCCCC")),
        # 揃え
        ("ALIGN", (0,1), (0,-1), "CENTER"),
        ("ALIGN", (2,1), (2,-1), "RIGHT"),
    ]))
    return t

# ========== 画面UI：購入 ==========
st.markdown("## 🏠 購入時 必要書類チェックリスト")
purchase_flags: Dict[str, Dict[str, Dict[int, bool]]] = {}

for big_group, sub_groups in PURCHASE_MASTER.items():
    st.markdown("⸻")
    st.markdown(f"**{big_group}**")
    purchase_flags[big_group] = {}
    for sub_name, items in sub_groups.items():
        st.write("")  # 空白（見やすさ）
        st.caption(sub_name)
        purchase_flags[big_group][sub_name] = {}
        for i, text in enumerate(items):
            cols = st.columns([0.06, 0.86, 0.08])  # 左□ / テキスト / 右□
            with cols[0]:
                purchase_flags[big_group][sub_name][i] = st.checkbox("", key=f"p-{big_group}-{sub_name}-{i}")
            with cols[1]:
                st.write(text)
            with cols[2]:
                st.write(BOX_EMPTY)

st.divider()

# ========== 画面UI：売却 ==========
st.markdown("## 🏡 売却時 必要書類チェックリスト")
sale_flags: Dict[str, Dict[str, Dict[int, bool]]] = {}
for big_group, sub_groups in SALE_MASTER.items():
    st.markdown("⸻")
    st.markdown(f"**{big_group}**")
    sale_flags[big_group] = {}
    for sub_name, items in sub_groups.items():
        st.write("")  # 空白
        st.caption(sub_name)
        sale_flags[big_group][sub_name] = {}
        for i, text in enumerate(items):
            cols = st.columns([0.06, 0.86, 0.08])
            with cols[0]:
                sale_flags[big_group][sub_name][i] = st.checkbox("", key=f"s-{big_group}-{sub_name}-{i}")
            with cols[1]:
                st.write(text)
            with cols[2]:
                st.write(BOX_EMPTY)

st.divider()

# ========== PDF生成（購入 / 売却 別々） ==========
def build_styles_and_doc():
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=12*mm, rightMargin=12*mm,
        topMargin=12*mm, bottomMargin=12*mm,
    )
    return buf, doc, build_styles()

def build_purchase_pdf() -> bytes:
    buf, doc, stl = build_styles_and_doc()
    w = doc.width
    flow = []
    flow.append(Paragraph("購入時 必要書類チェックリスト", stl["h_title"]))
    for big_group, sub_groups in PURCHASE_MASTER.items():
        flow.append(Spacer(1, 3*mm))
        flow.append(Paragraph(big_group, stl["h_group"]))
        for sub_name, items in sub_groups.items():
            flow.append(Spacer(1, 2*mm))  # 空白
            flow.append(Paragraph(sub_name, stl["h_sub"]))
            flow.append(Spacer(1, 1*mm))
            flags = purchase_flags.get(big_group, {}).get(sub_name, {})
            flow.append(make_table(items, flags, w, stl))
            flow.append(Spacer(1, 5*mm))  # グループ間の空白
    doc.build(flow)
    pdf = buf.getvalue(); buf.close(); return pdf

def build_sale_pdf() -> bytes:
    buf, doc, stl = build_styles_and_doc()
    w = doc.width
    flow = []
    flow.append(Paragraph("売却時 必要書類チェックリスト", stl["h_title"]))
    for big_group, sub_groups in SALE_MASTER.items():
        flow.append(Spacer(1, 3*mm))
        flow.append(Paragraph(big_group, stl["h_group"]))
        for sub_name, items in sub_groups.items():
            flow.append(Spacer(1, 2*mm))
            flow.append(Paragraph(sub_name, stl["h_sub"]))
            flow.append(Spacer(1, 1*mm))
            flags = sale_flags.get(big_group, {}).get(sub_name, {})
            flow.append(make_table(items, flags, w, stl))
            flow.append(Spacer(1, 5*mm))
    doc.build(flow)
    pdf = buf.getvalue(); buf.close(); return pdf

# ========== ダウンロード ==========
col1, col2 = st.columns(2)
with col1:
    if st.button("購入PDFを作成", type="primary"):
        pdf = build_purchase_pdf()
        st.download_button("購入PDFをダウンロード", data=pdf, file_name="チェックリスト_購入.pdf", mime="application/pdf")
with col2:
    if st.button("売却PDFを作成", type="primary"):
        pdf = build_sale_pdf()
        st.download_button("売却PDFをダウンロード", data=pdf, file_name="チェックリスト_売却.pdf", mime="application/pdf")