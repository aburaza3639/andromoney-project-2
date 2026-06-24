"""
Entry point for the AndroMoney expense report pipeline.

Usage:
    python andro_money.py <start_date> <end_date>

    start_date / end_date : 8-digit strings in YYYYMMDD format (e.g. 20251101).
    If omitted, defaults to 20251101–20251130.

The script reads AndroMoney transaction data, builds a category pivot table
with multi-currency FX conversion, and writes the result to the configured
output Excel file (see andromoney/settings.py).
"""
from .andromoney import andro_control
import sys


def run(start_date, end_date):
    """Run the full AndroMoney pipeline for the given date range.

    Args:
        start_date: Period start in YYYYMMDD format (e.g. '20251201').
        end_date:   Period end   in YYYYMMDD format (e.g. '20251231').
    """
    andro_control.start_andro(start_date, end_date)


if __name__ == '__main__':
    try:
        
        args = sys.argv

        if len(args) == 1:
            start_date = "20251201"
            end_date = "20251231"                        
        elif len(args) ==3:
            if not args[1].isdigit() or not args[2].isdigit():
                raise ValueError("Invalid date format. Please use YYYYMMDD format.")
            start_date = args[1]
            end_date = args[2]
        else:
            raise ValueError("Invalid number of arguments. Usage: python andro_money.py <start_date> <end_date>")
        run(start_date, end_date)
        
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
