# AndroMoney Project 2

A Python tool that processes AndroMoney expense data and generates a summarised Excel report, with automatic currency conversion (JPY, HKD → SGD) using live exchange rates.

## Features

- Reads AndroMoney CSV export
- Pivots spending data by category and currency
- Fetches live FX rates (SGD/JPY, SGD/HKD) via Yahoo Finance
- Outputs a formatted Excel report

## Requirements

- Python 3.x
- pandas
- numpy
- openpyxl
- yfinance

Install dependencies:

```bash
pip install pandas numpy openpyxl yfinance
```

## Usage

```bash
# Run with a date range (YYYYMMDD format)
python andro_main.py 20251101 20251130

# Or set the default dates directly in andro_main.py
```

## Project Structure

```
andro_main.py          # Entry point
AndroMoney/
├── andro_control.py   # Orchestrates the pipeline
├── andro_data.py      # Data processing and FX conversion
├── andro_fx.py        # Fetches exchange rates via yfinance
├── andro_writer.py    # Writes output to Excel
└── settings.py        # Configuration (file paths, etc.)
```
