# インフルエンサーDB自動収集システム

ゲームタイトルをキーワードにYouTubeインフルエンサーを自動収集・分析し、
Googleスプレッドシートへ出力するシステム。

## 構成

```
.
├── main.py                  # エントリーポイント（CLI実行用）
├── app.py                   # Streamlit UI
├── config.py                # 設定値・定数管理
├── collectors/
│   ├── base.py              # 共通インターフェース定義
│   └── youtube.py           # YouTube Data API v3 実装
├── analyzers/
│   └── claude_analyzer.py   # Claude APIによるスコアリング・分析
├── writers/
│   └── sheet_writer.py      # gspreadによるスプレッドシート書き込み
├── data/                    # 中間JSONの保存先
└── .github/workflows/
    └── weekly_update.yml    # 週次自動更新（GitHub Actions）
```

## セットアップ

1. 依存関係をインストールする。

   ```bash
   pip install -r requirements.txt
   ```

2. `.env.example` を `.env` にコピーし、各値を設定する。

   ```bash
   cp .env.example .env
   ```

   - `YOUTUBE_API_KEY`: YouTube Data API v3 のAPIキー
   - `ANTHROPIC_API_KEY`: Claude APIキー
   - `GOOGLE_SERVICE_ACCOUNT_JSON`: サービスアカウントJSONをBase64エンコードした文字列
     ```bash
     base64 -i service_account.json
     ```
   - `SPREADSHEET_ID`: 書き込み先スプレッドシートのID（URLの `/d/` と `/edit` の間の文字列）

   サービスアカウントには対象スプレッドシートの編集者権限を共有しておくこと。

## 実行方法

### CLI

```bash
python main.py "Subnautica2"
```

### Streamlit UI

```bash
streamlit run app.py
```

## 自動実行（GitHub Actions）

毎週月曜09:00 JSTに `data/` 配下の既存JSONに記録されたキーワードを全件更新する。
以下のSecretsをリポジトリに設定すること。

- `YOUTUBE_API_KEY`
- `ANTHROPIC_API_KEY`
- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `SPREADSHEET_ID`
- `SLACK_WEBHOOK_URL`

## クォータについて

YouTube Data API v3 は1日10,000ユニットの上限がある。
動画タイトル取得には `playlistItems.list`（1ユニット/回）を使用しており、
`search.list`（100ユニット/回）をチャンネルごとに呼ぶ実装と比べて
1キーワードあたりの消費を大幅に抑えている。

チャンネル候補の収集には `search.list(type="video")` でキーワードにヒットした動画の
投稿者チャンネルIDを重複排除しながら集める方式を採用している（`type="channel"`検索は
チャンネル自身のメタデータにキーワードが含まれる場合しかヒットせず候補が少なすぎるため）。
1ページ最大50件取得でき、`MAX_CHANNELS_PER_SEARCH`件のユニークなチャンネルIDが集まるか
`SEARCH_MAX_PAGES`（デフォルト10）に達するかページが尽きるまでページネーションする。
ページ追加ごとに100ユニット消費するため、`SEARCH_MAX_PAGES=10`の場合は
1キーワードあたり最大1,000ユニット（+チャンネル数分のchannels.list/playlistItems.list）となる。
`MAX_CHANNELS_PER_SEARCH` / `MAX_VIDEOS_PER_CHANNEL` / `SEARCH_MAX_PAGES` で調整できる。

検索結果は `SEARCH_REGION_CODE="JP"` で日本向けに絞り込み、取得したチャンネルの
`snippet.country` が `TARGET_COUNTRY`（JP）と完全一致しない場合は除外している
（未設定の場合も除外する厳格なルール）。

## 拡張方法

X・TikTok・SerpAPI等を追加する場合は `collectors/base.py` の `BaseCollector` を継承し、
`fetch` / `normalize` を実装した新しいファイルを `collectors/` に追加するだけでよい。
コアモジュールへの変更は不要。
