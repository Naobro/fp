# fp/pages/諸費用.py
# 諸費用明細（完全再現版）
# - 添付PDFの形式を忠実再現
# - 仲介手数料は契約時/決済時に分割入力
# - 金利は小数第3位まで入力・保存・表示

import os, re, io, zipfile, tempfile
from pathlib import Path
import streamlit as st
import requests
from fpdf import FPDF
from client_portal import now_iso, get_sb

SB = get_sb()

# ============ データロード ============
def load_saved_data(client_id: str):
    if not SB:
        return None
    try:
        res = (
            SB.table("fees_detail")
            .select("*")
            .eq("client_id", client_id)
            .order("saved_at", desc=True)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]
    except Exception as e:
        st.warning(f"保存データ読み込み失敗: {e}")
    return None

client_id = st.query_params.get("client", "unknown")
saved = load_saved_data(client_id)
if saved:
    for k, v in saved.items():
        st.session_state[k] = v

# ============ 基本設定 ============
st.set_page_config(page_title="資金計画書（諸費用明細）", layout="centered")
st.title("資金計画書（諸費用明細）")

# ============ フォント ============
def _pick_font_dir():
    for d in [Path.cwd()/"fonts_runtime", Path(tempfile.gettempdir())/"fonts_runtime"]:
        try:
            d.mkdir(parents=True, exist_ok=True)
            (d/".t").write_text("ok"); (d/".t").unlink()
            return d
        except: continue
    return Path(tempfile.mkdtemp(prefix="fonts_runtime_"))

FONT_DIR=_pick_font_dir()
IPAEX_G_ZIP="https://moji.or.jp/wp-content/ipafont/IPAexfont/ipaexg00401.zip"
FONT_PATH=FONT_DIR/"IPAexGothic.ttf"
def _ensure_font():
    if not FONT_PATH.exists():
        r=requests.get(IPAEX_G_ZIP); r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            for n in zf.namelist():
                if n.lower().endswith("ipaexg.ttf"):
                    with zf.open(n) as src, open(FONT_PATH,"wb") as dst: dst.write(src.read())
def _register_font(pdf): _ensure_font(); pdf.add_font("IPAexGothic","",str(FONT_PATH),uni=True)

# ============ 関数 ============
def fmt_jpy(v): return f"{int(v):,} 円"
def number_input_commas(label,v,step=1):
    s=st.text_input(label,f"{v:,}"); s=re.sub(r"[^\d]","",s)
    try:return int(s)
    except:return v
def monthly_payment(a,y,r):
    n=y*12; rr=r/100/12
    if rr==0: return int(a/n)
    return int(a*rr*(1+rr)**n/((1+rr)**n-1))
def calc_stamp_tax(p):
    if p<=5_000_000:return 5_000
    if p<=10_000_000:return 10_000
    if p<=50_000_000:return 10_000
    if p<=100_000_000:return 30_000
    if p<=500_000_000:return 60_000
    if p<=1_000_000_000:return 160_000
    return 320_000

# ============ 入力 ============
st.session_state["customer_name"]=st.text_input("お客様名",st.session_state.get("customer_name",""))
st.session_state["property_name"]=st.text_input("物件名",st.session_state.get("property_name",""))
price_man=st.number_input("物件価格（万円）",value=7880,step=10)
property_price=int(price_man)*10_000
deposit=number_input_commas("手付金（円）",4_000_000)
base_rate=st.number_input("基準金利（年%）",value=0.880,step=0.001,format="%.3f")
base_years=35
kanri_month=number_input_commas("管理費・修繕積立（月額円）",18_000)

# ============ 各費用 ============
stamp_fee=calc_stamp_tax(property_price)
regist_fee=number_input_commas("登記費用（円）",405_600)
tax_clear=number_input_commas("精算金（円）",50_000)
display_fee=number_input_commas("表示登記（円）",0)
loan_fee=number_input_commas("銀行事務手数料（円）",int(property_price*0.022))
fire_fee=number_input_commas("火災保険（円）",100_000)
tekigo_fee=number_input_commas("適合証明書（円）",0)
broker_contract=number_input_commas("仲介手数料（契約時・円）",1_333_200)
broker_decision=number_input_commas("仲介手数料（決済時・円）",1_333_200)
broker_total=broker_contract+broker_decision
move_fee=number_input_commas("引越し費用（円）",100_000)

