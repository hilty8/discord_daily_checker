from datetime import datetime, date
import re
from typing import List, Dict
import logging
from config.config import DATE_FORMATS

class MessageChecker:
    def __init__(self, target_date: datetime = None, batch_size: int = 5):
        self.target_date = target_date or datetime.now()
        self.batch_size = batch_size

    def process_users_in_batches(self, users: List[Dict]) -> List[List[Dict]]:
        """ユーザーリストをバッチサイズごとに分割する"""
        batches = []
        for i in range(0, len(users), self.batch_size):
            batch = users[i:i + self.batch_size]
            batches.append(batch)
        return batches

    def has_valid_date(self, content: str) -> bool:
        if not content:
            logging.info("    × 内容が空です")
            return False

        # メッセージを行に分割し、最初の10行を取得
        lines = content.split('\n')[:10]
        logging.info("\n    最初の10行を確認:")
        for i, line in enumerate(lines, 1):
            logging.info(f"    {i}行目: {line}")

        # 各行で日付パターンを確認
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue

            logging.info(f"\n    {i}行目の日付チェック:")
            # 各パターンで完全一致を試行
            for pattern in DATE_FORMATS:
                logging.info(f"    パターン: {pattern}")
                logging.info(f"    チェック対象行: '{line}'")
                matches = re.finditer(pattern, line)
                match_found = False
                
                for match in matches:
                    match_found = True
                    date_str = match.group()
                    logging.info(f"    マッチ: '{date_str}' (位置: {match.start()}-{match.end()})")
                    # マッチした部分が行の一部に含まれているか確認
                    if date_str in line:
                        try:
                            date = self._parse_date(date_str)
                            if not date:
                                logging.info(f"    × 日付のパースに失敗: '{date_str}'")
                                continue

                            # 年が指定されていない場合は現在の年を使用
                            if date.year == 1900:
                                date = date.replace(year=self.target_date.year)
                                logging.info(f"    年の補完: {date.strftime('%Y/%m/%d')}")

                            logging.info(f"    検出: '{date_str}' → '{date.strftime('%Y/%m/%d')}'")
                            check_date = date.date()
                            target_date = self.target_date if hasattr(self.target_date, 'date') else self.target_date
                            
                            logging.info(f"    比較: 検出={check_date} vs 目標={target_date}")
                            if check_date == target_date:
                                logging.info(f"    ✓ {self.target_date.strftime('%Y/%m/%d')}の日付を確認")
                                return True
                            else:
                                logging.info(f"    × {self.target_date.strftime('%Y/%m/%d')}と一致しません")
                                # 一致しない場合は次のパターンを試す
                                continue
                        except ValueError as e:
                            logging.info(f"    日付パースエラー '{date_str}': {str(e)}")
                            continue
                
                if not match_found:
                    logging.info(f"    × このパターンではマッチしませんでした")

        logging.info(f"\n    × 対象の日付が見つかりません")
        return False

    def _parse_date(self, date_str: str) -> datetime:
        # 全角括弧と余分な文字を除去
        date_str = date_str.replace('【', '').replace('】', '')
        date_str = date_str.replace('［', '').replace('］', '')
        date_str = date_str.replace('「', '').replace('」', '')
        
        # "日報"などの文字列を除去
        date_str = re.sub(r'日[報誌記].*$', '', date_str)
        date_str = date_str.strip()
        
        logging.info(f"    クリーニング後の日付文字列: '{date_str}'")
        
        # 月日形式（MM月DD日）のチェック
        if '月' in date_str and '日' in date_str:
            try:
                month = int(re.search(r'(\d{1,2})月', date_str).group(1))
                day = int(re.search(r'月(\d{1,2})日', date_str).group(1))
                year = self.target_date.year
                return datetime(year, month, day)
            except (ValueError, IndexError, AttributeError):
                pass  # 他の形式を試す

        # スラッシュとハイフンの両方に対応
        separators = ['/', '-']
        parts = None
        
        for sep in separators:
            if sep in date_str:
                # 数字以外の文字を含む部分を除去してから分割
                clean_date = re.sub(r'[^\d' + sep + ']', '', date_str)
                parts = clean_date.split(sep)
                break
        
        if not parts:
            raise ValueError(f"Invalid date format: {date_str}")

        parts = [p.strip() for p in parts]  # 空白を削除
        parts = [re.sub(r'\D', '', p) for p in parts]  # 数字以外を除去
            
        # 年/月/日の判定
        if len(parts) == 3:
            # YY/MM/DD または YYYY/MM/DD
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
            
            if year < 100:  # 2桁年の場合
                if 0 <= year <= 99:
                    year = 2000 + year
        else:
            # MM/DD
            year = self.target_date.year
            try:
                month = int(parts[0])
                day = int(parts[1])
            except (ValueError, IndexError):
                raise ValueError(f"Invalid date parts: {parts}")
            
        # 日付の妥当性チェック
        if not (1 <= month <= 12 and 1 <= day <= 31):
            raise ValueError(f"Invalid date values: month={month}, day={day}")
            
        try:
            return datetime(year, month, day)
        except ValueError:
            raise ValueError(f"Invalid date combination: year={year}, month={month}, day={day}")