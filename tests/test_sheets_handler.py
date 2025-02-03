import unittest
from unittest.mock import Mock, patch
from datetime import datetime
from src.sheets_handler import SheetsHandler
from config.config import USER_COLUMNS

class TestSheetsHandler(unittest.TestCase):
    def setUp(self):
        # Google APIのモック化
        self.mock_service = Mock()
        patcher = patch('src.sheets_handler.build')
        self.addCleanup(patcher.stop)
        mock_build = patcher.start()
        mock_build.return_value = self.mock_service

        # 認証情報のモック化
        patcher = patch('src.sheets_handler.service_account.Credentials.from_service_account_file')
        self.addCleanup(patcher.stop)
        patcher.start()

        self.sheets_handler = SheetsHandler()
        self.test_date = datetime(2025, 1, 28)
        self.test_user_id = list(USER_COLUMNS.keys())[0]

    def test_write_check_result(self):
        # モックの設定
        mock_spreadsheets = Mock()
        self.mock_service.spreadsheets.return_value = mock_spreadsheets
        mock_spreadsheets.batchUpdate.return_value.execute.return_value = {}
        mock_spreadsheets.values.return_value.batchUpdate.return_value.execute.return_value = {}

        # テストの実行
        self.sheets_handler.write_check_result(
            self.test_date,
            self.test_user_id,
            True,  # report_status
            False  # declaration_status
        )

        # バッチ更新が呼び出されたことを確認
        mock_spreadsheets.batchUpdate.assert_called_once()
        mock_spreadsheets.values.return_value.batchUpdate.assert_called_once()

        # 値の更新リクエストの内容を確認
        values_update_call = mock_spreadsheets.values.return_value.batchUpdate.call_args
        update_body = values_update_call[1]['body']
        
        # 正しい値が設定されていることを確認
        self.assertEqual(update_body['valueInputOption'], 'USER_ENTERED')
        data = update_body['data']
        self.assertEqual(len(data), 2)  # report と declaration の2つの更新

        # 値が正しく設定されていることを確認
        report_values = data[0]['values']
        declaration_values = data[1]['values']
        self.assertEqual(report_values, ['○'])  # True -> ○
        self.assertEqual(declaration_values, ['×'])  # False -> ×

    def test_get_row_index(self):
        test_cases = [
            (datetime(2025, 1, 1), 2),   # 年始（START_ROW）
            (datetime(2025, 1, 28), 29), # テスト日
            (datetime(2025, 12, 31), 366)  # 年末
        ]

        for test_date, expected_row in test_cases:
            with self.subTest(date=test_date):
                row = self.sheets_handler._get_row_index(test_date)
                self.assertEqual(row, expected_row)

    def test_column_to_index(self):
        test_cases = [
            ('A', 0),
            ('B', 1),
            ('Z', 25),
            ('AA', 26),
            ('AB', 27)
        ]

        for column, expected_index in test_cases:
            with self.subTest(column=column):
                index = self.sheets_handler._column_to_index(column)
                self.assertEqual(index, expected_index)

    def test_invalid_user_id(self):
        with self.assertRaises(ValueError):
            self.sheets_handler.write_check_result(
                self.test_date,
                'invalid_user_id',
                True,
                True
            )

if __name__ == '__main__':
    unittest.main()