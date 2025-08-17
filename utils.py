# utils.py
import os
from pathlib import Path
from fpdf import FPDF

# ===== フォントの絶対パスを固定 =====
# /mount/src/fp/utils.py → parents[1] が /mount/src
PROJECT_ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = PROJECT_ROOT / "fonts"                      # /mount/src/fonts
FONT_REGULAR = FONT_DIR / "NotoSansJP-Regular.ttf"
FONT_BOLD    = FONT_DIR / "NotoSansJP-Bold.ttf"

def _assert_fonts_exist() -> None:
    missing = [p for p in (FONT_REGULAR, FONT_BOLD) if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "日本語フォントが見つかりません。\n"
            + "\n".join(f"- {p}" for p in missing)
            + f"\n想定ディレクトリ: {FONT_DIR}"
        )

def register_fonts(pdf: FPDF) -> FPDF:
    _assert_fonts_exist()
    # 旧fpdf / fpdf2 どちらでも動く書式（uni=True は旧fpdf向け、fpdf2でも許容）
    pdf.add_font("NotoSans", "", str(FONT_REGULAR), uni=True)
    pdf.add_font("NotoSans", "B", str(FONT_BOLD),    uni=True)
    return pdf

def create_pdf_with_fonts() -> FPDF:
    pdf = FPDF(unit="mm", format="A4")
    register_fonts(pdf)
    return pdf