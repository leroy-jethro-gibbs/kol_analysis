"""コレクター共通インターフェース定義。

X・TikTok・SerpAPI等の拡張モジュールは、このクラスを継承し
fetch / normalize / save_json を実装するだけで追加できる。
"""
import json
import logging
import os
import shutil
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from config import DATA_DIR

logger = logging.getLogger(__name__)

# 共通スキーマ：取得不可フィールドはNoneとし、キー自体は必ず含める
EMPTY_SCHEMA = {
    # 基本情報
    "channel_name": None,
    "channel_url": None,
    "estimated_age_group": None,
    "location": None,
    # プレゼンス
    "platform": None,
    "account_created": None,
    "subscriber_count": None,
    # コンテンツ
    "main_genre": None,
    "title_history": [],
    "post_frequency": None,
    "tone": None,
    # オーディエンス（YouTube Analytics非対応のためNull固定）
    "audience_age": None,
    "audience_gender": None,
    "audience_region": None,
    "active_hours": None,
    # ネットワーク
    "collaborations": [],
    # スタンス
    "pr_ratio": None,
    # オーガニック
    "organic_mentions": [],
    "unpaid_coverage": None,
    # リスク
    "controversy_history": None,
    # コスト（手動入力欄）
    "unit_price": None,
    "cost_history": None,
    # コンタクト
    "agency": None,
    "contact_info": None,
    # 取引実績（手動入力欄）
    "past_engagement": None,
    "communication_rating": None,
    # 判定（Claude APIが生成）
    "total_score": None,
    "title_fit_score": None,
    "organic_potential": None,
    "recommended_approach": None,
    # メタ
    "source": None,
    "fetched_at": None,
}


class BaseCollector(ABC):
    """全コレクターが継承する基底クラス。"""

    source_name = "base"

    @abstractmethod
    def fetch(self, keyword: str) -> list[dict]:
        """APIからキーワードに紐づく生データを取得する。"""
        raise NotImplementedError

    @abstractmethod
    def normalize(self, raw: dict) -> dict:
        """取得した生データを共通スキーマ(EMPTY_SCHEMA)に変換する。"""
        raise NotImplementedError

    def save_json(self, data: list[dict], keyword: str) -> str:
        """data/配下にキーワード単位でJSON保存する。既存ファイルは.bakにバックアップする。"""
        os.makedirs(DATA_DIR, exist_ok=True)
        filepath = os.path.join(DATA_DIR, f"{self.source_name}_{keyword}.json")

        if os.path.exists(filepath):
            backup_path = filepath + ".bak"
            try:
                shutil.copy2(filepath, backup_path)
            except OSError as e:
                logger.error("バックアップ作成に失敗しました: %s", e)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.error("JSON保存に失敗しました: %s", e)
            raise

        return filepath

    @staticmethod
    def now_iso() -> str:
        """現在時刻をISO 8601形式で返す。"""
        return datetime.now(timezone.utc).isoformat()


# 簡易ユニットテスト（実行可能コードは不要、方針のみ記載）
# - EMPTY_SCHEMAの全キーがnormalize()の戻り値に含まれることを確認する
# - save_json()呼び出し前に既存ファイルがあれば.bakが作成されることを確認する
# - save_json()が正しいファイルパスを返すことを確認する
