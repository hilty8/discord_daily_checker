import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
import time
import asyncio
import logging
from src.sheets_handler import SheetsHandler
from config.config import USER_COLUMNS

logging.basicConfig(level=logging.INFO)

async def test_batch_performance():
    handler = SheetsHandler()
    test_date = datetime(2025, 1, 1)
    
    # テスト用のユーザーIDリスト(config/user_columns.jsonから取得)
    test_users = list(USER_COLUMNS.keys())
    total_users = len(test_users)
    
    logging.info(f"テスト開始: 合計 {total_users} ユーザー")
    
    # 単一更新の時間計測
    start_time = time.time()
    single_update_tasks = []
    for user_id in test_users:
        single_update_tasks.append(
            handler.write_check_result(test_date, user_id, True, True)
        )
    await asyncio.gather(*single_update_tasks)
    single_update_time = time.time() - start_time
    logging.info(f"単一更新の処理時間: {single_update_time:.2f}秒")
    
    # バッチ更新の時間計測
    start_time = time.time()
    updates = [(test_date, user_id, True, True) for user_id in test_users]
    await handler.write_check_results(updates)
    batch_update_time = time.time() - start_time
    logging.info(f"バッチ更新の処理時間: {batch_update_time:.2f}秒")
    
    # 改善率の計算
    improvement = ((single_update_time - batch_update_time) / single_update_time) * 100
    logging.info(f"処理速度の改善率: {improvement:.1f}%")
    
    # バッチサイズの情報
    users_per_batch = handler.USERS_PER_BATCH
    total_batches = (total_users + users_per_batch - 1) // users_per_batch
    avg_time_per_batch = batch_update_time / total_batches
    
    logging.info(f"バッチ処理の詳細:")
    logging.info(f"- 1バッチあたりのユーザー数: {users_per_batch}")
    logging.info(f"- 合計バッチ数: {total_batches}")
    logging.info(f"- 1バッチあたりの平均処理時間: {avg_time_per_batch:.2f}秒")

async def test_error_handling():
    """エラーハンドリングとリトライのテスト"""
    handler = SheetsHandler()
    test_date = datetime(2025, 1, 1)
    
    # 無効なユーザーIDを含めてテスト
    test_users = list(USER_COLUMNS.keys())[:3] + ['invalid_user_id'] + list(USER_COLUMNS.keys())[3:6]
    updates = [(test_date, user_id, True, True) for user_id in test_users]
    
    logging.info("エラーハンドリングテスト開始")
    start_time = time.time()
    await handler.write_check_results(updates)
    end_time = time.time()
    
    logging.info(f"エラーハンドリングテスト完了: {end_time - start_time:.2f}秒")

if __name__ == "__main__":
    # 両方のテストを実行
    async def run_tests():
        await test_batch_performance()
        logging.info("\n" + "="*50 + "\n")
        await test_error_handling()
    
    asyncio.run(run_tests())