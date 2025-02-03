import os
import json
from dotenv import load_dotenv
from pathlib import Path

# .envファイルのロード
load_dotenv()

def _get_env_var(name: str, required: bool = True) -> str:
    value = os.getenv(name)
    if required and not value:
        raise ValueError(f"Required environment variable {name} is not set")
    return value

def _get_env_int(name: str, required: bool = True) -> int:
    value = _get_env_var(name, required)
    try:
        return int(value)
    except (ValueError, TypeError):
        raise ValueError(f"Environment variable {name} must be an integer")

# Discord設定
DISCORD_TOKEN = _get_env_var('DISCORD_TOKEN')
REPORT_CHANNEL_ID = _get_env_int('DISCORD_REPORT_CHANNEL_ID')
DECLARATION_CHANNEL_ID = _get_env_int('DISCORD_DECLARATION_CHANNEL_ID')

# Google Sheets設定
SPREADSHEET_ID = _get_env_var('SPREADSHEET_ID')
CREDENTIALS_PATH = Path(__file__).parent / 'credentials.json'

# 日付フォーマット設定
DATE_FORMATS = [
    # 年/月/日パターン(優先)
    r'(?<!\d)(?:20)?\d{2}[/-]\d{1,2}[/-]\d{1,2}(?!\d)',  # YYYY/MM/DD, YY/MM/DD
    # 月/日パターン(年/月/日にマッチしない場合のみ)
    r'(?<!\d)\d{1,2}[/-]\d{1,2}(?![/-]\d)(?!\d)',        # MM/DD
    r'\d{1,2}月\d{1,2}日'                                # MM月DD日
]

# 1月1日の開始行
START_ROW = 7  # 7行目からデータ開始

# Discord設定の追加
MESSAGE_HISTORY_LIMIT = 100  # メッセージ履歴取得の制限

# ユーザー設定の読み込み
def _column_to_index(column: str) -> int:
    # 列名(A,B,C...)を数値インデックス(0,1,2...)に変換
    return sum((ord(char) - ord('A') + 1) * (26 ** i)
            for i, char in enumerate(reversed(column))) - 1

def _index_to_column(index: int) -> str:
    # 数値インデックスを列名に変換
    index += 1
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(ord('A') + remainder) + result
    return result

def _load_user_columns():
    json_path = Path(__file__).parent / 'user_columns.json'
    with open(json_path, 'r', encoding='utf-8') as f:
        users = json.load(f)
    
    # ユーザー列の設定を変換
    user_columns = {}
    for user in users:
        sangen_col = user['sengenCol']
        # 列名を数値インデックスに変換、1を加算して次の列を取得、再び列名に変換
        sangen_index = _column_to_index(sangen_col)
        report_col = _index_to_column(sangen_index + 1)
        user_columns[user['userId']] = {
            "declaration": sangen_col,
            "report": report_col
        }
    return user_columns

# ユーザーIDと列の対応
USER_COLUMNS = _load_user_columns()