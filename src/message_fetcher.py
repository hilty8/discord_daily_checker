import discord
from discord.ext import commands
import logging
import pytz
from datetime import datetime, timedelta
from typing import Optional
import asyncio
import json
import os
import sys
from pathlib import Path

# プロジェクトのルートディレクトリをPythonパスに追加
root_dir = str(Path(__file__).parent.parent)
sys.path.append(root_dir)

from config.config import REPORT_CHANNEL_ID, DISCORD_TOKEN

class MessageFetcher(commands.Bot):
    def __init__(self, user_id: str, target_date: datetime):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        super().__init__(command_prefix='!', intents=intents)
        
        self.target_user_id = user_id
        self.target_date = target_date.date() if isinstance(target_date, datetime) else target_date
        self.user_name = self._get_user_name()
        self.setup_logging()

    def _get_user_name(self) -> str:
        """user_columns.jsonからユーザー名を取得"""
        json_path = Path(__file__).parent.parent / 'config' / 'user_columns.json'
        with open(json_path, 'r', encoding='utf-8') as f:
            users = json.load(f)
            for user in users:
                if user['userId'] == self.target_user_id:
                    return user['name']
        return self.target_user_id

    def setup_logging(self):
        """ユーザー別のログディレクトリを作成し、ログ設定を行う"""
        # ログディレクトリのパスを生成
        log_dir = Path(__file__).parent.parent / 'user_logs' / self.user_name
        log_dir.mkdir(parents=True, exist_ok=True)

        # ログファイル名を生成（例：20250625_messages.log）
        log_file = log_dir / f"{self.target_date.strftime('%Y%m%d')}_messages.log"

        # ログハンドラの設定
        handler = logging.FileHandler(log_file, encoding='utf-8')
        handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))

        # ルートロガーの設定
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        
        # 既存のハンドラをクリア
        for h in logger.handlers[:]:
            logger.removeHandler(h)
        
        # 新しいハンドラを追加（ファイルと標準出力の両方）
        logger.addHandler(handler)
        
        # 標準出力用のハンドラも追加
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        logger.addHandler(console_handler)

    async def on_ready(self):
        logging.info(f"✓ Botとして接続完了: {self.user.name}")
        await self.fetch_messages()
        await self.close()

    async def fetch_messages(self):
        channel = self.get_channel(REPORT_CHANNEL_ID)
        if not channel:
            logging.error("日報チャンネルが見つかりません")
            return

        log_file = Path(__file__).parent.parent / 'user_logs' / self.user_name / f"{self.target_date.strftime('%Y%m%d')}_messages.log"
        
        logging.info("\n==========================================")
        logging.info("=== メッセージ取得処理の開始 ===")
        logging.info("==========================================")
        logging.info(f"対象ユーザー: {self.user_name} (ID: {self.target_user_id})")
        logging.info(f"対象日付: {self.target_date.strftime('%Y/%m/%d')}")
        logging.info(f"対象チャンネル: {channel.name}")
        logging.info(f"ログ出力先: {log_file}")

        # タイムゾーンの設定
        jst = pytz.timezone('Asia/Tokyo')
        now = datetime.now(jst)

        logging.info("\n=== 検索範囲の設定 ===")
        # 検索開始日時の設定（指定日の0:00 JST）
        search_start_jst = jst.localize(
            datetime.combine(self.target_date, datetime.min.time())
        )
        logging.info(f"検索開始日時を設定: {search_start_jst.strftime('%Y/%m/%d %H:%M:%S')} JST")

        # 検索終了日時の設定
        # 指定日の2日後の0:00 JSTを計算
        two_days_later = self.target_date + timedelta(days=2)
        end_date_jst = jst.localize(
            datetime.combine(two_days_later, datetime.min.time())
        )
        logging.info(f"2日後の0:00を計算: {end_date_jst.strftime('%Y/%m/%d %H:%M:%S')} JST")

        # 現在時刻と2日後の0:00を比較し、早い方を採用
        search_end_jst = min(now, end_date_jst)
        logging.info(f"検索終了日時を設定: {search_end_jst.strftime('%Y/%m/%d %H:%M:%S')} JST")
        
        # UTC変換
        search_start_utc = search_start_jst.astimezone(pytz.utc)
        search_end_utc = search_end_jst.astimezone(pytz.utc)
        logging.info("\nUTC変換後の検索範囲:")
        logging.info(f"  開始: {search_start_utc.strftime('%Y/%m/%d %H:%M:%S')} UTC")
        logging.info(f"  終了: {search_end_utc.strftime('%Y/%m/%d %H:%M:%S')} UTC")

        try:
            logging.info("\n=== メッセージ検索の実行 ===")
            message_count = 0
            user_message_count = 0
            date_match_count = 0
            async for message in channel.history(
                after=search_start_utc,
                before=search_end_utc,
                limit=None
            ):
                message_count += 1
                if message_count % 100 == 0:
                    logging.info(f"  - {message_count}件目を処理中...")
                
                if str(message.author.id) == self.target_user_id:
                    user_message_count += 1
                    logging.info(f"\n=== 対象ユーザーのメッセージ #{user_message_count} ===")
                    logging.info(f"投稿日時 (UTC): {message.created_at.strftime('%Y/%m/%d %H:%M:%S')}")
                    logging.info(f"投稿日時 (JST): {message.created_at.astimezone(jst).strftime('%Y/%m/%d %H:%M:%S')}")
                    
                    # メッセージ内容を行ごとに出力
                    lines = message.content.splitlines()
                    logging.info("\nメッセージ内容:")
                    for i, line in enumerate(lines, 1):
                        logging.info(f"    [{i}行目] {line}")
                    
                    # 添付ファイルの情報も出力
                    if message.attachments:
                        logging.info("\n添付ファイル:")
                        for attachment in message.attachments:
                            logging.info(f"    - {attachment.filename} ({attachment.url})")
                    
                    # メッセージへのリンクを出力
                    message_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
                    logging.info(f"\nメッセージリンク: {message_link}")
                    
                    # 日付チェック
                    logging.info("\n=== 日付チェックの実行 ===")
                    from src.message_checker import MessageChecker
                    checker = MessageChecker(target_date=self.target_date)
                    has_date = checker.has_valid_date(message.content)
                    if has_date:
                        date_match_count += 1
                        logging.info(f"✓ 対象日付({self.target_date.strftime('%Y/%m/%d')})を含むメッセージを発見")
                    else:
                        logging.info(f"× 対象日付({self.target_date.strftime('%Y/%m/%d')})は含まれていません")
                    logging.info("===================================\n")

            logging.info("\n=== メッセージ取得結果のサマリー ===")
            logging.info(f"検索したメッセージ総数: {message_count}件")
            logging.info(f"対象ユーザーのメッセージ数: {user_message_count}件")
            logging.info(f"日付マッチ数: {date_match_count}件")
            logging.info("==========================================\n")

        except discord.errors.Forbidden:
            logging.error("チャンネルへのアクセス権限がありません")
        except Exception as e:
            logging.error(f"エラーが発生しました: {str(e)}")

