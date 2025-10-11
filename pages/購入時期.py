# fp/pages/購入時期.py
# 404で落ちない日本語PDF：IPAexフォントを公式ZIPから自動DL→展開→登録
import io
import os
import zipfile
import tempfile
from pathlib import Path

import requests
import streamlit as st
from fpdf import FPDF

# =========================
# フォント（IPAexに全面切替／自動DL＆展開）
# =========================
# 書き込み可能な一時領域にフォントを置く（Streamlit Cloudでも安全）
FONT_DIR = Path(tempfile.gettempdir()) / "fonts_fp"
FONT_DIR.mkdir(parents=True, exist_ok=True)

# ここを上書き
IPAEX_G_ZIP = "https://moji.or.jp/wp-content/ipafont/IPAexfont/ipaexg00401.zip"  # ゴシック
IPAEX_M_ZIP = "https://moji.or.jp/wp-content/ipafont/IPAexfont/ipaexm00401.zip"  # 明朝

# 保存する実体ファイル名（拡張子は .ttf）
FONT_GOTHIC_PATH = FONT_DIR / "IPAexGothic.ttf"   # 例: ipaexg.ttf をこの名前で保存
FONT_MINCHO_PATH = FONT_DIR / "IPAexMincho.ttf"   # 例: ipaexm.ttf をこの名前で保存


def _download_and_extract_ttf(zip_url: str, member_suffix: str, save_path: Path):
    """
    zip_url からzipを取得→中の *.ttf を抽出して save_path に保存
    member_suffix 例: 'ipaexg.ttf', 'ipaexm.ttf'
    """
    # ★ 追加：保存先の親ディレクトリを必ず作成（堅牢化）
    save_path.parent.mkdir(parents=True, exist_ok=True)

    resp = requests.get(zip_url, timeout=30)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        ttf_members = [n for n in zf.namelist() if n.lower().endswith(member_suffix)]
        if not ttf_members:
            raise RuntimeError(f"TTF not found in {zip_url}")
        with zf.open(ttf_members[0]) as src, open(save_path, "wb") as dst:
            dst.write(src.read())


def _ensure_fonts():
    """
    IPAexゴシック/明朝 をローカルに用意。なければ自動DL。
    ※ FPDF の 'B' スタイル用は同一TTFを登録（見た目は太字化されないがエラーは出ない）
    """
    if not FONT_GOTHIC_PATH.exists():
        _download_and_extract_ttf(IPAEX_G_ZIP, "ipaexg.ttf", FONT_GOTHIC_PATH)
    if not FONT_MINCHO_PATH.exists():
        _download_and_extract_ttf(IPAEX_M_ZIP, "ipaexm.ttf", FONT_MINCHO_PATH)


def _register_jp_fonts(pdf: FPDF):
    """
    FPDFインスタンスに日本語フォントを登録。
    使用例: pdf.set_font("IPAexGothic", size=12)
    """
    _ensure_fonts()
    # ゴシック
    pdf.add_font("IPAexGothic", "", str(FONT_GOTHIC_PATH), uni=True)
    pdf.add_font("IPAexGothic", "B", str(FONT_GOTHIC_PATH), uni=True)  # Bも同一TTFを割当
    # 明朝（未使用でも登録しておくと切替可能）
    pdf.add_font("IPAexMincho", "", str(FONT_MINCHO_PATH), uni=True)
    pdf.add_font("IPAexMincho", "B", str(FONT_MINCHO_PATH), uni=True)

# =========================
# ローン計算ユーティリティ（万円ベース）
# =========================
def monthly_payment(principal_man: float, years: int, annual_rate_pct: float) -> float:
    """元利均等: 万円単位で返す"""
    n = years * 12
    if n <= 0:
        return 0.0
    r = (annual_rate_pct / 100.0) / 12.0
    P = principal_man
    if r == 0:
        return P / n
    return P * r * (1 + r) ** n / ((1 + r) ** n - 1)


def total_payment(principal_man: float, years: int, annual_rate_pct: float) -> float:
    m = monthly_payment(principal_man, years, annual_rate_pct)
    return m * years * 12


