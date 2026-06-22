# AndroMoney Project 2

A Python tool that processes AndroMoney expense data and generates a summarised Excel report, with automatic currency conversion (JPY, HKD → SGD) using live exchange rates.

## Features

- Reads AndroMoney data from a Google Spreadsheet on Google Drive
- Pivots spending data by category and currency
- Fetches live FX rates (SGD/JPY, SGD/HKD) via Yahoo Finance
- Outputs a formatted Excel report

## Requirements

- Python 3.x
- pandas
- numpy
- openpyxl
- yfinance
- google-auth-oauthlib
- google-api-python-client

Install dependencies:

```bash
pip install pandas numpy openpyxl yfinance google-auth-oauthlib google-api-python-client
```

## Google Drive Setup (first time only)

1. Go to [Google Cloud Console](https://console.cloud.google.com) and create a project
2. Enable the **Google Drive API** (APIs & Services → Library)
3. Create **OAuth 2.0 credentials** (APIs & Services → Credentials → Create Credentials → OAuth client ID → Desktop app)
4. Download the JSON file and save it as `credentials.json` in the project root
5. Add your Google account as a test user (APIs & Services → OAuth consent screen → Test users)
6. Run the pipeline once — a browser tab opens for consent, then `token.json` is saved automatically

> `credentials.json` and `token.json` are gitignored and will never be committed.

## Usage

```bash
# Run with a date range (YYYYMMDD format)
python andro_money.py 20251201 20251231

# Or set the default dates directly in andro_money.py
```

## Configuration

Edit `andromoney/settings.py` to adjust:

```python
USE_GOOGLE_DRIVE = True        # Set False to read from local xlsx instead
DRIVE_FILENAME = "AndroMoney"  # Name of the Google Spreadsheet on Drive
CREDENTIALS_PATH = "credentials.json"
TOKEN_PATH = "token.json"
XLSX_FILE_PATH = "/path/to/AndroMoney.xlsx"   # Local fallback (USE_GOOGLE_DRIVE=False)
XLSX2_FILE_PATH = "/path/to/credit-card.xlsx" # Secondary output workbook
```

## Project Structure

```
andro_money.py         # Entry point — run() launches the pipeline
credentials.json       # OAuth client secret (not committed)
token.json             # Cached OAuth token (not committed)
andromoney/
├── andro_control.py   # Orchestrates the pipeline
├── andro_data.py      # Data loading (Drive or local) and transformation
├── andro_drive.py     # Google Drive auth, file search, CSV export
├── andro_fx.py        # Fetches exchange rates via yfinance
├── andro_writer.py    # Writes output to Excel (andro_pivot_writer, andro_excel_writer)
└── settings.py        # Configuration (file paths, Drive settings)
tests/
├── test_andro_drive.py  # Unit tests for Drive module
└── test_andro_data.py   # Unit tests for data source layer
```
