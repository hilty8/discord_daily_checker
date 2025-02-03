from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime
import asyncio
from typing import Dict, List, Tuple, Any
from pathlib import Path
import logging
from config.config import (
    SPREADSHEET_ID, 
    CREDENTIALS_PATH,
    START_ROW,
    USER_COLUMNS
)

class SheetsHandler:
    def __init__(self):
        credentials = service_account.Credentials.from_service_account_file(
            CREDENTIALS_PATH,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        self.service = build('sheets', 'v4', credentials=credentials)
        self.spreadsheet_id = SPREADSHEET_ID
        # シート名のキャッシュ
        self._sheet_name_cache: Dict[str, str] = {}
        # 最大バッチサイズ(Google Sheets APIの制限に基づく)
        self.MAX_BATCH_SIZE = 100
        # 1バッチあたりのユーザー数(パフォーマンステストに基づいて最適化)
        self.USERS_PER_BATCH = 15
        # 最大再試行回数
        self.MAX_RETRIES = 3
        # 同時実行数の制限
        self.CONCURRENT_LIMIT = 3

    async def write_check_results(self, updates: List[Tuple[datetime, str, bool, bool]]):
        """
        複数のユーザーの更新をバッチ処理で行う
        
        Args:
            updates: (日付, ユーザーID, レポート状態, 宣言状態)のタプルのリスト
        """
        # シートごとに更新をグループ化
        sheet_updates: Dict[str, List[Tuple[datetime, str, bool, bool]]] = {}
        for update in updates:
            date = update[0]
            sheet_name = self._get_cached_sheet_name(date)
            if sheet_name not in sheet_updates:
                sheet_updates[sheet_name] = []
            sheet_updates[sheet_name].append(update)

        # 各シートの更新を並列で処理
        tasks = []
        for sheet_name, sheet_updates_list in sheet_updates.items():
            tasks.append(self._process_sheet_updates(sheet_name, sheet_updates_list))

        # 同時実行数を制限して実行
        semaphore = asyncio.Semaphore(self.CONCURRENT_LIMIT)
        async def bounded_process(task):
            async with semaphore:
                return await task
        
        results = await asyncio.gather(*[bounded_process(task) for task in tasks])
        
        # エラーチェック
        for sheet_name, result in zip(sheet_updates.keys(), results):
            if isinstance(result, Exception):
                logging.error(f"Failed to process sheet {sheet_name}: {str(result)}")

    async def write_check_result(self, date: datetime, user_id: str, report_status: bool, declaration_status: bool):
        """
        単一ユーザーの更新を行う(非同期バージョン)
        """
        updates = [(date, user_id, report_status, declaration_status)]
        await self.write_check_results(updates)

    async def _process_sheet_updates(self, sheet_name: str, updates: List[Tuple[datetime, str, bool, bool]]) -> bool:
        """
        1つのシートの更新を処理する
        """
        try:
            # 更新をバッチに分割
            batches = [updates[i:i + self.USERS_PER_BATCH] 
                      for i in range(0, len(updates), self.USERS_PER_BATCH)]
            
            # 各バッチを処理
            for batch in batches:
                batch_updates = self._prepare_batch_updates(sheet_name, batch)
                await self._execute_batch_update(batch_updates)
            
            return True
        except Exception as e:
            logging.error(f"Error processing sheet {sheet_name}: {str(e)}")
            return False

    def _prepare_batch_updates(self, sheet_name: str, batch: List[Tuple[datetime, str, bool, bool]]) -> List[Dict]:
        """
        バッチ更新のデータを準備する
        """
        updates = []
        for date, user_id, report_status, declaration_status in batch:
            row = self._get_row_index(date)
            columns = USER_COLUMNS.get(user_id)
            
            if not columns:
                logging.error(f"Unknown user_id: {user_id}")
                continue

            updates.extend([
                {
                    'range': f"'{sheet_name}'!{columns['report']}{row}",
                    'values': [["提出" if report_status else "なし"]]
                },
                {
                    'range': f"'{sheet_name}'!{columns['declaration']}{row}",
                    'values': [["提出" if declaration_status else "なし"]]
                }
            ])
        
        return updates

    async def _execute_batch_update(self, updates: List[Dict], attempt: int = 0) -> bool:
        """
        バッチ更新を実行し、必要に応じて再試行する
        """
        try:
            data = {
                'valueInputOption': 'USER_ENTERED',
                'data': updates
            }

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.service.spreadsheets().values().batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body=data
                ).execute()
            )
            return True

        except Exception as e:
            if attempt < self.MAX_RETRIES:
                await asyncio.sleep(2 ** attempt)  # 指数バックオフ
                return await self._execute_batch_update(updates, attempt + 1)
            raise e

    def _get_cached_sheet_name(self, date: datetime) -> str:
        """
        キャッシュを使用してシート名を取得
        """
        cache_key = f"{date.year}-{date.month}"
        if cache_key not in self._sheet_name_cache:
            self._sheet_name_cache[cache_key] = self._get_sheet_name(date)
        return self._sheet_name_cache[cache_key]

    def _get_row_index(self, date: datetime) -> int:
        return START_ROW + (date.day - 1)

    def _get_sheet_name(self, date: datetime) -> str:
        return f"{date.month}月"

    def _column_to_index(self, column: str) -> int:
        return sum((ord(char) - ord('A') + 1) * (26 ** i) 
                for i, char in enumerate(reversed(column))) - 1