# ============ 明細テーブル ============
cost_rows=[
["◆ 登記費用・税金・精算金等","","",""],
["契約書 印紙代",fmt_jpy(stamp_fee),"契約時","電子契約で削減可能"],
["登記費用",fmt_jpy(regist_fee),"決済時","司法書士報酬＋登録免許税"],
["精算金",fmt_jpy(tax_clear),"決済時","固都税・管理費等（日割り精算）"],
["表示登記",fmt_jpy(display_fee),"決済時","新築戸建の場合必要（目安10万円）"],
["◆ 金融機関・火災保険","","",""],
["銀行事務手数料",fmt_jpy(loan_fee),"決済時","借入金額概算として物件価格×2.2%"],
["火災保険",fmt_jpy(fire_fee),"決済時","5年の火災保険（概算）"],
["適合証明書",fmt_jpy(tekigo_fee),"相談","フラット35の場合 必須"],
["◆ 仲介会社（TERASS）","","",""],
["仲介手数料（契約時）",fmt_jpy(broker_contract),"契約時","物件価格×3%＋6万＋税"],
["仲介手数料（決済時）",fmt_jpy(broker_decision),"決済時","物件価格×3%＋6万＋税"],
["◆ 追加工事・引越し","","",""],
["引越し費用",fmt_jpy(move_fee),"入居時","距離・荷物量による"],
]

total_expenses=sum(int(r[1].replace(" 円","").replace(",","")) for r in cost_rows if "◆" not in r[0])
total=property_price+total_expenses
need=int(deposit+stamp_fee+broker_contract)

loan_full=property_price+total_expenses
loan_only=property_price

# ============ ③④入力 ============
st.markdown("#### ③ 入力A（手動）")
colA1,colA2,colA3=st.columns(3)
with colA1:
    loanA_man=st.number_input("借入金額（万円：③）",value=int(price_man),step=10)
    loanA=int(loanA_man)*10_000
with colA2:
    rateA=st.number_input("金利（③）",value=base_rate,step=0.001,format="%.3f")
with colA3:
    yearA=st.number_input("年数（③）",value=35,step=1)

st.markdown("#### ④ 入力B（手動）")
colB1,colB2,colB3=st.columns(3)
with colB1:
    loanB_man=st.number_input("借入金額（万円：④）",value=int(price_man),step=10)
    loanB=int(loanB_man)*10_000
with colB2:
    rateB=st.number_input("金利（④）",value=base_rate,step=0.001,format="%.3f")
with colB3:
    yearB=st.number_input("年数（④）",value=35,step=1)

# ============ 支払例 ============
m_full=monthly_payment(loan_full,base_years,base_rate)
m_only=monthly_payment(loan_only,base_years,base_rate)
mA=monthly_payment(loanA,yearA,rateA)
mB=monthly_payment(loanB,yearB,rateB)

