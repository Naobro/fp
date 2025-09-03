# -*- coding: utf-8 -*-
# 画面で「購入」「売却」を分けて一覧表示（左=あなたの選定 / 右=お客様用）
# PDFは「購入PDF」「売却PDF」を別々に作成
# 依存は streamlit / reportlab のみ（requests / numpy / pandas / matplotlib / supabase 不使用）

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

# ─────────────────────────────────────────────────────────────
# 画面
# ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="チェックリストPDF", page_icon="✅", layout="wide")

# ─────────────────────────────────────────────────────────────
# フォント：最優先で「リポジトリ直下の fonts/NotoSansJP-Regular.ttf」を探す
#  - pages/checklists.py から見て: ../../fonts, ../fonts, ./fonts を順にチェック
#  - 見つからなければカレント直下
#  - 最後に内蔵 HeiseiKakuGo-W5 にフォールバック（DLはしない）
# ─────────────────────────────────────────────────────────────
FONT_NAME = "AppJPFont"
FONT_FILE = "NotoSansJP-Regular.ttf"

def register_jp_font():
    global FONT_NAME
    here = Path(__file__).resolve().parent             # pages/
    candidates = [
        here.parent.parent / "fonts" / FONT_FILE,      # ../../fonts/
        here.parent / "fonts" / FONT_FILE,             # ../fonts/
        here / "fonts" / FONT_FILE,                    # ./fonts/
        Path.cwd() / "fonts" / FONT_FILE,              # CWD/fonts/
        Path.cwd() / FONT_FILE,                        # CWD/
    ]
    for p in candidates:
        if p.exists():
            pdfmetrics.registerFont(TTFont(FONT_NAME, str(p)))
            return
    # 見つからない場合は内蔵フォント
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
    FONT_NAME = "HeiseiKakuGo-W5"

register_jp_font()

# 記号・配色
BOX_EMPTY = "□"
BOX_FULL  = "■"
HEADER_BG = colors.HexColor("#FFF7CC")  # 薄い黄色
HEADER_FG = colors.black

# ─────────────────────────────────────────────────────────────
# 文言マスタ（要望反映）
# ─────────────────────────────────────────────────────────────
PURCHASE_MASTER: Dict[str, Dict[str, List[str]]] = {
    "① 事前審査": {
        "基本書類": [
            "運転免許証（表・裏）",
            "健康保険証（表・裏）",
            "源泉徴収票（会社員）",
            "確定申告書（自営業）",
        ],
        "追加書類": [
            "【借入がある場合】",
            "返済予定表",
            "",
            "【転職1年未満】",
            "職務経歴書",
            "雇用契約書／労働条件通知書",
            "給与明細（直近3か月分）",
            "賞与明細（支給分）",
            "",
            "【産休・育休中】",
            "満額時の直近源泉徴収票・給与明細等（金融機関による）",
            "",
            "【産休復帰1年未満】",
            "満額時源泉徴収票＋復帰後給与明細1か月＋賞与明細1年分",
            "",
            "【外国籍】",
            "在留カード または 特別永住者証明書",
            "",
            "【諸費用借入・リフォーム費用・注文住宅】",
            "諸費用明細（諸費用借入／仲介準備）",
            "リフォーム見積書（リフォーム借入）",
            "建築工事請負契約書＋建築見積書（注文住宅）",
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

# ─────────────────────────────────────────────────────────────
# PDFスタイル
# ─────────────────────────────────────────────────────────────
def build_styles():
    ss = getSampleStyleSheet()
    base = ParagraphStyle("base", parent=ss["Normal"], fontName=FONT_NAME, fontSize=11, leading=15, textColor=colors.black)
    h_title = ParagraphStyle("h_title", parent=base, fontSize=16, leading=22, alignment=1, spaceAfter=8)
    h_group = ParagraphStyle("h_group", parent=base, fontSize=13, leading=18, spaceBefore=6, spaceAfter=4)
    h_sub   = ParagraphStyle("h_sub",   parent=base, fontSize=11.5, leading=16, spaceBefore=2, spaceAfter=2)
    h_head  = ParagraphStyle("h_head",  parent=base, fontSize=11.5, leading=16, spaceBefore=2, spaceAfter=2, textColor=colors.HexColor("#333333"))
    cell_l  = ParagraphStyle("cell_l",  parent=base, alignment=0)
    cell_c  = ParagraphStyle("cell_c",  parent=base, alignment=1)
    cell_r  = ParagraphStyle("cell_r",  parent=base, alignment=2)
    return dict(base=base, h_title=h_title, h_group=h_group, h_sub=h_sub, h_head=h_head, cell_l=cell_l, cell_c=cell_c, cell_r=cell_r)

def is_heading(txt: str) -> bool:
    return txt.startswith("【") and txt.endswith("】")

def is_blank(txt: str) -> bool:
    return txt.strip() == ""

def make_table(rows: List[str], flags: Dict[int, bool], width: float, stl: dict) -> Table:
    left_w  = 30 * mm
    right_w = 26 * mm
    middle_w = width - left_w - right_w
    data = [[Paragraph("必要なもの", stl["cell_c"]),
             Paragraph("書類",       stl["cell_l"]),
             Paragraph("チェック",   stl["cell_r"])]]
    for i, txt in enumerate(rows):
        if is_blank(txt):
            data.append(["", Paragraph(" ", stl["cell_l"]), ""])
            continue
        if is_heading(txt):
            data.append(["", Paragraph(txt, stl["h_head"]), ""])
            continue
        left_mark = BOX_FULL if flags.get(i, False) else BOX_EMPTY
        data.append([Paragraph(left_mark, stl["cell_c"]),
                     Paragraph(txt,     stl["cell_l"]),
                     Paragraph(BOX_EMPTY, stl["cell_r"])])
    t = Table(data, colWidths=[left_w, middle_w, right_w], repeatRows=1)
    t.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("FONT", (0,0), (-1,-1), FONT_NAME, 11),
        ("BACKGROUND", (0,0), (-1,0), HEADER_BG),
        ("TEXTCOLOR", (0,0), (-1,0), HEADER_FG),
        ("LINEBELOW", (0,0), (-1,0), 0.8, colors.HexColor("#555555")),
        ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#CCCCCC")),
        ("ALIGN", (0,1), (0,-1), "CENTER"),
        ("ALIGN", (2,1), (2,-1), "RIGHT"),
    ]))
    return t

