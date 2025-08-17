# utils.py
import os
import platform
import matplotlib.pyplot as plt
from fpdf import FPDF

# =====================================
# 🔹 Matplotlib用 日本語フォント設定関数（そのまま）
# =====================================
def set_matplotlib_japanese_font():
    system = platform.system()
    if system == "Darwin":  # macOS
        plt.rcParams["font.family"] = "Hiragino Sans"
    elif system == "Windows":
        plt.rcParams["font.family"] = "MS Gothic"
    else:
        plt.rcParams["font.family"] = "Noto Sans CJK JP"

# =====================================
# 🔹 FPDFで日本語フォントを登録する関数群（パス解決を絶対化）
# =====================================

# ↓↓↓ ここを相対パスではなく、utils.py からの絶対パス解決に変更 ↓↓↓
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(BASE_DIR, "fonts")

def _font_path(filename: str) -> str:
    path = os.path.join(FONT_DIR, filename)
    if not os.path.exists(path):
        # 原因特定用にフルパスを出す
        raise FileNotFoundError(f"Font file not found: {path}")
    return path

def register_fonts(pdf: FPDF) -> FPDF:
    regular_path = _font_path("NotoSansJP-Regular.ttf")
    bold_path = _font_path("NotoSansJP-Bold.ttf")
    # Unicodeサブセット埋め込み（必須）
    pdf.add_font("NotoSans", "", regular_path, uni=True)
    pdf.add_font("NotoSans", "B", bold_path, uni=True)
    return pdf

def create_pdf_with_fonts() -> FPDF:
    # 単位・用紙を明示（任意だが安定）
    pdf = FPDF(unit="mm", format="A4")
    pdf = register_fonts(pdf)
    return pdf

def add_title(pdf: FPDF, title: str):
    pdf.set_font("NotoSans", "B", 18)
    pdf.cell(0, 10, title, ln=True, align="C")

def add_text(pdf: FPDF, text: str, size: int = 12):
    pdf.set_font("NotoSans", "", size)
    pdf.multi_cell(0, 8, text)

def add_table(pdf: FPDF, headers: list, rows: list):
    pdf.set_font("NotoSans", "B", 12)
    col_width = pdf.w / (len(headers) + 1)
    for header in headers:
        pdf.cell(col_width, 10, header, border=1, align="C")
    pdf.ln()
    pdf.set_font("NotoSans", "", 11)
    for row in rows:
        for cell in row:
            pdf.cell(col_width, 10, str(cell), border=1, align="C")
        pdf.ln()