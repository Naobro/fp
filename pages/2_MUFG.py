# pages/2_MUFG.py
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="三菱UFJ銀行｜住宅ローン", page_icon="🏦", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 0.6rem;}
</style>
""", unsafe_allow_html=True)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "mufg"

PDF_DESC   = ASSETS / "商品説明.pdf"
PDF_NOTICE = ASSETS / "入力時の注意点.pdf"

def load_bytes(p: Path) -> bytes:
    return p.read_bytes()

st.title("三菱UFJ銀行｜住宅ローン")

st.subheader("商品説明（PDF）")
st.download_button("📥 三菱UFJ｜商品説明", data=load_bytes(PDF_DESC), file_name="三菱UFJ_商品説明.pdf", mime="application/pdf")

st.subheader("事前審査（オンライン）")
st.link_button("🔗 事前審査ログイン（仲介向け）",
               "https://web.smart-entry-tab.jp/setWeb/estate/login/?realtor_cd=HGSHW-04384")

st.subheader("入力時の注意点（PDF）")
st.download_button("📥 入力時の注意点", data=load_bytes(PDF_NOTICE), file_name="三菱UFJ_入力時の注意点.pdf", mime="application/pdf")

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