# ─────────────────────────────────────────────────────────────
# 画面UI：購入
# ─────────────────────────────────────────────────────────────
st.markdown("## 🏠 購入時 必要書類チェックリスト")
purchase_flags: Dict[str, Dict[str, Dict[int, bool]]] = {}
for big, subs in PURCHASE_MASTER.items():
    st.markdown("⸻"); st.markdown(f"**{big}**")
    purchase_flags[big] = {}
    for sub, items in subs.items():
        st.write("")  # 空白
        st.caption(sub)
        purchase_flags[big][sub] = {}
        for i, text in enumerate(items):
            if is_blank(text):
                st.write("")  # 空行
                continue
            if is_heading(text):
                st.markdown(f"*{text}*")  # 見出し（選択不可）
                continue
            c = st.columns([0.06, 0.86, 0.08])
            with c[0]:
                purchase_flags[big][sub][i] = st.checkbox("", key=f"p-{big}-{sub}-{i}")
            with c[1]:
                st.write(text)
            with c[2]:
                st.write(BOX_EMPTY)  # お客様用

st.divider()

# ─────────────────────────────────────────────────────────────
# 画面UI：売却
# ─────────────────────────────────────────────────────────────
st.markdown("## 🏡 売却時 必要書類チェックリスト")
sale_flags: Dict[str, Dict[str, Dict[int, bool]]] = {}
for big, subs in SALE_MASTER.items():
    st.markdown("⸻"); st.markdown(f"**{big}**")
    sale_flags[big] = {}
    for sub, items in subs.items():
        st.write("")  # 空白
        st.caption(sub)
        sale_flags[big][sub] = {}
        for i, text in enumerate(items):
            c = st.columns([0.06, 0.86, 0.08])
            with c[0]:
                sale_flags[big][sub][i] = st.checkbox("", key=f"s-{big}-{sub}-{i}")
            with c[1]:
                st.write(text)
            with c[2]:
                st.write(BOX_EMPTY)

st.divider()

# ─────────────────────────────────────────────────────────────
# PDF生成
# ─────────────────────────────────────────────────────────────
def new_doc():
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=12*mm, rightMargin=12*mm,
                            topMargin=12*mm, bottomMargin=12*mm)
    return buf, doc, build_styles()

def build_purchase_pdf() -> bytes:
    buf, doc, stl = new_doc()
    w = doc.width
    flow = [Paragraph("購入時 必要書類チェックリスト", stl["h_title"])]
    for big, subs in PURCHASE_MASTER.items():
        flow += [Spacer(1, 3*mm), Paragraph(big, stl["h_group"])]
        for sub, items in subs.items():
            flow += [Spacer(1, 2*mm), Paragraph(sub, stl["h_sub"]), Spacer(1, 1*mm)]
            flags = purchase_flags.get(big, {}).get(sub, {})
            flow.append(make_table(items, flags, w, stl))
            flow.append(Spacer(1, 5*mm))
    doc.build(flow)
    pdf = buf.getvalue(); buf.close(); return pdf

def build_sale_pdf() -> bytes:
    buf, doc, stl = new_doc()
    w = doc.width
    flow = [Paragraph("売却時 必要書類チェックリスト", stl["h_title"])]
    for big, subs in SALE_MASTER.items():
        flow += [Spacer(1, 3*mm), Paragraph(big, stl["h_group"])]
        for sub, items in subs.items():
            flow += [Spacer(1, 2*mm), Paragraph(sub, stl["h_sub"]), Spacer(1, 1*mm)]
            flags = sale_flags.get(big, {}).get(sub, {})
            flow.append(make_table(items, flags, w, stl))
            flow.append(Spacer(1, 5*mm))
    doc.build(flow)
    pdf = buf.getvalue(); buf.close(); return pdf

c1, c2 = st.columns(2)
with c1:
    if st.button("購入PDFを作成", type="primary"):
        st.download_button("購入PDFをダウンロード", data=build_purchase_pdf(),
                           file_name="チェックリスト_購入.pdf", mime="application/pdf")
with c2:
    if st.button("売却PDFを作成", type="primary"):
        st.download_button("売却PDFをダウンロード", data=build_sale_pdf(),
                           file_name="チェックリスト_売却.pdf", mime="application/pdf")