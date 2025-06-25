# run.py
import os
import asyncio
import argparse
import logging
from datetime import datetime, date
from pathlib import Path
from src.bot import ReportBot

def parse_date(date_str: str) -> date:
    try:
        # YYYY/MM/DD, YYYY-MM-DD形式をサポート
        for fmt in ['%Y/%m/%d', '%Y-%m-%d']:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        raise ValueError
    except ValueError:
        raise argparse.ArgumentTypeError(f'Invalid date format: {date_str}. Use YYYY/MM/DD or YYYY-MM-DD')

def parse_args():
    parser = argparse.ArgumentParser(description='日報・宣言チェックBot')
    parser.add_argument(
        '--date',
        type=parse_date,
        help='チェックする日付（YYYY/MM/DD形式）。指定がない場合は本日の日付',
        default=date.today()
    )
    return parser.parse_args()
from config.config import (
    DISCORD_TOKEN,
    REPORT_CHANNEL_ID,
    DECLARATION_CHANNEL_ID,
    SPREADSHEET_ID,
    CREDENTIALS_PATH
)

def setup_logging(target_date: date, debug_mode: bool = False):
    # logディレクトリが存在しない場合は作成
    log_dir = Path("log")
    log_dir.mkdir(exist_ok=True)
    
    # ログファイル名を設定（YYYYMMDD.log形式）
    log_file = log_dir / f"{target_date.strftime('%Y%m%d')}.log"
    
    # ロガーの設定
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    
    # 既存のハンドラーをクリア
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # ファイルハンドラーの設定
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    
    # フォーマッターの設定
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # ロガーにハンドラーを追加
    logger.addHandler(file_handler)
    
    if debug_mode:
        logging.info("デバッグモードが有効です")

def check_environment():
    logging.info("環境変数チェック中...")
    required_vars = {
        'DISCORD_TOKEN': DISCORD_TOKEN,
        'REPORT_CHANNEL_ID': REPORT_CHANNEL_ID,
        'DECLARATION_CHANNEL_ID': DECLARATION_CHANNEL_ID,
        'SPREADSHEET_ID': SPREADSHEET_ID
    }

    missing_vars = [name for name, value in required_vars.items() if not value]
    
    if missing_vars:
        logging.error("以下の環境変数が設定されていません:")
        for var in missing_vars:
            logging.error(f"- {var}")
        return False

    if not CREDENTIALS_PATH.exists():
        logging.error("Google認証情報ファイルが見つかりません:")
        logging.error(f"- {CREDENTIALS_PATH}")
        return False

    logging.info("✓ すべての環境変数が正しく設定されています")
    return True

async def main():
    args = parse_args()
    
    # ロギングの設定（デフォルトはINFOレベル）
    setup_logging(args.date, debug_mode=False)
    
    logging.info("=== 報告・宣言チェックBot ===")
    
    if not check_environment():
        logging.error("❌ 環境設定が不完全です。プログラムを終了します。")
        return

    logging.info("🤖 Botを起動中...")
    logging.info(f"チェック対象日: {args.date.strftime('%Y/%m/%d')}")
    bot = ReportBot(target_date=args.date)
    
    try:
        # Botを起動し、チェック完了を待つ
        async with bot:
            logging.info("✓ Bot準備完了")
            # 5分のタイムアウトを設定
            try:
                async with asyncio.timeout(300):  # 5分
                    await bot.start(DISCORD_TOKEN)
            except asyncio.TimeoutError:
                logging.warning("⚠️ タイムアウト：処理が5分以上かかったため終了します")
    except KeyboardInterrupt:
        logging.warning("⚠️ プログラムが中断されました")
    except Exception as e:
        logging.error(f"❌ エラーが発生しました: {str(e)}")
    finally:
        if not bot.is_closed():
            await bot.close()
        logging.info("✓ プログラムを終了しました")

if __name__ == "__main__":
    asyncio.run(main())