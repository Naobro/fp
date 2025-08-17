# utils.py
import os
import shutil
from pathlib import Path
from fpdf import FPDF

# === パス定義 ===
# /mount/src/fp/utils.py → parents[1] が /mount/src
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PKG_DIR      = Path(__file__).resolve().parent     # /mount/src/fp
PKG_FONTS    = PKG_DIR / "fonts"                   # 最終的にここに“必ず”置く
ROOT_FONTS   = PROJECT_ROOT / "fonts"              # 既にあなたが置いている場所

FONT_REGULAR_NAME = "NotoSansJP-Regular.ttf"
FONT_BOLD_NAME    = "NotoSansJP-Bold.ttf"

def _ensure_pkg_fonts():
    """
    フォントを /mount/src/fp/fonts に“必ず”用意する。
    1) 既にPKG_FONTSに両方あればOK
    2) なければ /mount/src/fonts からコピー
    3) それも無ければ CWD/fonts からコピー
    どこにも無ければ FileNotFoundError
    """
    PKG_FONTS.mkdir(parents=True, exist_ok=True)

    have_regular = (PKG_FONTS / FONT_REGULAR_NAME).exists()
    have_bold    = (PKG_FONTS / FONT_BOLD_NAME).exists()
    if have_regular and have_bold:
        return

    # 供給元候補
    sources = [
        ROOT_FONTS,
        Path.cwd() / "fonts",
    ]
    copied = False
    for src in sources:
        if not src.is_dir():
            continue
        sr = src / FONT_REGULAR_NAME
        sb = src / FONT_BOLD_NAME
        if sr.exists():
            shutil.copy2(sr, PKG_FONTS / FONT_REGULAR_NAME)
            copied = True
        if sb.exists():
            shutil.copy2(sb, PKG_FONTS / FONT_BOLD_NAME)
            copied = True
        # 揃ったら終了
        if (PKG_FONTS / FONT_REGULAR_NAME).exists() and (PKG_FONTS / FONT_BOLD_NAME).exists():
            return

    # ここまで来たら不足
    missing = []
    if not (PKG_FONTS / FONT_REGULAR_NAME).exists():
        missing.append(str(PKG_FONTS / FONT_REGULAR_NAME))
    if not (PKG_FONTS / FONT_BOLD_NAME).exists():
        missing.append(str(PKG_FONTS / FONT_BOLD_NAME))
    raise FileNotFoundError(
        "日本語フォントが見つかりません。\n"
        f"- 探索元: {ROOT_FONTS} , {Path.cwd()/'fonts'}\n"
        f"- 不足ファイル:\n  - " + "\n  - ".join(missing) + "\n"
        "※ リポジトリ直下 /fonts に NotoSansJP-Regular.ttf と NotoSansJP-Bold.ttf を置いてください。"
    )

# ここで “fp/fonts” にフォントを必ず用意
_ensure_pkg_fonts()

# === 登録用の絶対パス（fpdfはoutput時にこのパスをopenします）===
FONT_REGULAR = (PKG_FONTS / FONT_REGULAR_NAME).resolve()
FONT_BOLD    = (PKG_FONTS / FONT_BOLD_NAME).resolve()

def register_fonts(pdf: FPDF) -> FPDF:
    # 旧fpdf/ fpdf2 両対応の書式（uni=True は旧fpdf向け・fpdf2でも許容）
    pdf.add_font("NotoSans", "", str(FONT_REGULAR), uni=True)
    pdf.add_font("NotoSans", "B", str(FONT_BOLD),    uni=True)
    return pdf

def create_pdf_with_fonts() -> FPDF:
    pdf = FPDF(unit="mm", format="A4")
    register_fonts(pdf)
    return pdf