def remaining_balance_at_k(principal_man: float, years: int, annual_rate_pct: float, k_months: int) -> float:
    """kヶ月返済後の残高（万円）"""
    n = years * 12
    if n <= 0:
        return 0.0
    k = max(0, min(k_months, n))
    r = (annual_rate_pct / 100.0) / 12.0
    P = principal_man
    if r == 0:
        # ゼロ金利は単純按分
        return P * (1 - k / n)
    factor = (1 + r) ** n
    return P * ((factor - (1 + r) ** k) / (factor - 1))


# 価格の将来値（複利）
def future_price_man(price_now_man: float, growth_pct_per_year: float, years_wait: int) -> float:
    g = growth_pct_per_year / 100.0
    return price_now_man * ((1 + g) ** years_wait)


# =========================
# Streamlit UI
# =========================
st.set_page_config(page_title="購入時期の比較シミュレーション", layout="wide")
st.title("🏠 購入時期シミュレーション（今 vs 何年後）")

colL, colR = st.columns(2)

with colL:
    st.subheader("今、購入する場合")
    age_now = st.number_input("現在の年齢（歳）", value=32, step=1)
    price_now_man = st.number_input("購入物件価格（万円）", value=3000, step=10)
    cash_now_man = st.number_input("現在の自己資金（万円）", value=300, step=10)
    years_now = st.number_input("ローン返済期間（年）", value=35, step=1)
    rate_now = st.number_input("ローン金利（年利 %）", value=1.0, format="%.3f", step=0.05)

with colR:
    st.subheader("将来、購入する場合")
    wait_years = st.number_input("何年後に購入？（年）", value=3, step=1)
    monthly_save_man = st.number_input("その間の毎月積立額（万円／月）", value=3.0, format="%.1f", step=0.1)
    growth_pct = st.number_input("物件価格上昇率（年率 %）", value=0.0, format="%.2f", step=0.1)
    rate_future = st.number_input("将来購入時のローン金利（年利 %）", value=2.0, format="%.3f", step=0.05)
    years_future = st.number_input("将来購入時の返済期間（年）", value=35, step=1)
    rent_until_man = st.number_input("購入までの毎月の家賃（万円／月）", value=8.0, format="%.1f", step=0.1)

# =========================
# 計算（すべて万円単位）
# =========================
# 今
down_now_man = max(0.0, min(cash_now_man, price_now_man))
loan_now_man = max(0.0, price_now_man - down_now_man)
loan_total_now_man = total_payment(loan_now_man, int(years_now), float(rate_now))
rent_now_man = 0.0
total_cost_now_man = down_now_man + loan_total_now_man + rent_now_man

# 将来
accum_save_man = monthly_save_man * 12 * wait_years
down_future_man = cash_now_man + accum_save_man
price_future_man = future_price_man(price_now_man, growth_pct, int(wait_years))
loan_future_man = max(0.0, price_future_man - down_future_man)
loan_total_future_man = total_payment(loan_future_man, int(years_future), float(rate_future))
rent_total_future_man = rent_until_man * 12 * wait_years
total_cost_future_man = down_future_man + loan_total_future_man + rent_total_future_man

# 60歳時のローン残債
months_to_60_now = max(0, int((60 - age_now) * 12))
months_to_60_future = max(0, int((60 - (age_now + wait_years)) * 12))
remain_now_man = remaining_balance_at_k(loan_now_man, int(years_now), float(rate_now), months_to_60_now)
remain_future_man = remaining_balance_at_k(loan_future_man, int(years_future), float(rate_future), months_to_60_future)

# 差分・1日あたり
diff_man = total_cost_future_man - total_cost_now_man
days = max(1, int(wait_years * 365))
loss_per_day_yen = diff_man * 10000 / days  # 円/日

# =========================
# 表示
# =========================
st.markdown("---")
st.subheader("結果サマリー（万円）")

c1, c2, c3 = st.columns([1.2, 1, 1])
with c1:
    st.markdown("#### 今、購入する場合")
    st.metric("購入時自己資金", f"{down_now_man:,.0f} 万円")
    st.caption("うち積立額 ー 万円")
    st.metric("ローン返済額（総額）", f"{loan_total_now_man:,.0f} 万円")
    st.metric("家賃支払い額", f"ー 万円")
    st.metric("生涯住居費総額（合計）", f"{total_cost_now_man:,.0f} 万円")
    st.metric("60歳時のローン残債額", f"{remain_now_man:,.0f} 万円")

