"""設定値・定数管理モジュール。

.envファイルから環境変数を読み込み、アプリ全体で使う設定値を一元管理する。
"""
import base64
import json
import os

from dotenv import load_dotenv

load_dotenv()

# --- API認証情報 ---
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GOOGLE_SERVICE_ACCOUNT_JSON_B64 = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")

# --- 収集制御 ---
MAX_CHANNELS_PER_SEARCH = int(os.getenv("MAX_CHANNELS_PER_SEARCH", "50"))
MAX_VIDEOS_PER_CHANNEL = int(os.getenv("MAX_VIDEOS_PER_CHANNEL", "30"))

# search.listの1回あたりの最大取得数（YouTube APIの上限）
SEARCH_PAGE_SIZE = 50

# 日本のインフルエンサーに限定するための検索条件
SEARCH_REGION_CODE = "JP"
SEARCH_RELEVANCE_LANGUAGE = "ja"
# channelのsnippet.countryがこの値と異なる場合は除外する（未設定(None)は許容する）
TARGET_COUNTRY = "JP"

# --- Claude分析モデル ---
CLAUDE_MODEL = "claude-sonnet-4-6"

# --- パス設定 ---
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# --- PR判定キーワード ---
PR_KEYWORDS = ["#PR", "#ad", "#sponsored", "#案件"]

# --- スプレッドシート出力設定 ---
SPREADSHEET_NAME = "インフルエンサーDB"

# 手動入力欄として列を確保するが値は空欄にし、視覚的に区別するためのグレー背景色
MANUAL_INPUT_BG_COLOR = {"red": 0.92, "green": 0.92, "blue": 0.92}

# カテゴリ・項目の2行ヘッダー構造
# (カテゴリ名, [(項目キー, 項目名, 手動入力欄か), ...])
SHEET_HEADER_STRUCTURE = [
    ("基本情報", [
        ("channel_name", "活動名", False),
        ("channel_url", "チャンネルURL", False),
        ("estimated_age_group", "年齢層", False),
        ("location", "拠点", False),
    ]),
    ("プレゼンス", [
        ("platform", "主要PF", False),
        ("account_created", "開設時期", False),
        ("subscriber_count", "フォロワー数", False),
    ]),
    ("コンテンツ", [
        ("main_genre", "主ジャンル", False),
        ("title_history", "タイトル履歴", False),
        ("post_frequency", "投稿頻度", False),
        ("tone", "トーン", False),
    ]),
    ("オーディエンス", [
        ("audience_age", "年齢層", False),
        ("audience_gender", "性別比", False),
        ("audience_region", "地域", False),
        ("active_hours", "アクティブ時間帯", False),
    ]),
    ("ネットワーク", [
        ("collaborations", "共演コラボ履歴", False),
    ]),
    ("スタンス", [
        ("pr_ratio", "PR案件比率", False),
    ]),
    ("オーガニック", [
        ("organic_mentions", "言及履歴", False),
        ("unpaid_coverage", "無償取り上げ実績", False),
    ]),
    ("リスク", [
        ("controversy_history", "炎上履歴", False),
    ]),
    ("コスト", [
        ("unit_price", "案件単価", True),
        ("cost_history", "単価推移", True),
    ]),
    ("コンタクト", [
        ("agency", "所属先", False),
        ("contact_info", "連絡経路", False),
    ]),
    ("取引実績", [
        ("past_engagement", "過去起用有無", True),
        ("communication_rating", "コミュ評価", True),
    ]),
    ("判定", [
        ("total_score", "総合スコア", False),
        ("title_fit_score", "適合度", False),
        ("organic_potential", "オーガニック誘発可能性", False),
        ("recommended_approach", "推奨アプローチ", False),
    ]),
]


def get_google_service_account_info() -> dict:
    """Base64エンコードされたサービスアカウントJSONをデコードして辞書で返す。"""
    decoded = base64.b64decode(GOOGLE_SERVICE_ACCOUNT_JSON_B64)
    return json.loads(decoded)
