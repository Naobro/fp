# -*- coding: utf-8 -*-
# ファイル名: make_checklists.py
# 目的: 「購入4枚＋売却1枚」チェックリストPDFを作成（列幅固定で右端チェック欄がビシッと揃う）
# 使い方:
#   1) 同ディレクトリに NotoSansJP-Regular.ttf を置く
#   2) pip install -r requirements.txt
#   3) python make_checklists.py

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pathlib import Path
import os

# ========= 設定 =========
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)
PDF_PATH = OUTPUT_DIR / "チェックリスト_購入4＋売却1.pdf"
FONT_PATH = Path("NotoSansJP-Regular.ttf")
FONT_NAME = "NotoSansJP"

# チェック記号（枠）：フォント依存しないよう □ を使用
CHECK = "□"

# スタイル
def build_styles():
    styles = getSampleStyleSheet()
    # 日本語用ベース
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
        alignment=1,  # 中央
    )
    h1 = ParagraphStyle(
        "h1",
        parent=base,
        fontSize=13,
        leading=18,
        spaceBefore=6,
        spaceAfter=4,
    )
    head = ParagraphStyle(
        "head",
        parent=base,
        fontSize=11,
        leading=15,
        textColor=colors.white,
    )
    cell_left = ParagraphStyle("cell_left", parent=base, alignment=0)   # 左
    cell_center = ParagraphStyle("cell_center", parent=base, alignment=1)  # 中央
    cell_right = ParagraphStyle("cell_right", parent=base, alignment=2)    # 右
    return dict(base=base, title=title, h1=h1, head=head,
                cell_left=cell_left, cell_center=cell_center, cell_right=cell_right)

# テーブル作成（3列: 左□/中央テキスト/右□）
def make_table(data_rows, doc_width, styles, add_header=True):
    """
    data_rows: list[str]  # 中央カラム（書類名）のテキストのみを渡す
    返り値: Table
    """
    # 列幅（A4の余白差し引いたコンテンツ幅で固定）
    left_w = 14 * mm
    right_w = 14 * mm
    middle_w = doc_width - left_w - right_w

    table_data = []

    if add_header:
        table_data.append([
            Paragraph("必要なもの", styles["cell_center"]),
            Paragraph("書類", styles["cell_left"]),
            Paragraph("チェック", styles["cell_right"]),
        ])

    # 明細行
    for txt in data_rows:
        table_data.append([
            Paragraph(CHECK, styles["cell_center"]),         # 左の□（必要なもの）
            Paragraph(txt, styles["cell_left"]),             # 中央（左寄せ）
            Paragraph(CHECK, styles["cell_right"]),          # 右の□（右寄せ表示）
        ])

    tbl = Table(table_data, colWidths=[left_w, middle_w, right_w], repeatRows=1 if add_header else 0)

    # 罫線・塗り
    style_cmds = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONT", (0, 0), (-1, -1), FONT_NAME, 11),
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#444444")) if add_header else (),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E3A59")) if add_header else (),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white) if add_header else (),
        ("GRID", (0, 0 if add_header else 0), (-1, -1), 0.25, colors.HexColor("#BBBBBB")),
        ("ALIGN", (0, 1 if add_header else 0), (0, -1), "CENTER"),  # 左列中央
        ("ALIGN", (2, 1 if add_header else 0), (2, -1), "RIGHT"),   # 右列右寄せ
    ]
    # 空タプル除去
    style_cmds = [cmd for cmd in style_cmds if cmd]
    tbl.setStyle(TableStyle(style_cmds))
    return tbl

# セクション追加（見出し＋テーブル）
def add_section(flow, title, rows, styles, doc_width):
    flow.append(Spacer(1, 2*mm))
    flow.append(Paragraph(title, styles["h1"]))
    flow.append(Spacer(1, 1*mm))
    flow.append(make_table(rows, doc_width, styles, add_header=True))
    flow.append(Spacer(1, 4*mm))

def main():
    # フォント登録
    if not FONT_PATH.exists():
        raise FileNotFoundError(
            f"{FONT_PATH} が見つかりません。日本語表示のため必須です。"
        )
    pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))

    # ドキュメント
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        leftMargin=12*mm,
        rightMargin=12*mm,
        topMargin=12*mm,
        bottomMargin=12*mm,
    )
    styles = build_styles()
    doc_width = doc.width

    flow = []

    # ============ ページ1：購入① 事前審査 ============
    flow.append(Paragraph("購入① 事前審査", styles["title"]))

    rows_basic = [
        "運転免許証（表・裏）",
        "健康保険証（表・裏）",
        "源泉徴収票（会社員）",
        "確定申告書（自営業）",
    ]
    rows_cases = [
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
    ]
    add_section(flow, "基本書類", rows_basic, styles, doc_width)
    add_section(flow, "ケース別追加", rows_cases, styles, doc_width)
    flow.append(PageBreak())

    # ============ ページ2：購入② 売買契約・住宅ローン本申込 ============
    flow.append(Paragraph("購入② 売買契約・住宅ローン本申込", styles["title"]))
    rows_p2 = [
        "身分証明書",
        "実印",
        "住民票（世帯全員・マイナンバー省略・本籍省略）",
        "印鑑証明書",
        "住民税決定通知書 または 課税証明書",
    ]
    add_section(flow, "提出書類", rows_p2, styles, doc_width)
    flow.append(PageBreak())

    # ============ ページ3：購入③ 金消契約 ============
    flow.append(Paragraph("購入③ 金消契約（金融機関契約）", styles["title"]))
    rows_p3 = [
        "新住所の住民票（世帯全員・マイナンバー省略・本籍省略）",
        "（旧住所の場合）媒介契約書 または 賃貸借契約書 等の住所証明",
    ]
    add_section(flow, "提出書類", rows_p3, styles, doc_width)
    flow.append(PageBreak())

    # ============ ページ4：購入④ 決済時 ============
    flow.append(Paragraph("購入④ 決済時", styles["title"]))
    rows_p4 = [
        "身分証明書",
        "実印",
        "住民票（マイナンバー省略・本籍省略）",
        "印鑑証明書",
        "通帳・銀行印（必要に応じて）",
    ]
    add_section(flow, "当日持参", rows_p4, styles, doc_width)
    flow.append(PageBreak())

    # ============ ページ5：売却 ============
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

    # 生成
    doc.build(flow)
    print(f"✔ 出力: {PDF_PATH}")

if __name__ == "__main__":
    main()