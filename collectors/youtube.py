"""YouTube Data API v3 によるインフルエンサー収集モジュール。

検索フロー:
  1. search.list でキーワードの動画検索 → ヒットした動画の投稿者チャンネルIDを重複排除しながら収集
     （regionCode=JPで日本向けに絞り込み、1ページ最大50件、MAX_CHANNELS_PER_SEARCH件に
     達するかSEARCH_MAX_PAGES（クォータ保護の上限）かページが尽きるまでページネーション）
  2. channels.list でチャンネル詳細取得（登録者数・開設日・説明文・投稿動画プレイリストID）
     snippet.countryがTARGET_COUNTRY（JP）と完全一致しないチャンネルはここで除外する
  3. playlistItems.list で投稿動画プレイリストから最新動画タイトルを取得（直近MAX_VIDEOS_PER_CHANNEL件）
  4. 取得データをnormalizeしてスキーマに変換

クォータ注記:
  search.list は1回100ユニット、channels.list / playlistItems.list は1回1ユニット。
  チャンネルごとの動画取得にsearch.listを使うと20チャンネルで2,000ユニットを消費し
  1日10,000ユニットの上限にすぐ達してしまうため、ここでは安価なplaylistItems.listを使用する。
  動画検索方式はtype="channel"検索よりヒット候補が大幅に増えるが、SEARCH_MAX_PAGES（デフォルト5）
  により1キーワードあたりのsearch.list呼び出し回数の上限を設け、クォータ超過を防いでいる。
"""
import logging

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config
from collectors.base import EMPTY_SCHEMA, BaseCollector

logger = logging.getLogger(__name__)