async def fetch_user_messages(token: str, user_id: str, target_date: datetime):
    """
    指定したユーザーの特定日のメッセージを取得する関数
    
    Args:
        token (str): Discordボットトークン
        user_id (str): 対象ユーザーのID
        target_date (datetime): 対象日付
    """
    bot = MessageFetcher(user_id, target_date)
    try:
        await bot.start(token)
    except KeyboardInterrupt:
        await bot.close()
    except Exception as e:
        logging.error(f"予期せぬエラーが発生しました: {str(e)}")
        await bot.close()

if __name__ == "__main__":
    import sys
    
    # コマンドライン引数のチェック
    if len(sys.argv) != 3:
        print("\n=== メッセージ取得ツール ===")
        print("使用方法: python message_fetcher.py <ユーザーID> <日付(YYYY-MM-DD)>")
        print("\n例:")
        print("python message_fetcher.py 1299219753159757844 2025-06-18")
        sys.exit(1)
    
    user_id = sys.argv[1]
    
    # 日付のバリデーション
    try:
        target_date = datetime.strptime(sys.argv[2], "%Y-%m-%d")
    except ValueError:
        print("\nエラー: 日付の形式が正しくありません")
        print("正しい形式: YYYY-MM-DD")
        print("例: 2025-06-18")
        sys.exit(1)
    
    try:
        print("\n=== メッセージ取得ツール ===")
        print(f"処理を開始します...")
        asyncio.run(fetch_user_messages(DISCORD_TOKEN, user_id, target_date))
    except Exception as e:
        print(f"\nエラーが発生しました: {str(e)}")
        print("詳細はログファイルを確認してください。")
        sys.exit(1)