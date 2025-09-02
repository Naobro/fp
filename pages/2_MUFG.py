# pages/2_MUFG.py
import streamlit as st
from pathlib import Path
from utils.rates import month_label, get_base_rates_for_current_month

st.set_page_config(page_title="三菱UFJ銀行｜住宅ローン", page_icon="🏦", layout="wide")

# 余白・バナーCSS（SBIページと同じ見た目）
st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 0.6rem;}
.rate-banner {
  display: flex; flex-direction: column; gap: 6px;
  border: 1px solid #e5e7eb; border-radius: 12px;
  background: #fff; padding: 14px 16px; margin: 4px 0 14px 0;
}
.rate-banner .label { font-size: 1.0rem; color: #374151; }
.rate-banner .value { font-size: 2.2rem; font-weight: 800; color: #1b232a; line-height: 1.1; }
.rate-banner .note  { font-size: 0.95rem; color: #4b5563; }
</style>
""", unsafe_allow_html=True)

# ローカルPDFパス
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "mufg"
PDF_DESC   = ASSETS / "商品説明.pdf"
PDF_NOTICE = ASSETS / "入力時の注意点.pdf"

def load_bytes(p: Path) -> bytes:
    try:
        return p.read_bytes()
    except Exception:
        st.warning(f"ファイルが見つかりません：{p}")
        return b""

st.title("三菱UFJ銀行｜住宅ローン")

# ========= 基準金利の参照（統一フォーマット）=========
# 1) セッションの manual_rates を見る（なければ空dict）
manual = st.session_state.get("manual_rates")
if manual is None or not isinstance(manual, dict):
    # 2) JSONがあれば読む（シミュレーターで自動保存されている想定）
    manual = {}
    try:
        from json import loads
        json_path = Path("data/manual_rates.json")
        if json_path.exists():
            manual = loads(json_path.read_text(encoding="utf-8"))
    except Exception:
        manual = {}

# 3) 今月の基準（金庫の初期値）
base = get_base_rates_for_current_month()

# 4) 表示する金利：手動 > 今月基準
mufg_rate = (manual.get("三菱UFJ銀行")
             if isinstance(manual, dict) and "三菱UFJ銀行" in manual
             else base.get("三菱UFJ銀行"))

if mufg_rate is not None:
    st.markdown(
        f"""
        <div class="rate-banner">
          <div class="label">🗓 {month_label()} の基準金利（三菱UFJ銀行）</div>
          <div class="value">{float(mufg_rate):.3f}%</div>
          <div class="note">三大疾病団信など条件で加算</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ─ 商品説明（PDF 配布）
st.subheader("商品説明（PDF）")
st.download_button(
    "📥 三菱UFJ｜商品説明",
    data=load_bytes(PDF_DESC),
    file_name="三菱UFJ_商品説明.pdf",
    mime="application/pdf"
)

# ─ 事前審査（オンライン）
st.subheader("事前審査（オンライン）")
st.markdown("アクセスコードを **コピペ** して、下のボタン先で入力してください。")
st.code("w-mufg-hgshw001", language="text")
st.link_button(
    "🔗 事前審査ログイン（仲介向け）",
    "https://web.smart-entry-tab.jp/setWeb/estate/login/?realtor_cd=HGSHW-04384"
)

# ─ 入力時の注意点（テキストの追記＋PDF 配布）
st.subheader("入力時の注意点")
st.markdown(
    "担当者名：**西山 直樹**  /  メール：**naoki.nishiyama@terass.com**",
    unsafe_allow_html=True,
)
st.download_button(
    "📥 入力時の注意点（PDF）",
    data=load_bytes(PDF_NOTICE),
    file_name="三菱UFJ_入力時の注意点.pdf",
    mime="application/pdf"
)

# ─ 特殊項目（横長テーブル）
st.subheader("特殊項目")
st.markdown("""
<table style="width:100%; border-collapse:collapse; background:#fff;">
  <thead>
    <tr style="background:#FCF9F0;">
      <th style="border:1px solid #aaa; padding:12px; width:22%;">項目</th>
      <th style="border:1px solid #aaa; padding:12px; width:10%;">取扱</th>
      <th style="border:1px solid #aaa; padding:12px;">備考</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="border:1px solid #aaa; padding:12px;">諸費用</td>
      <td style="border:1px solid #aaa; padding:12px;" align="center">◯</td>
      <td style="border:1px solid #aaa; padding:12px;">物件価格の <b>110%</b> まで</td>
    </tr>
    <tr>
      <td style="border:1px solid #aaa; padding:12px;">リフォーム</td>
      <td style="border:1px solid #aaa; padding:12px;" align="center">◯</td>
      <td style="border:1px solid #aaa; padding:12px;">2本扱い／本体と同金利</td>
    </tr>
    <tr>
      <td style="border:1px solid #aaa; padding:12px;">買い替え</td>
      <td style="border:1px solid #aaa; padding:12px;" align="center">◯</td>
      <td style="border:1px solid #aaa; padding:12px;">可能だが、<b>原則 返済比率に含めて計算</b></td>
    </tr>
  </tbody>
</table>
""", unsafe_allow_html=True)

st.caption("※本ページは案内用ダイジェスト。正式条件は銀行公表資料をご確認ください。")