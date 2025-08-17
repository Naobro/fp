# utils.py
import os
import platform
from pathlib import Path
import matplotlib.pyplot as plt
from fpdf import FPDF

# ==============================
# Matplotlib 日本語フォント設定
# ==============================
def set_matplotlib_japanese_font():
    system = platform.system()
    if system == "Darwin":      # macOS
        plt.rcParams["font.family"] = "Hiragino Sans"
    elif system == "Windows":
        plt.rcParams["font.family"] = "MS Gothic"
    else:                       # Linux/Streamlit Cloud
        plt.rcParams["font.family"] = "Noto Sans CJK JP"


# ==============================
# FPDF2 用フォント解決（決定版）
# ==============================
FONT_FILENAMES = ("NotoSansJP-Regular.ttf", "NotoSansJP-Bold.ttf")

def _both_exist(dir_path: Path) -> bool:
    return dir_path.is_dir() and all((dir_path / name).exists() for name in FONT_FILENAMES)

def _font_dir_candidates() -> list[Path]:
    """環境差を吸収する探索候補を列挙"""
    here = Path(__file__).resolve()       # .../fp/utils.py
    pkg_dir = here.parent                 # .../fp
    repo_root = pkg_dir.parent            # .../
    cwd = Path.cwd()

    env_dir = os.environ.get("FONT_DIR")
    candidates = [
        pkg_dir / "fonts",                # /mount/src/fp/fonts
        repo_root / "fonts",              # /mount/src/fonts
        cwd / "fonts",                    # CWD/fonts（ローカル実行向け）
        Path(env_dir) if env_dir else None,
    ]
    # None を除外し、重複も除去
    uniq = []
    for d in candidates:
        if d and d not in uniq:
            uniq.append(d)
    return uniq

def _detect_font_dir() -> Path:
    """候補を総当りして、両フォントが存在するディレクトリを返す"""
    tried = []
    for d in _font_dir_candidates():
        tried.append(str(d))
        if _both_exist(d):
            return d
    # 見つからなければ詳細を出して明確に落とす
    raise FileNotFoundError(
        "NotoSansJP TTF not found in any known locations.\n"
        + "Tried:\n- " + "\n- ".join(tried) + "\n"
        + "Expected files:\n- " + "\n- ".join(FONT_FILENAMES) + "\n"
        + "Hint: 配置はプロジェクト直下 'fonts/' か、パッケージ直下 'fp/fonts/' にしてください。"
    )

# 実際に使うフォントディレクトリ（存在確認済み）
FONT_DIR = str(_detect_font_dir())

def _font_path(filename: str) -> str:
    p = Path(FONT_DIR) / filename
    if not p.exists():
        raise FileNotFoundError(f"Font file not found: {p}")
    return str(p)

def register_fonts(pdf: FPDF) -> FPDF:
    """NotoSansJP Regular/Bold を Unicode サブセットで登録"""
    regular_path = _font_path("NotoSansJP-Regular.ttf")
    bold_path    = _font_path("NotoSansJP-Bold.ttf")
    pdf.add_font("NotoSans", "", regular_path, uni=True)
    pdf.add_font("NotoSans", "B", bold_path,    uni=True)
    return pdf

def create_pdf_with_fonts() -> FPDF:
    """A4mmのFPDFインスタンスにフォントを登録して返す"""
    pdf = FPDF(unit="mm", format="A4")
    register_fonts(pdf)
    return pdf

# ==============================
# 便利ヘルパ（既存互換）
# ==============================
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