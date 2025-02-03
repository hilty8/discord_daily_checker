import discord
from discord.ext import commands
from discord.ext import tasks
from datetime import datetime
import asyncio
from typing import Optional, List, Tuple

from config.config import (
    USER_COLUMNS,
    REPORT_CHANNEL_ID,
    DECLARATION_CHANNEL_ID,
    MESSAGE_HISTORY_LIMIT
)
from src.message_checker import MessageChecker
from src.sheets_handler import SheetsHandler

class ReportBot(commands.Bot):
    def __init__(self, target_date=None):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        super().__init__(command_prefix='!', intents=intents)
        
        # 指定された日付、または現在の日付を使用
        self.target_date = target_date.date() if isinstance(target_date, datetime) else target_date or datetime.now().date()
        print(f"チェック対象日: {self.target_date.strftime('%Y/%m/%d')}")
        
        self.message_checker = MessageChecker(target_date=self.target_date)
        self.sheets_handler = SheetsHandler()

    async def on_ready(self):
        print(f"\n✓ Discordサーバーへの接続が完了しました")
        print(f"Bot名: {self.user.name}")
        print(f"Bot ID: {self.user.id}")
        
        # 接続完了後に即座にチェックを実行
        await self._check_all_channels()

    async def close(self):
        print("\n✓ プログラムを終了します")
        await super().close()

    async def _check_all_channels(self):
        print("\n=== 日次チェック開始 ===")
        check_time = datetime.combine(self.target_date, datetime.min.time())
        print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"チェック対象日: {self.target_date.strftime('%Y/%m/%d')}")

        report_channel = self.get_channel(REPORT_CHANNEL_ID)
        declaration_channel = self.get_channel(DECLARATION_CHANNEL_ID)

        if not report_channel or not declaration_channel:
            print("エラー: チャンネルが見つかりません")
            return

        print(f"\nチェック対象チャンネル:")
        print(f"- 報告チャンネル: {report_channel.name}")
        print(f"- 宣言チャンネル: {declaration_channel.name}")

        # ユーザー名のキャッシュを作成
        user_names = {}
        for user_id in USER_COLUMNS.keys():
            try:
                user = await self.fetch_user(int(user_id))
                user_names[user_id] = user.name
            except:
                user_names[user_id] = user_id

        # 全ユーザーの結果を格納するリスト
        updates: List[Tuple[datetime, str, bool, bool]] = []

        for user_id in USER_COLUMNS.keys():
            user_name = user_names.get(user_id, user_id)
            print(f"\nユーザー: {user_name} (ID: {user_id}) のチェックを開始")
            
            print("報告チャンネルをチェック中...")
            report_status = await self._check_channel(report_channel, user_id)
            print(f"- 報告状態: {'○' if report_status else '×'}")
            
            print("宣言チャンネルをチェック中...")
            declaration_status = await self._check_channel(declaration_channel, user_id)
            print(f"- 宣言状態: {'○' if declaration_status else '×'}")
            
            # 結果をリストに追加
            updates.append((check_time, user_id, report_status, declaration_status))

        # バッチ処理で一括更新
        print("\nGoogle Sheetsに結果を一括書き込み中...")
        try:
            start_time = datetime.now()
            await self.sheets_handler.write_check_results(updates)
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            print(f"✓ 書き込み完了 (処理時間: {processing_time:.2f}秒)")
        except Exception as e:
            print(f"× 書き込みエラー: {str(e)}")

        print("\n=== 日次チェック完了 ===")
        # チェック完了後にBotを終了
        await self.close()

    async def _check_channel(self, channel, user_id) -> bool:
        if not channel:
            error_msg = f"Channel not found for user {user_id}"
            print(f"エラー: {error_msg}")
            return False

        try:
            # 必要なメッセージ数を計算
            days_diff = (datetime.now().date() - self.target_date).days
            required_messages = days_diff + 2  # 今日なら2件、1日前なら3件...
            print(f"- ユーザーのメッセージを検索中...(最新{required_messages}件)")
            user_messages = []
            async for message in channel.history(limit=None):  # 制限なし
                # スレッド内のメッセージは除外
                if message.thread:
                    continue
                    
                if str(message.author.id) == user_id:
                    user_messages.append(message)
                    # 指定日からの日数 + 2件を取得
                    days_diff = (datetime.now().date() - self.target_date).days
                    required_messages = days_diff + 2  # 今日なら2件、1日前なら3件...
                    
                    if len(user_messages) >= required_messages:
                        break

            if not user_messages:
                error_msg = f"User {user_id} has no messages in {channel.name}"
                print(f"- メッセージなし: {error_msg}")
                return False

            print(f"- {len(user_messages)}件のメッセージを取得")
            for msg in user_messages:
                print("\n=== メッセージ開始 ===")
                print(f"{msg.content}")
                print("=== メッセージ終了 ===\n")
                if self.message_checker.has_valid_date(msg.content):
                    return True

            print("- 対象日の日付が見つかりませんでした")
            return False
            
        except discord.errors.Forbidden:
            error_msg = f"Bot lacks permission to read {channel.name}"
            print(f"エラー: {error_msg}")
            return False
        except discord.errors.HTTPException as e:
            error_msg = f"Error in {channel.name}: {str(e)}"
            print(f"エラー: {error_msg}")
            return False
        except Exception as e:
            error_msg = f"Unexpected error in {channel.name}: {str(e)}"
            print(f"エラー: {error_msg}")
            return False