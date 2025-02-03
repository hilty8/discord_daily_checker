from datetime import datetime
import asyncio
import logging
from src.sheets_handler import SheetsHandler
from config.config import USER_COLUMNS

logging.basicConfig(level=logging.INFO)

async def verify_production():
    handler = SheetsHandler()
    test_date = datetime(2025, 1, 30)  # 1月30日
    
    # 全ユーザーを対象に更新
    test_users = list(USER_COLUMNS.keys())
    total_users = len(test_users)
    
    logging.info(f"本番環境での動作確認開始: {test_date.strftime('%Y/%m/%d')}")
    logging.info(f"対象ユーザー数: {total_users}")
    
    # バッチ更新の実行
    start_time = time.time()
    updates = [(test_date, user_id, True, True) for user_id in test_users]
    await handler.write_check_results(updates)
    execution_time = time.time() - start_time
    
    logging.info(f"処理時間: {execution_time:.2f}秒")
    logging.info(f"1ユーザーあたりの平均処理時間: {execution_time/total_users:.2f}秒")
    logging.info("本番環境での動作確認完了")

if __name__ == "__main__":
    import time
    asyncio.run(verify_production())