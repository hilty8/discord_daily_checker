from datetime import datetime, date
import re
from config.config import DATE_FORMATS

class MessageChecker:
    def __init__(self, target_date: datetime = None):
        self.target_date = target_date or datetime.now()

    def has_valid_date(self, content: str) -> bool:
        if not content:
            return False

        # メッセージを行に分割し、最初の5行を取得
        lines = content.split('\n')[:5]
        print(f"\n    最初の5行を確認:")
        for i, line in enumerate(lines, 1):
            print(f"    {i}行目: {line}")

        # 各行で日付パターンを確認
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue

            print(f"\n    {i}行目の日付チェック:")
            # 各パターンで完全一致を試行
            for pattern in DATE_FORMATS:
                matches = re.finditer(pattern, line)
                for match in matches:
                    date_str = match.group()
                    # マッチした部分が行の一部に含まれているか確認
                    if date_str in line:
                        try:
                            date = self._parse_date(date_str)
                            if not date:
                                continue

                            # 年が指定されていない場合は現在の年を使用
                            if date.year == 1900:
                                date = date.replace(year=self.target_date.year)

                            print(f"    検出: {date_str} → {date.strftime('%Y/%m/%d')}")
                            check_date = date.date()
                            target_date = self.target_date if hasattr(self.target_date, 'date') else self.target_date
                            
                            if check_date == target_date:
                                print(f"    ✓ {self.target_date.strftime('%Y/%m/%d')}の日付を確認")
                                return True
                            else:
                                print(f"    × {self.target_date.strftime('%Y/%m/%d')}と一致しません")
                                # 日付が見つかったが一致しない場合は、他のパターンを試す必要なし
                                return False
                        except ValueError as e:
                            print(f"    日付パースエラー '{date_str}': {str(e)}")
                            continue

                            # 年が指定されていない場合は現在の年を使用
                            if date.year == 1900:
                                date = date.replace(year=self.target_date.year)

                            print(f"    検出: {date_str} → {date.strftime('%Y/%m/%d')}")
                            check_date = date.date()
                            target_date = self.target_date if hasattr(self.target_date, 'date') else self.target_date
                            
                            if check_date == target_date:
                                print(f"    ✓ {self.target_date.strftime('%Y/%m/%d')}の日付を確認")
                                return True
                            else:
                                print(f"    × {self.target_date.strftime('%Y/%m/%d')}と一致しません")
                        except ValueError as e:
                            print(f"    日付パースエラー '{date_str}': {str(e)}")
                            continue

        print(f"\n    × 対象の日付が見つかりません")
        return False

    def _parse_date(self, date_str: str) -> datetime:
        # 全角括弧を除去
        date_str = date_str.replace('【', '').replace('】', '')
        date_str = date_str.replace('［', '').replace('］', '')
        date_str = date_str.replace('「', '').replace('」', '')
        
        # 月日形式（MM月DD日）のチェック
        if '月' in date_str and '日' in date_str:
            try:
                month = int(date_str.split('月')[0])
                day = int(date_str.split('月')[1].split('日')[0])
                year = self.target_date.year
                return datetime(year, month, day)
            except (ValueError, IndexError):
                pass  # 他の形式を試す

        # スラッシュとハイフンの両方に対応
        separators = ['/', '-']
        parts = None
        
        for sep in separators:
            if sep in date_str:
                parts = date_str.split(sep)
                break
        
        if not parts:
            raise ValueError(f"Invalid date format: {date_str}")

        parts = [p.strip() for p in parts]  # 空白を削除
            
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
            month = int(parts[0])
            day = int(parts[1])
            
        # 日付の妥当性チェック
        if not (1 <= month <= 12 and 1 <= day <= 31):
            raise ValueError(f"Invalid date values: month={month}, day={day}")
            
        try:
            return datetime(year, month, day)
        except ValueError:
            raise ValueError(f"Invalid date combination: year={year}, month={month}, day={day}")