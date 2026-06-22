"""エントリーポイント（CLI実行用）。

使用例:
    python main.py "Subnautica2"
"""
import argparse
import logging
import sys

from analyzers.claude_analyzer import ClaudeAnalyzer
from collectors.youtube import YouTubeCollector
from writers.sheet_writer import SheetWriter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run(keyword: str) -> str:
    """1キーワードに対して収集・分析・書き込みを実行し、スプレッドシートURLを返す。"""
    collector = YouTubeCollector()
    analyzer = ClaudeAnalyzer()

    logger.info("収集開始: %s", keyword)
    raw_list = collector.fetch(keyword)
    normalized = [collector.normalize(raw) for raw in raw_list]
    collector.save_json(normalized, keyword)
    logger.info("収集完了: %d件", len(normalized))

    logger.info("分析開始")
    analyzed = [analyzer.analyze_influencer(influencer, keyword) for influencer in normalized]
    collector.save_json(analyzed, keyword)
    logger.info("分析完了")

    logger.info("スプレッドシート書き込み開始")
    writer = SheetWriter()
    url = writer.write(analyzed, keyword)
    logger.info("書き込み完了: %s", url)

    return url


def main() -> None:
    parser = argparse.ArgumentParser(description="ゲームタイトルをキーワードにYouTubeインフルエンサーを収集・分析する")
    parser.add_argument("keyword", help="検索キーワード（ゲームタイトル）")
    args = parser.parse_args()

    try:
        url = run(args.keyword)
        print(url)
    except Exception as e:
        logger.error("実行中にエラーが発生しました: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()


# 簡易ユニットテスト（実行可能コードは不要、方針のみ記載）
# - runがcollector.fetchから空リストが返った場合でも例外なく完了することを確認する
# - main()がrunの例外発生時にsys.exit(1)で終了することを確認する
