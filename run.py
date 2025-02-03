# run.py
import os
import asyncio
import argparse
from datetime import datetime, date
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

def check_environment():
    print("環境変数チェック中...")
    required_vars = {
        'DISCORD_TOKEN': DISCORD_TOKEN,
        'REPORT_CHANNEL_ID': REPORT_CHANNEL_ID,
        'DECLARATION_CHANNEL_ID': DECLARATION_CHANNEL_ID,
        'SPREADSHEET_ID': SPREADSHEET_ID
    }

    missing_vars = [name for name, value in required_vars.items() if not value]
    
    if missing_vars:
        print("\n⚠️ 以下の環境変数が設定されていません:")
        for var in missing_vars:
            print(f"- {var}")
        return False

    if not CREDENTIALS_PATH.exists():
        print("\n⚠️ Google認証情報ファイルが見つかりません:")
        print(f"- {CREDENTIALS_PATH}")
        return False

    print("✓ すべての環境変数が正しく設定されています")
    return True

async def main():
    args = parse_args()
    
    if not check_environment():
        print("\n❌ 環境設定が不完全です。プログラムを終了します。")
        return

    print("\n🤖 Botを起動中...")
    print(f"チェック対象日: {args.date.strftime('%Y/%m/%d')}")
    bot = ReportBot(target_date=args.date)
    
    try:
        # Botを起動し、チェック完了を待つ
        async with bot:
            print("✓ Bot準備完了")
            # 5分のタイムアウトを設定
            try:
                async with asyncio.timeout(300):  # 5分
                    await bot.start(DISCORD_TOKEN)
            except asyncio.TimeoutError:
                print("\n⚠️ タイムアウト：処理が5分以上かかったため終了します")
    except KeyboardInterrupt:
        print("\n⚠️ プログラムが中断されました")
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {str(e)}")
    finally:
        if not bot.is_closed():
            await bot.close()
        print("\n✓ プログラムを終了しました")

if __name__ == "__main__":
    print("=== 報告・宣言チェックBot ===")
    asyncio.run(main())