with c2:
    st.markdown("#### 将来、購入する場合")
    st.metric("購入時自己資金", f"{down_future_man:,.0f} 万円")
    st.caption(f"うち積立額 {accum_save_man:,.0f} 万円")
    st.metric("ローン返済額（総額）", f"{loan_total_future_man:,.0f} 万円")
    st.metric("家賃支払い額（購入まで）", f"{rent_total_future_man:,.0f} 万円")
    st.metric("生涯住居費総額（合計）", f"{total_cost_future_man:,.0f} 万円")
    st.metric("60歳時のローン残債額", f"{remain_future_man:,.0f} 万円")

with c3:
    st.markdown("#### 差分")
    cheaper = "今、購入する方が" if diff_man > 0 else "将来、購入する方が"
    st.metric("どちらが有利？", f"{cheaper} {abs(diff_man):,.0f} 万円有利")
    st.caption(f"1日あたりの差額（概算）: {loss_per_day_yen:,.0f} 円/日")

st.markdown("---")

# =========================
# PDF 出力
# =========================
def build_pdf_bytes() -> bytes:
    """
    既存UIの結果値をPDF化（日本語フォントはIPAex）
    """
    _ensure_fonts()
    pdf = FPDF(unit="mm", format="A4")
    _register_jp_fonts(pdf)
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()

    # タイトル
    pdf.set_font("IPAexGothic", "B", 16)
    pdf.cell(0, 10, "購入時期シミュレーション（今 vs 将来）", ln=1)

    # 前提
    pdf.set_font("IPAexGothic", "", 11)
    pdf.cell(0, 8, f"前提：物件価格（現在） {price_now_man:,.0f} 万円 / 上昇率 {growth_pct:.2f}% / 待機 {wait_years} 年", ln=1)
    pdf.ln(2)

    # 表
    def row(label, now_val, fut_val):
        pdf.set_font("IPAexGothic", "B", 11)
        pdf.cell(70, 8, label, 1, 0, "L")
        pdf.set_font("IPAexGothic", "", 11)
        pdf.cell(60, 8, now_val, 1, 0, "R")
        pdf.cell(60, 8, fut_val, 1, 1, "R")

    pdf.set_font("IPAexGothic", "B", 12)
    pdf.cell(70, 8, "", 1, 0)
    pdf.cell(60, 8, "今、購入", 1, 0, "C")
    pdf.cell(60, 8, "将来、購入", 1, 1, "C")

    row("購入時自己資金", f"{down_now_man:,.0f} 万円", f"{down_future_man:,.0f} 万円")
    row("（うち積立）", "ー 万円", f"{accum_save_man:,.0f} 万円")
    row("ローン返済額（総額）", f"{loan_total_now_man:,.0f} 万円", f"{loan_total_future_man:,.0f} 万円")
    row("家賃支払い額", "ー 万円", f"{rent_total_future_man:,.0f} 万円")
    row("生涯住居費総額", f"{total_cost_now_man:,.0f} 万円", f"{total_cost_future_man:,.0f} 万円")
    row("60歳時の残債", f"{remain_now_man:,.0f} 万円", f"{remain_future_man:,.0f} 万円")

    pdf.ln(4)
    pdf.set_font("IPAexGothic", "B", 12)
    if diff_man > 0:
        msg = f"今、購入する方が {diff_man:,.0f} 万円 有利（1日あたり約 {loss_per_day_yen:,.0f} 円）"
    else:
        msg = f"将来、購入する方が {abs(diff_man):,.0f} 万円 有利（1日あたり約 {abs(loss_per_day_yen):,.0f} 円）"
    pdf.multi_cell(0, 8, msg)

    # 一旦ファイルに出してから読む（エンコード問題回避）
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        tmp.flush()
        tmp.seek(0)
        data = tmp.read()
    return data


