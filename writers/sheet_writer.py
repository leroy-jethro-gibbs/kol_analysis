"""gspreadによるGoogleスプレッドシート書き込みモジュール。

シート構造:
  - スプレッドシート名: インフルエンサーDB
  - シート名: 検索キーワード（例: Subnautica2）
  - 1キーワード = 1シート。既存シートがあれば内容をクリアして上書き更新する。
  - 1行目: カテゴリ名（結合セル）、2行目: 項目名、3行目以降: データ。
  - 手動入力欄（×項目）は列は確保するが値は空白とし、グレー背景色で視覚的に区別する。
"""
import logging

import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import WorksheetNotFound

import config

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class SheetWriter:
    def __init__(self):
        creds_info = config.get_google_service_account_info()
        creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        self.gc = gspread.authorize(creds)
        self.spreadsheet = self.gc.open_by_key(config.SPREADSHEET_ID)
        self._columns = self._flatten_columns()

    @staticmethod
    def _flatten_columns() -> list[tuple[str, str, str, bool]]:
        """SHEET_HEADER_STRUCTUREを(カテゴリ名, 項目キー, 項目名, 手動入力欄か)のフラットなリストに変換する。"""
        columns = []
        for category, items in config.SHEET_HEADER_STRUCTURE:
            for key, label, is_manual in items:
                columns.append((category, key, label, is_manual))
        return columns

    def write(self, data: list[dict], keyword: str) -> str:
        """キーワードに対応するシートへデータを書き込み、スプレッドシートのURLを返す。"""
        try:
            worksheet = self._get_or_create_worksheet(keyword)
            worksheet.clear()
            self._write_headers(worksheet)
            self._write_rows(worksheet, data)
            self._apply_manual_column_style(worksheet, len(data))
        except gspread.exceptions.APIError as e:
            logger.error("スプレッドシート書き込みに失敗しました（keyword=%s）: %s", keyword, e)
            raise

        return self.spreadsheet.url

    def _get_or_create_worksheet(self, keyword: str):
        try:
            return self.spreadsheet.worksheet(keyword)
        except WorksheetNotFound:
            return self.spreadsheet.add_worksheet(
                title=keyword, rows=max(len(self._columns) + 10, 100), cols=len(self._columns)
            )

    def _write_headers(self, worksheet) -> None:
        """1行目にカテゴリ名（結合）、2行目に項目名を書き込む。"""
        category_row = [col[0] for col in self._columns]
        label_row = [col[2] for col in self._columns]
        worksheet.update(values=[category_row, label_row], range_name="A1")

        merge_requests = []
        col_index = 0
        for category, items in config.SHEET_HEADER_STRUCTURE:
            span = len(items)
            if span > 1:
                start_col = col_index
                end_col = col_index + span - 1
                merge_requests.append((start_col, end_col))
            col_index += span

        for start_col, end_col in merge_requests:
            worksheet.merge_cells(
                1, start_col + 1, 1, end_col + 1, merge_type="MERGE_ALL"
            )

    def _write_rows(self, worksheet, data: list[dict]) -> None:
        """3行目以降にインフルエンサーを1行ずつ書き込む。手動入力欄は空白にする。"""
        rows = []
        for influencer in data:
            row = []
            for _category, key, _label, is_manual in self._columns:
                if is_manual:
                    row.append("")
                else:
                    row.append(self._format_value(influencer.get(key)))
            rows.append(row)

        if rows:
            worksheet.update(values=rows, range_name="A3")

    @staticmethod
    def _format_value(value):
        """リスト・bool等のセル表示用フォーマットを行う。"""
        if isinstance(value, list):
            return ", ".join(str(v) for v in value)
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if value is None:
            return ""
        return value

    def _apply_manual_column_style(self, worksheet, data_row_count: int) -> None:
        """手動入力欄の列全体にグレー背景色を設定する。"""
        total_rows = max(data_row_count + 2, 2)
        for col_index, (_category, _key, _label, is_manual) in enumerate(self._columns, start=1):
            if not is_manual:
                continue
            cell_range = gspread.utils.rowcol_to_a1(1, col_index) + ":" + gspread.utils.rowcol_to_a1(total_rows, col_index)
            worksheet.format(cell_range, {"backgroundColor": config.MANUAL_INPUT_BG_COLOR})


# 簡易ユニットテスト（実行可能コードは不要、方針のみ記載）
# - _flatten_columnsがSHEET_HEADER_STRUCTUREの全項目数と一致する長さを返すことを確認する
# - _format_valueがlist/bool/Noneを正しく文字列化することを確認する
# - _write_rowsが手動入力欄の値を常に空文字にすることを確認する
