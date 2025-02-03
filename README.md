# Discord 日報・宣言チェックBot

Discordの特定チャンネルで投稿された日報と宣言を自動でチェックし、Google Spreadsheetsに記録するBotです。

## 機能

- 指定された日付の日報・宣言の投稿状況を確認
- 日付フォーマットの自動認識(YYYY/MM/DD, YYYY-MM-DD, MM/DD, M月D日など)
- Google Spreadsheetsへの自動記録
- バッチ処理による効率的な更新
- エラーハンドリングと再試行機能

## セットアップ

1. リポジトリのクローン
```bash
git clone https://github.com/your-username/genkai_zero_discord.git
cd genkai_zero_discord
```

2. Python仮想環境の作成と有効化
```bash
python -m venv myenv
# Windows
myenv\Scripts\activate
# macOS/Linux
source myenv/bin/activate
```

3. 依存パッケージのインストール
```bash
pip install -r requirements.txt
```

4. 設定ファイルの準備
- `.env`ファイルを作成
- `config/credentials.json`を作成(Google Cloud Platformで取得した認証情報)
- `config/user_columns.json`を作成(ユーザー情報の設定)

## 設定ファイル

### .env

以下の環境変数を設定します:

```env
# Discord Bot設定
DISCORD_TOKEN=your_discord_bot_token
DISCORD_REPORT_CHANNEL_ID=1234567890
DISCORD_DECLARATION_CHANNEL_ID=1234567890

# Google Sheets設定
SPREADSHEET_ID=your_spreadsheet_id
```

各環境変数の説明:
- `DISCORD_TOKEN`: Discord Botのトークン
- `DISCORD_REPORT_CHANNEL_ID`: 日報チャンネルのID
- `DISCORD_DECLARATION_CHANNEL_ID`: 宣言チャンネルのID
- `SPREADSHEET_ID`: Google SpreadsheetsのID(URLの一部)

### credentials.json

Google Cloud Platformで取得した認証情報を以下のフォーマットで保存します:

```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "your-private-key-id",
  "private_key": "your-private-key",
  "client_email": "your-client-email",
  "client_id": "your-client-id",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "your-cert-url"
}
```

### user_columns.json

ユーザー情報を以下のフォーマットで設定します:

```json
[
    {
        "userId": "123456789012345678",
        "name": "ユーザー1",
        "sengenCol": "C"
    },
    {
        "userId": "234567890123456789",
        "name": "ユーザー2",
        "sengenCol": "E"
    }
]
```

## 使用方法

### 基本的な実行

現在の日付でチェックを実行:
```bash
python run.py
```

特定の日付を指定してチェックを実行:
```bash
python run.py --date 2025/01/30
```

### オプション

- `--date`: チェックする日付を指定(YYYY/MM/DD形式)
  - 指定がない場合は本日の日付が使用されます

### 実行結果

- 各ユーザーの日報・宣言の状態を確認
- Google Spreadsheetsに結果を記録
- 処理の詳細なログを出力

## パフォーマンステスト

バッチ処理のパフォーマンスを確認:
```bash
python tests/test_performance.py
```

## エラーハンドリング

- Discord APIの制限やネットワークエラーに対する再試行機能
- Google Sheets APIの制限を考慮したバッチ処理
- 詳細なエラーログの出力

## 注意事項

- .envファイルには機密情報が含まれるため、Gitにコミットしないでください
- credentials.jsonには機密情報が含まれるため、Gitにコミットしないでください
- user_columns.jsonにはユーザー情報が含まれるため、Gitにコミットしないでください
- 実行時は必ず仮想環境を有効化してください