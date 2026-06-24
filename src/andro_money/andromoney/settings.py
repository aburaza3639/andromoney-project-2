import os

XLSX_FILE_PATH: str = "/Users/aburaza3639/Documents/プライベート/資産/AndroMoney.xlsx"
TABLE_FILE_PATH: str = "/Users/aburaza3639/Documents/プライベート/資産/AndroMoney_Pivot.xlsx"
XLSX2_FILE_PATH: str = "/Users/aburaza3639/Documents/プライベート/資産/クレジットカード履歴.xlsx"

# Google Drive integration
USE_GOOGLE_DRIVE: bool = True
DRIVE_FILENAME: str = "AndroMoney"

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_PATH: str = os.path.join(_HERE, "credentials.json")
TOKEN_PATH: str = os.path.join(_HERE, "token.json")