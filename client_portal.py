import streamlit as st

def render(client_id: str, sheet_url: str = "") -> None:
    # ----- ヘッダ（page_configはapp.py側で1回だけ設定する） -----
    st.title("お客さま専用ポータル")
    st.caption("このページから各機能に進めます。ブックマーク推奨。")

    with st.container():
        c1, c2 = st.columns([0.7, 0.3])
        with c1:
            st.markdown(f"**顧客コード**：`{client_id}`")
            st.write("※ 物件は未定です。まずはヒアリング → 仮審査 → 物件選定…の順で進めます。")
        with c2:
            if sheet_url:
                st.link_button("📄 共有スプレッドシートを開く", url=sheet_url, help="進捗・タスク管理用（外部リンク）")

    st.divider()

    # ----- 機能タイル（この表紙から各ページへ遷移） -----
    st.subheader("メニュー")

    def _goto(page_path: str):
        # client を保持したままアプリ内ページへ遷移
        try:
            st.query_params["client"] = client_id
        except Exception:
            st.experimental_set_query_params(client=client_id)
        st.switch_page(page_path)

    col = st.columns(4)

    with col[0]:
        st.markdown("#### 📊 住宅ローン提案（PDF）")
        st.write("各行・各銀行の返済額を比較し、提案書PDFを作成します。")
        if st.button("開く", key="open_mortgage"):
            _goto("pages/住宅ローン提案.py")

    with col[1]:
        st.markdown("#### 🧾 諸費用明細（PDF）")
        st.write("諸費用の概算→確定まで更新し続けられる明細PDF。")
        if st.button("開く", key="open_costs"):
            _goto("pages/諸費用明細.py")

    with col[2]:
        st.markdown("#### ✅ 必要書類チェック（PDF）")
        st.write("購入/売却の必要書類を整理し、チェック付きPDFを作成。")
        if st.button("開く", key="open_checklist"):
            _goto("pages/チェックリスト.py")

    with col[3]:
        st.markdown("#### 📝 事前審査 入力")
        st.write("仮審査のための基本情報入力フォーム。")
        if st.button("開く", key="open_preexam"):
            _goto("pages/事前審査入力.py")

    st.divider()

    # ----- 進め方（参考） -----
    with st.expander("進め方（参考）", expanded=False):
        st.markdown(
            """
1) **ヒアリング**  
2) **仮審査**（各行の事前審査）  
3) **物件選定**（内見・条件調整）  
4) **売買契約**  
5) **本審査**  
6) **金消**（金銭消費貸借契約）  
7) **決済**  
            """
        )

    # ----- フッター -----
    st.markdown("---")
    st.caption("このページのURLと顧客コードはお客様と担当者のみで共有しています。")