class YouTubeCollector(BaseCollector):
    source_name = "youtube"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or config.YOUTUBE_API_KEY
        self.client = build("youtube", "v3", developerKey=self.api_key)

    def fetch(self, keyword: str) -> list[dict]:
        """キーワードでチャンネルを検索し、詳細・動画タイトルを含む生データのリストを返す。"""
        raw_list = []
        try:
            channel_ids = self._search_channel_ids(keyword)
        except HttpError as e:
            logger.error("チャンネル検索に失敗しました（keyword=%s）: %s", keyword, e)
            return raw_list

        for channel_id in channel_ids:
            try:
                channel_detail = self._get_channel_detail(channel_id)
                if channel_detail is None:
                    continue
                if not self._is_target_country(channel_detail):
                    continue
                video_titles = self._get_recent_video_titles(channel_detail)
                raw_list.append({
                    "keyword": keyword,
                    "channel": channel_detail,
                    "video_titles": video_titles,
                })
            except HttpError as e:
                logger.error("チャンネル詳細取得に失敗しました（channel_id=%s）: %s", channel_id, e)
                continue

        return raw_list

    def _search_channel_ids(self, keyword: str) -> list[str]:
        """search.list（動画検索）でキーワードにヒットした動画の投稿者チャンネルIDを収集する。

        type="channel"検索はチャンネル自身のメタデータにキーワードが含まれる
        場合しかヒットせず候補が極端に少なくなるため、動画検索でヒットした
        動画の投稿者チャンネルIDを重複排除しながら集める方式にする。
        MAX_CHANNELS_PER_SEARCH件のユニークなチャンネルIDが集まるか、
        SEARCH_MAX_PAGES（クォータ保護の上限）に達するか、ページが尽きるまで
        nextPageTokenでページネーションする。ページ追加ごとに100ユニット消費する。
        """
        channel_ids: list[str] = []
        seen_channel_ids: set[str] = set()
        page_token = None
        page_count = 0

        while len(channel_ids) < config.MAX_CHANNELS_PER_SEARCH and page_count < config.SEARCH_MAX_PAGES:
            response = self.client.search().list(
                q=keyword,
                type="video",
                part="snippet",
                maxResults=config.SEARCH_PAGE_SIZE,
                regionCode=config.SEARCH_REGION_CODE,
                relevanceLanguage=config.SEARCH_RELEVANCE_LANGUAGE,
                pageToken=page_token,
            ).execute()
            page_count += 1

            for item in response.get("items", []):
                channel_id = item["snippet"]["channelId"]
                if channel_id not in seen_channel_ids:
                    seen_channel_ids.add(channel_id)
                    channel_ids.append(channel_id)

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return channel_ids[:config.MAX_CHANNELS_PER_SEARCH]

    @staticmethod
    def _is_target_country(channel_detail: dict) -> bool:
        """チャンネルのsnippet.countryがTARGET_COUNTRYと完全一致する場合のみ許容する（未設定は除外）。"""
        country = channel_detail.get("snippet", {}).get("country")
        return country == config.TARGET_COUNTRY

    def _get_channel_detail(self, channel_id: str) -> dict | None:
        """channels.listでチャンネル詳細（統計・開設日・概要欄・投稿動画プレイリストID）を取得する。"""
        response = self.client.channels().list(
            id=channel_id,
            part="snippet,statistics,contentDetails",
        ).execute()
        items = response.get("items", [])
        if not items:
            return None
        return items[0]

    def _get_recent_video_titles(self, channel_detail: dict) -> list[dict]:
        """投稿動画プレイリストから直近MAX_VIDEOS_PER_CHANNEL件の動画タイトル・概要欄を取得する。"""
        uploads_playlist_id = (
            channel_detail.get("contentDetails", {})
            .get("relatedPlaylists", {})
            .get("uploads")
        )
        if not uploads_playlist_id:
            return []

        try:
            response = self.client.playlistItems().list(
                playlistId=uploads_playlist_id,
                part="snippet",
                maxResults=min(config.MAX_VIDEOS_PER_CHANNEL, 50),
            ).execute()
        except HttpError as e:
            logger.error("動画タイトル取得に失敗しました（playlist_id=%s）: %s", uploads_playlist_id, e)
            return []

        videos = []
        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            videos.append({
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
            })
        return videos

    def normalize(self, raw: dict) -> dict:
        """生データを共通スキーマに変換する。"""
        data = dict(EMPTY_SCHEMA)
        channel = raw["channel"]
        snippet = channel.get("snippet", {})
        statistics = channel.get("statistics", {})
        videos = raw.get("video_titles", [])

        titles = [v["title"] for v in videos]
        descriptions = [v["description"] for v in videos]

        data["channel_name"] = snippet.get("title")
        data["channel_url"] = f"https://www.youtube.com/channel/{channel.get('id')}"
        data["location"] = snippet.get("country")
        data["platform"] = "YouTube"
        data["account_created"] = snippet.get("publishedAt")
        subscriber_count = statistics.get("subscriberCount")
        data["subscriber_count"] = int(subscriber_count) if subscriber_count is not None else None
        data["title_history"] = titles
        data["agency"] = None
        data["contact_info"] = snippet.get("description")
        data["pr_ratio"] = self._calc_pr_ratio(titles, descriptions)
        data["organic_mentions"] = [t for t in titles if raw["keyword"].lower() in t.lower()]
        data["unpaid_coverage"] = len(data["organic_mentions"]) > 0
        data["source"] = self.source_name
        data["fetched_at"] = self.now_iso()

        return data

    @staticmethod
    def _calc_pr_ratio(titles: list[str], descriptions: list[str]) -> str | None:
        """概要欄・動画タイトルに含まれるPR表記の割合を算出する。"""
        total = len(titles)
        if total == 0:
            return None
        pr_count = 0
        for title, description in zip(titles, descriptions):
            text = f"{title} {description}"
            if any(kw.lower() in text.lower() for kw in config.PR_KEYWORDS):
                pr_count += 1
        return f"{pr_count}/{total}"


# 簡易ユニットテスト（実行可能コードは不要、方針のみ記載）
# - _search_channel_idsがMAX_CHANNELS_PER_SEARCH件以下のIDリストを、ページネーションを跨いで返すことを確認する
# - _is_target_countryがcountry未設定の場合にTrueを返し、JP以外の場合にFalseを返すことを確認する
# - _get_recent_video_titlesがuploads_playlist_id無しの場合に空リストを返すことを確認する
# - _calc_pr_ratioがPRキーワードを含むタイトル数を正しく数えることを確認する
# - normalizeの戻り値がEMPTY_SCHEMAの全キーを含み、channel_urlが正しい形式であることを確認する
