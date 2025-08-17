# utils.py の該当部のみ差し替え
import os
import platform
import matplotlib.pyplot as plt
from fpdf import FPDF

def set_matplotlib_japanese_font():
    system = platform.system()
    if system == "Darwin":
        plt.rcParams["font.family"] = "Hiragino Sans"
    elif system == "Windows":
        plt.rcParams["font.family"] = "MS Gothic"
    else:
        plt.rcParams["font.family"] = "Noto Sans CJK JP"

# ==== ここから修正 ====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 候補1: utils.py と同じパッケージ配下: /mount/src/fp/fonts
cand1 = os.path.join(BASE_DIR, "fonts")
# 候補2: リポジトリ直下: /mount/src/fonts
cand2 = os.path.abspath(os.path.join(BASE_DIR, "..", "fonts"))

if os.path.isdir(cand1):
    FONT_DIR = cand1
elif os.path.isdir(cand2):
    FONT_DIR = cand2
else:
    # どちらにも無ければ明示的に落とす（フルパスを出して原因特定）
    raise FileNotFoundError(f"fonts directory not found. tried: {cand1} , {cand2}")

def _font_path(filename: str) -> str:
    path = os.path.join(FONT_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Font file not found: {path}")
    return path

def register_fonts(pdf: FPDF) -> FPDF:
    regular_path = _font_path("NotoSansJP-Regular.ttf")
    bold_path = _font_path("NotoSansJP-Bold.ttf")
    pdf.add_font("NotoSans", "", regular_path, uni=True)
    pdf.add_font("NotoSans", "B", bold_path, uni=True)
    return pdf

def create_pdf_with_fonts() -> FPDF:
    pdf = FPDF(unit="mm", format="A4")
    pdf = register_fonts(pdf)
    return pdf
# ==== 修正ここまで ====

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