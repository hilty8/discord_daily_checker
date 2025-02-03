from datetime import datetime
from src.sheets_handler import SheetsHandler

def test_write():
    handler = SheetsHandler()
    
    # 1月から12月まで各月のシートにテストデータを書き込み
    for month in range(1, 13):
        test_date = datetime(2025, month, 15)  # 各月15日にテスト
        print(f"{month}月シートへの書き込みテスト...")
        handler.write_check_result(
            date=test_date,
            user_id="1195348117176979529",  # いのさん
            report_status=True,
            declaration_status=True
        )
        print(f"{month}月シートへの書き込み完了")

if __name__ == "__main__":
    test_write()