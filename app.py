"""Streamlit UI。検索ワード入力・実行ボタン・進捗表示・結果URL表示を行う。"""
import logging

import streamlit as st

from main import run

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

st.set_page_config(page_title="インフルエンサーDB自動収集", page_icon="📊")
st.title("インフルエンサーDB自動収集システム")

keyword = st.text_input("検索キーワード（ゲームタイトル）", placeholder="例: Subnautica2")
run_button = st.button("収集開始", type="primary", disabled=not keyword)

if run_button:
    status = st.empty()
    try:
        status.info("収集中... チャンネルを検索しています")
        url = run(keyword)
        status.success("完了しました")
        st.markdown(f"[スプレッドシートを開く]({url})")
    except Exception as e:
        logger.error("UIからの実行中にエラーが発生しました: %s", e)
        status.error(f"エラーが発生しました: {e}")


# 簡易ユニットテスト（実行可能コードは不要、方針のみ記載）
# - keyword未入力時に実行ボタンがdisabledになることを確認する
# - run()が例外を投げた場合にスタックトレースを表示せずエラーメッセージのみ表示することを確認する