# ============ PDF ============
def build_pdf():
    pdf=FPDF(unit="mm",format="A4"); _register_font(pdf)
    pdf.set_left_margin(13); pdf.set_top_margin(13)
    pdf.add_page(); pdf.set_font("IPAexGothic","",11)
    if st.session_state["customer_name"]:
        pdf.set_font("IPAexGothic","B",12)
        pdf.cell(0,8,f"{st.session_state['customer_name']} 様",ln=1)
    pdf.set_font("IPAexGothic","B",11)
    pdf.cell(0,7,f"物件名：{st.session_state['property_name']}",ln=1)
    pdf.cell(0,7,f"物件価格：{fmt_jpy(property_price)}",ln=1)
    pdf.cell(0,7,f"手付金：{fmt_jpy(deposit)}（物件価格の5%前後／契約時振込・物件価格に充当）",ln=1)
    pdf.ln(2)

    # テーブル
    headers=["項目","金額","支払時期","説明"]; w=[46,34,33,77]
    pdf.set_font("IPAexGothic","B",10); pdf.set_fill_color(220,230,250)
    for i,h in enumerate(headers): pdf.cell(w[i],7,h,1,0,"C",1)
    pdf.ln(7); pdf.set_font("IPAexGothic","",10)
    for r in cost_rows:
        if "◆" in r[0]:
            pdf.set_font("IPAexGothic","B",10)
            pdf.cell(sum(w),7,r[0],1,1); pdf.set_font("IPAexGothic","",10)
        else:
            pdf.cell(w[0],7,r[0],1,0)
            pdf.cell(w[1],7,r[1],1,0,"R")
            pdf.cell(w[2],7,r[2],1,0,"C")
            pdf.cell(w[3],7,r[3],1,1)
    pdf.ln(2)

    # 備考
    note="※諸費用は全て目安です。物件・契約形態・条件により変動します\n登記費用・火災保険・精算金等も見積取得後に確定します\n①②は『基準金利』を使用し、年数は35年固定で試算しています\n③④は借入金額・金利・返済期間を手動入力して試算します\n銀行事務手数料は概算として『物件価格×2.2%』で計上しています。"
    pdf.set_font("IPAexGothic","",9.5); pdf.multi_cell(0,5,note)
    pdf.ln(2)

    # 合計
    pdf.set_font("IPAexGothic","B",11)
    pdf.cell(45,8,"諸費用合計",1,0,"C",1)
    pdf.cell(50,8,fmt_jpy(total_expenses),1,0,"R",1)
    pdf.cell(55,8,"総合計（物件＋諸費用）",1,0,"C",1)
    pdf.cell(40,8,fmt_jpy(total),1,1,"R",1)
    pdf.ln(2)

    # 支払例
    pdf.set_font("IPAexGothic","B",11)
    pdf.cell(0,7,f"（支払例）①②は基準金利{base_rate:.3f}%／{base_years}年、③④は手動入力条件",ln=1)
    headers2=["借入パターン","借入金額","月々返済額","総額（管理費含)"]; w2=[90,30,35,35]
    pdf.set_font("IPAexGothic","B",10); pdf.set_fill_color(220,240,255)
    for i,h in enumerate(headers2): pdf.cell(w2[i],7,h,1,0,"C",1)
    pdf.ln(7); pdf.set_font("IPAexGothic","",10)
    rows=[["①自己資金0（物件＋諸費用フル）",loan_full,m_full,m_full+kanri_month],
          ["②諸費用のみ自己資金（物件のみ借入）",loan_only,m_only,m_only+kanri_month],
          [f"③A 金利{rateA:.3f}%／{yearA}年",loanA,mA,mA+kanri_month],
          [f"④B 金利{rateB:.3f}%／{yearB}年",loanB,mB,mB+kanri_month]]
    for r in rows:
        pdf.cell(w2[0],8,r[0],1,0,"L")
        pdf.cell(w2[1],8,fmt_jpy(r[1]),1,0,"R")
        pdf.cell(w2[2],8,fmt_jpy(r[2]),1,0,"R")
        pdf.cell(w2[3],8,fmt_jpy(r[3]),1,1,"R")

    pdf.cell(0,8,f"契約時必要資金（手付金＋印紙代＋仲介半金）：{fmt_jpy(need)}",ln=1)
    pdf.ln(3)
    pdf.set_font("IPAexGothic","",9)
    pdf.cell(0,5,"西山　直樹 / Naoki Nishiyama",ln=1)
    pdf.cell(0,5,"TERASS, Inc.",ln=1)
    pdf.cell(0,5,"〒105-0001 東京都港区虎ノ門二丁目2番1号 住友不動産虎ノ門タワー13階",ln=1)
    pdf.cell(0,5,"TEL: 090-4399-2480 / FAX: 03-6369-3864",ln=1)
    pdf.cell(0,5,"Email: naoki.nishiyama@terass.com",ln=1)
    pdf.cell(0,5,"LINE：naokiwm",ln=1)
    out=pdf.output(dest="S")
    return out.encode("latin-1") if isinstance(out,str) else bytes(out)

pdf_bytes=build_pdf()

if st.button("💾 諸費用データを保存"):
    payload={
        "customer_name":st.session_state["customer_name"],
        "property_name":st.session_state["property_name"],
        "property_price":property_price,
        "deposit":deposit,
        "total_expenses":total_expenses,
        "total":total,
        "monthly_full":m_full,
        "monthly_only":m_only,
        "monthly_A":mA,
        "monthly_B":mB,
        "rateA":rateA,
        "rateB":rateB,
        "saved_at":now_iso(),
    }
    SB.table("fees_detail").upsert({**payload,"client_id":client_id},on_conflict="client_id").execute()
    st.success("保存しました ✅")

st.download_button(
    "📄 資金計画書.pdf ダウンロード",
    data=pdf_bytes,
    file_name=f"{st.session_state['property_name']}　諸費用明細.pdf",
    mime="application/pdf",
)
