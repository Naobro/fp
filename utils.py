import os
import platform
import matplotlib.pyplot as plt
from fpdf import FPDF

# =====================================
# 🔹 Matplotlib用 日本語フォント設定関数
# =====================================
def set_matplotlib_japanese_font():
    """
    OSごとにMatplotlibで日本語フォントを設定する
    """
    system = platform.system()
    if system == "Darwin":  # macOS
        plt.rcParams["font.family"] = "Hiragino Sans"
    elif system == "Windows":
        plt.rcParams["font.family"] = "MS Gothic"
    else:
        plt.rcParams["font.family"] = "Noto Sans CJK JP"


# =====================================
# 🔹 FPDFで日本語フォントを登録する関数群
# =====================================

# フォントフォルダのパス
FONT_DIR = "fonts"

def register_fonts(pdf: FPDF) -> FPDF:
    """
    FPDFオブジェクトに日本語フォントを登録する関数
    """
    regular_path = os.path.join(FONT_DIR, "NotoSansJP-Regular.ttf")
    bold_path = os.path.join(FONT_DIR, "NotoSansJP-Bold.ttf")

    pdf.add_font("NotoSans", "", regular_path, uni=True)
    pdf.add_font("NotoSans", "B", bold_path, uni=True)

    return pdf


def create_pdf_with_fonts() -> FPDF:
    """
    日本語フォントを登録済みのFPDFオブジェクトを返す便利関数
    """
    pdf = FPDF()
    pdf = register_fonts(pdf)
    return pdf


def add_title(pdf: FPDF, title: str):
    """
    PDFにタイトルを追加する共通関数
    """
    pdf.set_font("NotoSans", "B", 18)
    pdf.cell(0, 10, title, ln=True, align="C")


def add_text(pdf: FPDF, text: str, size: int = 12):
    """
    PDFに本文テキストを追加する共通関数
    """
    pdf.set_font("NotoSans", "", size)
    pdf.multi_cell(0, 8, text)


def add_table(pdf: FPDF, headers: list, rows: list):
    """
    シンプルな表をPDFに追加する共通関数
    headers: ["列1", "列2", ...]
    rows: [["セル1", "セル2", ...], [...], ...]
    """
    pdf.set_font("NotoSans", "B", 12)
    col_width = pdf.w / (len(headers) + 1)

    # ヘッダー行
    for header in headers:
        pdf.cell(col_width, 10, header, border=1, align="C")
    pdf.ln()

    # データ行
    pdf.set_font("NotoSans", "", 11)
    for row in rows:
        for cell in row:
            pdf.cell(col_width, 10, str(cell), border=1, align="C")
        pdf.ln()
