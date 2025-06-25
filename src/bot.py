import discord
from discord.ext import commands
from discord.ext import tasks
from datetime import datetime, timedelta
import asyncio
import logging
import pytz
from typing import Optional, List, Tuple, Dict

from config.config import (
    USER_COLUMNS,
    REPORT_CHANNEL_ID,
    DECLARATION_CHANNEL_ID,
    MESSAGE_HISTORY_LIMIT
)
from src.message_checker import MessageChecker
from src.sheets_handler import SheetsHandler

class ReportBot(commands.Bot):
    def __init__(self, target_date=None, batch_size=5):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        super().__init__(command_prefix='!', intents=intents)
        
        # 指定された日付、または現在の日付を使用
        self.target_date = target_date.date() if isinstance(target_date, datetime) else target_date or datetime.now().date()
        logging.info(f"チェック対象日: {self.target_date.strftime('%Y/%m/%d')}")
        
        self.message_checker = MessageChecker(target_date=self.target_date, batch_size=batch_size)
        self.sheets_handler = SheetsHandler()
        self.batch_size = batch_size

    async def on_ready(self):
        logging.info("✓ Discordサーバーへの接続が完了しました")
        logging.info(f"Bot名: {self.user.name}")
        logging.info(f"Bot ID: {self.user.id}")
        
        # 接続完了後に即座にチェックを実行
        await self._check_all_channels()

    async def close(self):
        logging.info("✓ プログラムを終了します")
        await super().close()

    def _create_user_batches(self) -> List[List[str]]:
        """ユーザーIDをバッチに分割する"""
        user_ids = list(USER_COLUMNS.keys())
        batches = []
        for i in range(0, len(user_ids), self.batch_size):
            batch = user_ids[i:i + self.batch_size]
            batches.append(batch)
        return batches

    async def _fetch_user_names(self, user_ids: List[str]) -> Dict[str, str]:
        """指定されたユーザーIDのユーザー名をフェッチする"""
        user_names = {}
        for user_id in user_ids:
            try:
                user = await self.fetch_user(int(user_id))
                user_names[user_id] = user.name
            except:
                user_names[user_id] = user_id
        return user_names

    async def _check_all_channels(self):
        logging.info("=== 日次チェック開始 ===")
        check_time = datetime.combine(self.target_date, datetime.min.time())
        logging.info(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logging.info(f"チェック対象日: {self.target_date.strftime('%Y/%m/%d')}")

        report_channel = self.get_channel(REPORT_CHANNEL_ID)
        declaration_channel = self.get_channel(DECLARATION_CHANNEL_ID)

        if not report_channel or not declaration_channel:
            logging.error("エラー: チャンネルが見つかりません")
            return

        logging.info("チェック対象チャンネル:")
        logging.info(f"- 報告チャンネル: {report_channel.name}")
        logging.info(f"- 宣言チャンネル: {declaration_channel.name}")

        # ユーザーをバッチに分割
        batches = self._create_user_batches()
        logging.info(f"全{len(USER_COLUMNS)}人のユーザーを{len(batches)}バッチに分割して処理します")
        logging.info(f"バッチサイズ: {self.batch_size}人")

        all_updates = []
        total_start_time = datetime.now()

        for batch_num, user_batch in enumerate(batches, 1):
            batch_start_time = datetime.now()
            logging.info(f"=== バッチ {batch_num}/{len(batches)} の処理開始 ===")
            
            # バッチ内のユーザー名をフェッチ
            user_names = await self._fetch_user_names(user_batch)
            
            # バッチ内の各ユーザーをチェック
            batch_updates = []
            for user_id in user_batch:
                user_name = user_names.get(user_id, user_id)
                config_name = USER_COLUMNS.get(user_id, {}).get("name", "N/A")
                logging.info("========================================")
                logging.info(f"🧑 ユーザー処理開始: {user_name} (ID: {user_id}) - 名前: {config_name}")
                
                logging.info("📌 報告チャンネルをチェック中...")
                report_status = await self._check_channel(report_channel, user_id)
                logging.info(f"📝 報告状態: {'○' if report_status else '×'}")
                
                logging.info("📌 宣言チャンネルをチェック中...")
                declaration_status = await self._check_channel(declaration_channel, user_id)
                logging.info(f"📝 宣言状態: {'○' if declaration_status else '×'}")
                
                logging.info(f"✅ ユーザー処理完了: {user_name}")
                
                # 結果をバッチリストに追加
                batch_updates.append((check_time, user_id, report_status, declaration_status))
            
            # バッチの結果をGoogle Sheetsに書き込み
            logging.info("Google Sheetsにバッチ結果を書き込み中...")
            try:
                await self.sheets_handler.write_check_results(batch_updates)
                all_updates.extend(batch_updates)
                
                batch_end_time = datetime.now()
                batch_processing_time = (batch_end_time - batch_start_time).total_seconds()
                logging.info(f"✓ バッチ {batch_num} 完了 (処理時間: {batch_processing_time:.2f}秒)")
            except Exception as e:
                logging.error(f"× バッチ {batch_num} 書き込みエラー: {str(e)}")

        total_end_time = datetime.now()
        total_processing_time = (total_end_time - total_start_time).total_seconds()
        logging.info(f"全バッチ処理完了 (総処理時間: {total_processing_time:.2f}秒)")
        logging.info(f"処理したユーザー数: {len(all_updates)}")

        logging.info("=== 日次チェック完了 ===")
        # チェック完了後にBotを終了
        await self.close()

    def _get_channel_config(self, channel) -> tuple:
        """チャンネル固有の設定を取得"""
        if channel.id == REPORT_CHANNEL_ID:
            return {
                'type': "日報",
                'date_offset': 0,  # 当日
                'description': "日報チャンネル"
            }
        elif channel.id == DECLARATION_CHANNEL_ID:
            return {
                'type': "宣言",
                'date_offset': -1,  # 前日
                'description': "宣言チャンネル"
            }
        else:
            logging.warning(f"未定義チャンネル {channel.name}")
            return {
                'type': "未定義",
                'date_offset': 0,
                'description': f"未定義チャンネル: {channel.name}"
            }

    def _get_search_range(self, base_date: datetime, time_info: dict) -> tuple:
        """検索範囲を計算"""
        jst = time_info['jst']
        now = time_info['now']
        
        # 検索開始日時（指定日の0:00 JST）
        search_start_jst = jst.localize(datetime.combine(base_date, datetime.min.time()))
        
        # 検索終了日時（指定日の2日後の0:00 JSTまたは現在時刻）
        two_days_later = base_date + timedelta(days=2)
        end_date_jst = jst.localize(datetime.combine(two_days_later, datetime.min.time()))
        search_end_jst = min(now, end_date_jst)
        
        # UTC変換
        search_start_utc = search_start_jst.astimezone(pytz.utc)
        search_end_utc = search_end_jst.astimezone(pytz.utc)
        
        # 検索範囲の情報をログ出力
        logging.info(f"\n検索範囲:")
        logging.info(f"  開始: {search_start_jst.strftime('%Y/%m/%d %H:%M:%S')} JST")
        logging.info(f"  終了: {search_end_jst.strftime('%Y/%m/%d %H:%M:%S')} JST")
        if search_end_jst == now:
            logging.info("  ※ 現在時刻までを検索範囲としています")
        else:
            logging.info("  ※ 指定日の2日後の0:00までを検索範囲としています")
        
        return search_start_jst, search_end_jst, search_start_utc, search_end_utc

    async def _check_channel(self, channel, user_id) -> bool:
        if not channel:
            error_msg = f"Channel not found for user {user_id}"
            logging.error(f"エラー: {error_msg}")
            return False

        try:
            def _init_time_info(target_date: datetime) -> dict:
                """時刻関連の情報を初期化"""
                jst = pytz.timezone('Asia/Tokyo')
                now = datetime.now(jst)
                
                return {
                    'jst': jst,
                    'now': now,
                    'target_date': target_date
                }

            # チャンネル設定を取得
            config = self._get_channel_config(channel)
            channel_type = config['type']
            
            # 検索対象日を計算
            target_date = self.target_date + timedelta(days=config['date_offset'])
            
            # 時刻関連の情報を初期化
            time_info = _init_time_info(target_date)
            jst = time_info['jst']
            now = time_info['now']
            
            logging.info(f"\n=== {config['description']}の検索開始 ===")
            logging.info(f"チャンネル名: {channel.name}")
            logging.info(f"ユーザーID: {user_id}")
            logging.info(f"対象日: {target_date.strftime('%Y/%m/%d')}")

            # 検索範囲を取得（ログ出力も_get_search_range内で行う）
            search_start_jst, search_end_jst, search_start_utc, search_end_utc = self._get_search_range(target_date, time_info)
            
            # 時刻情報を含む状態を初期化
            state = {
                'message_count': 0,
                'user_message_count': 0,
                'thread_message_count': 0,
                'matched_messages': [],
                'last_message_time': None,
                'stats': {
                    'main_channel': 0,
                    'thread': 0,
                    'user_main': 0,
                    'user_thread': 0
                },
                'time_info': time_info  # 時刻関連の情報を状態に含める
            }
            
            logging.info("\nメッセージ検索開始...")
            logging.info("メッセージ一覧:")

            # 進捗報告用の設定
            progress_interval = 10  # 10件ごとに進捗を報告
            logging.info("\nメッセージ取得設定:")
            logging.info("- 取得順序: 古い順")
            logging.info("- 開始日時: " + search_start_utc.strftime('%Y/%m/%d %H:%M:%S UTC'))
            logging.info("- 終了日時: " + search_end_utc.strftime('%Y/%m/%d %H:%M:%S UTC'))
            
            def _update_stats(state: dict, message: discord.Message, user_id: str):
                """統計情報を更新"""
                if message.thread:
                    state['stats']['thread'] += 1
                    if str(message.author.id) == user_id:
                        state['stats']['user_thread'] += 1
                else:
                    state['stats']['main_channel'] += 1
                    if str(message.author.id) == user_id:
                        state['stats']['user_main'] += 1

            def _log_message_info(message: discord.Message, count: int, thread_info: str, jst: pytz.timezone):
                """メッセージの基本情報をログ出力"""
                created_at_jst = message.created_at.astimezone(jst)
                logging.info(f"\n=== メッセージ #{count} {thread_info} ===")
                logging.info(f"作成日時 (UTC): {message.created_at.strftime('%Y/%m/%d %H:%M:%S')}")
                logging.info(f"作成日時 (JST): {created_at_jst.strftime('%Y/%m/%d %H:%M:%S')}")
                logging.info(f"作成者: {message.author.name} (ID: {message.author.id})")
                logging.info(f"内容の先頭行: {message.content.split('\n')[0][:100]}")
                if message.thread:
                    logging.info(f"スレッド名: {message.thread.name}")
                    logging.info(f"スレッドID: {message.thread.id}")

            async for message in channel.history(
                after=search_start_utc,
                before=search_end_utc,
                limit=None,
                oldest_first=True  # 古いメッセージから順に取得
            ):
                state['message_count'] += 1
                
                # スレッド内のメッセージの記録
                thread_info = "（スレッド内）" if message.thread else "（メインチャンネル）"
                
                # 進捗報告
                if state['message_count'] % progress_interval == 0:
                    logging.info(f"\n進捗状況: {state['message_count']}件目を処理中...")
                    if state['last_message_time']:
                        logging.info(f"現在の処理位置: {state['last_message_time'].astimezone(jst).strftime('%Y/%m/%d %H:%M:%S JST')}")

                # メッセージの基本情報を出力
                _log_message_info(message, state['message_count'], thread_info, jst)
                
                # 最後のメッセージ時刻を更新
                state['last_message_time'] = message.created_at
                
                # 対象ユーザーのメッセージのみを処理
                logging.info("ユーザーチェック:")
                logging.info(f"- メッセージの author.id: {message.author.id} ({type(message.author.id)})")
                logging.info(f"- 比較対象の user_id: {user_id} ({type(user_id)})")
                if str(message.author.id) == user_id:
                    state['user_message_count'] += 1
                    logging.info(f"✓ ユーザーIDが一致")
                    logging.info(f"\n=== ユーザーメッセージ #{state['user_message_count']} ===")
                    logging.info(f"投稿日時 (UTC): {message.created_at.strftime('%Y/%m/%d %H:%M:%S')}")
                    logging.info(f"投稿日時 (JST): {message.created_at.astimezone(jst).strftime('%Y/%m/%d %H:%M:%S')}")
                    
                    lines = message.content.splitlines()
                    logging.info("メッセージ内容:")
                    for i, line in enumerate(lines[:10], 1):
                        logging.info(f"    [{i}行目] {line}")
                    if len(lines) > 10:
                        logging.info("    （※ 11行目以降は省略）")
                    
                    logging.info("\n日付チェック開始...")
                    if self.message_checker.has_valid_date(message.content):
                        logging.info("✓ 対象日の日付を含むメッセージを発見")
                        state['matched_messages'].append(message)
                        return True
                    else:
                        logging.info("× このメッセージは対象日の日付を含んでいません")

                # 統計情報を更新
                _update_stats(state, message, user_id)

            def _log_search_summary(state: dict, channel_type: str, jst: pytz.timezone,
                                search_start_utc: datetime, search_end_utc: datetime,
                                last_message: discord.Message, now: datetime) -> None:
                """検索結果のサマリーを出力"""
                logging.info(f"\n検索結果サマリー:")
                logging.info(f"- 総メッセージ数: {state['message_count']}件")
                logging.info(f"  * メインチャンネル: {state['stats']['main_channel']}件")
                logging.info(f"  * スレッド内: {state['stats']['thread']}件")
                logging.info(f"- ユーザーのメッセージ数: {state['user_message_count']}件")
                logging.info(f"  * メインチャンネル: {state['stats']['user_main']}件")
                logging.info(f"  * スレッド内: {state['stats']['user_thread']}件")
                logging.info(f"- 日付マッチ数: {len(state['matched_messages'])}件")
                
                if state['last_message_time']:
                    first_message_time = state['last_message_time']  # 最後に保存された時刻が最古のメッセージ（oldest_first=Trueのため）
                    logging.info("\n取得されたメッセージの時間範囲:")
                    logging.info(f"- 最古のメッセージ: {first_message_time.astimezone(jst).strftime('%Y/%m/%d %H:%M:%S JST')}")
                    logging.info(f"- 最新のメッセージ: {last_message.created_at.astimezone(jst).strftime('%Y/%m/%d %H:%M:%S JST')}")
                    
                    # 検索範囲の検証
                    _validate_search_range(first_message_time, last_message.created_at,
                                      search_start_utc, search_end_utc)
                
                if not state['matched_messages']:
                    logging.warning(f"- 対象日の日付を含むメッセージが見つかりませんでした")
                
                logging.info(f"=== {channel_type}チャンネルの検索終了 ===\n")

            def _validate_search_range(first_time: datetime, last_time: datetime,
                                  start_utc: datetime, end_utc: datetime) -> None:
                """検索範囲の妥当性を検証"""
                if first_time > start_utc:
                    logging.warning("! 注意: 検索開始日時までのメッセージが取得できていない可能性があります")
                if last_time < end_utc:
                    logging.warning("! 注意: 検索終了日時までのメッセージが取得できていない可能性があります")

            # 検索結果のサマリーを出力
            _log_search_summary(state, channel_type, jst, search_start_utc, search_end_utc, message, now)
            return False

        except (discord.errors.Forbidden, discord.errors.HTTPException, Exception) as e:
            error_type = type(e).__name__
            error_msg = f"{error_type} in {channel.name}: {str(e)}"
            logging.error(f"エラー: {error_msg}")
            return False