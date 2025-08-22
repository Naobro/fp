# pages/2_MUFG.py
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="三菱UFJ銀行｜住宅ローン", page_icon="🏦", layout="wide")

# タイトルが切れない最小余白
st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 0.6rem;}
</style>
""", unsafe_allow_html=True)

# ローカルPDFパス
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "mufg"

PDF_DESC   = ASSETS / "商品説明.pdf"
PDF_NOTICE = ASSETS / "入力時の注意点.pdf"

def load_bytes(p: Path) -> bytes:
    return p.read_bytes()

st.title("三菱UFJ銀行｜住宅ローン")

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