if st.button("📄 PDFを作成（日本語フォント内蔵）"):
    try:
        pdf_bytes = build_pdf_bytes()
        st.download_button(
            "📥 PDFダウンロード",
            data=pdf_bytes,
            file_name="購入時期シミュレーション.pdf",
            mime="application/pdf",
        )
        st.success("PDFを生成しました。")
    except Exception as e:
        st.error(f"PDF生成エラー: {e}")

# ===== 公式LINEバナー（×で閉じられる・PC/スマホ両対応）=====
import urllib.parse as _url

def render_line_banner():
    # 1) セッションフラグ初期化
    if "line_banner_closed" not in st.session_state:
        st.session_state.line_banner_closed = False

    # 2) ?close_banner=1 を検知して閉じる
    try:
        qp = st.query_params
        close_flag = str(qp.get("close_banner", "0")) == "1"
        qp_dict = dict(qp)  # 既存のクエリ保持用
    except Exception:
        qp = st.experimental_get_query_params()
        close_flag = (qp.get("close_banner", ["0"])[0] == "1")
        qp_dict = {k: (v[0] if isinstance(v, list) else v) for k, v in qp.items()}

    if close_flag:
        st.session_state.line_banner_closed = True

    if st.session_state.line_banner_closed:
        return  # 以降レンダしない

    # 3) × クリック時のURL（既存クエリを保持して close_banner=1 だけ付与）
    qp_dict = {k: (v if not isinstance(v, list) else v[0]) for k, v in qp_dict.items()}
    qp_dict["close_banner"] = "1"
    qs = _url.urlencode(qp_dict)
    close_url = "?" + qs if qs else "?close_banner=1"

    # 4) バナー描画（×はリンク。JS不要）
    st.markdown(f"""
    <style>
    .line-banner-wrap {{
      position: fixed;
      bottom: 100px; right: 18px; z-index: 9999;
    }}
    .line-banner {{
      background: #06C755; color: #fff;
      padding: 14px 18px 20px; border-radius: 12px;
      box-shadow: 0 4px 10px rgba(0,0,0,0.25);
      font-size: 15px; text-align: center; position: relative;
    }}
    .line-banner:hover {{ transform: scale(1.02); background:#05b34d; }}
    .line-banner .ttl {{ font-size: 17px; font-weight: 800; line-height: 1.4; }}
    .line-banner .id  {{ font-size: 20px; font-weight: 900; margin: 6px 0 6px; }}
    .line-banner img  {{
      width: 130px; display:block; margin: 8px auto 10px;
      border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.3);
      background:#fff;
    }}
    .line-banner .cta {{ display:inline-block; font-weight: 800; text-decoration: underline; color:#fff; }}
    .line-banner .close-btn {{
      position:absolute; top:6px; right:10px; width:24px; height:24px;
      border-radius:50%; background: rgba(0,0,0,0.25);
      color:#fff; text-align:center; line-height:24px;
      font-size:16px; font-weight:700; text-decoration:none;
    }}
    .line-banner .close-btn:hover {{ background: rgba(0,0,0,0.4); }}
    @media (max-width: 768px){{
      .line-banner-wrap {{ bottom: 100px; right: 14px; }}
      .line-banner {{ padding: 12px 14px 18px; }}
      .line-banner img {{ width: 110px; }}
      .line-banner .id {{ font-size: 18px; }}
    }}
    </style>

    <div class="line-banner-wrap" id="line-banner">
      <div class="line-banner" role="region" aria-label="LINE公式バナー">
        <a class="close-btn" href="{close_url}" aria-label="バナーを閉じる">×</a>
        <a href="https://lin.ee/m40HEqN" target="_blank" rel="noopener" style="text-decoration:none; color:#fff;">
          <div class="ttl">📲 シミュレーション利用は<br>LINEで簡単・不動産相談</div>
          <div class="id">LINE ID：@fudo3</div>
          <img src="https://qr-official.line.me/gs/M_277qthwd_GW.png?oat_content=qr" alt="LINE公式QRコード">
          <span class="cta">▶ 公式LINEで相談する</span>
        </a>
      </div>
    </div>
    """, unsafe_allow_html=True)

# どこかで呼び出す（各ページの末尾など）
render_line_banner()
