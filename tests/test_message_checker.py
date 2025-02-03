import unittest
from datetime import datetime
from src.message_checker import MessageChecker

class TestMessageChecker(unittest.TestCase):
    def setUp(self):
        self.target_date = datetime(2025, 1, 28)
        self.checker = MessageChecker(self.target_date)

    def test_valid_date_formats(self):
        valid_messages = [
            "今日の報告です 2025/1/28",
            "報告 2025-01-28",
            "1/28の報告",
            "01-28 報告します",
            "【2025/1/28】報告"
        ]
        for message in valid_messages:
            with self.subTest(message=message):
                self.assertTrue(self.checker.has_valid_date(message))

    def test_invalid_date_formats(self):
        invalid_messages = [
            "",  # 空文字列
            "今日の報告です",  # 日付なし
            "2025/13/28",  # 無効な月
            "2025/1/32",   # 無効な日
            "報告 2024/1/28",  # 異なる年
            "報告 2025/1/27",  # 異なる日
        ]
        for message in invalid_messages:
            with self.subTest(message=message):
                self.assertFalse(self.checker.has_valid_date(message))

    def test_parse_date(self):
        test_cases = [
            ("2025/1/28", datetime(2025, 1, 28)),
            ("2025-01-28", datetime(2025, 1, 28)),
            ("1/28", datetime(2025, 1, 28)),  # 年なしの場合は現在の年を使用
            ("01-28", datetime(2025, 1, 28))  # 年なしの場合は現在の年を使用
        ]
        for date_str, expected in test_cases:
            with self.subTest(date_str=date_str):
                result = self.checker._parse_date(date_str)
                if len(date_str.split('/')[0]) == 2 or len(date_str.split('-')[0]) == 2:
                    result = result.replace(year=self.target_date.year)
                self.assertEqual(result.date(), expected.date())

    def test_invalid_parse_date(self):
        invalid_dates = [
            "2025/13/28",  # 無効な月
            "2025/1/32",   # 無効な日
            "invalid",     # 無効なフォーマット
            "2025-1",     # 不完全なフォーマット
        ]
        for date_str in invalid_dates:
            with self.subTest(date_str=date_str):
                with self.assertRaises(ValueError):
                    self.checker._parse_date(date_str)

if __name__ == '__main__':
    unittest.main()