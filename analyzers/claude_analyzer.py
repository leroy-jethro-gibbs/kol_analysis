"""Claude APIによるインフルエンサーのスコアリング・分析モジュール。"""
import json
import logging

import anthropic

import config

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT_TEMPLATE = """\
あなたはゲームマーケティングの専門アナリストです。
以下のYouTubeインフルエンサーの情報を分析し、JSON形式のみで回答してください。

検索キーワード（起用検討中のゲームタイトル）: {keyword}

チャンネル名: {channel_name}
登録者数: {subscriber_count}
動画タイトル一覧:
{title_list}

以下のキーを持つJSONオブジェクトのみを出力してください（説明文は不要）。
{{
  "main_genre": "動画タイトル群から推定した主ジャンル",
  "tone": "コンテンツのトーン（実況系・解説系・エンタメ系等）",
  "total_score": 0.0から10.0の総合スコア（小数点1位）,
  "title_fit_score": 0.0から10.0の検索キーワードとの適合度（小数点1位）,
  "organic_potential": "高・中・低のいずれか",
  "recommended_approach": "起用推奨アプローチ（100字以内）"
}}
"""


class ClaudeAnalyzer:
    def __init__(self, api_key: str | None = None):
        self.client = anthropic.Anthropic(api_key=api_key or config.ANTHROPIC_API_KEY)

    def analyze_influencer(self, influencer: dict, keyword: str) -> dict:
        """インフルエンサーデータを受け取り、Claude APIでジャンル・トーン・スコア等を生成する。"""
        prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            keyword=keyword,
            channel_name=influencer.get("channel_name"),
            subscriber_count=influencer.get("subscriber_count"),
            title_list="\n".join(f"- {t}" for t in influencer.get("title_history", [])) or "（なし）",
        )

        try:
            response = self.client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            result = self._parse_response(response.content[0].text)
        except anthropic.APIError as e:
            logger.error("Claude API呼び出しに失敗しました（channel=%s）: %s", influencer.get("channel_name"), e)
            result = {}
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("Claude応答のJSON解析に失敗しました（channel=%s）: %s", influencer.get("channel_name"), e)
            result = {}

        updated = dict(influencer)
        updated["main_genre"] = result.get("main_genre")
        updated["tone"] = result.get("tone")
        updated["total_score"] = result.get("total_score")
        updated["title_fit_score"] = result.get("title_fit_score")
        updated["organic_potential"] = result.get("organic_potential")
        updated["recommended_approach"] = result.get("recommended_approach")
        return updated

    @staticmethod
    def _parse_response(text: str) -> dict:
        """Claudeの応答テキストからJSONオブジェクトを抽出してパースする。"""
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("応答にJSONオブジェクトが見つかりません")
        return json.loads(text[start:end + 1])


# 簡易ユニットテスト（実行可能コードは不要、方針のみ記載）
# - _parse_responseが前後に説明文が付いたテキストからもJSONを抽出できることを確認する
# - analyze_influencerがAPI呼び出し失敗時に元のinfluencerデータを欠損なく返すことを確認する
