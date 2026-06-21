"""
Entry point for the AndroMoney expense report pipeline.

Usage:
    python andro_main.py <start_date> <end_date>

    start_date / end_date : 8-digit strings in YYYYMMDD format (e.g. 20251101).
    If omitted, defaults to 20251101–20251130.

The script reads AndroMoney transaction data, builds a category pivot table
with multi-currency FX conversion, and writes the result to the configured
output Excel file (see AndroMoney/settings.py).
"""
from AndroMoney import andro_control
import sys


try:
    args = sys.argv
    if args[1].isdigit():
        if args[2].isdigit():
            start_date = args[1]
            end_date = args[2]
except:
    start_date = "20251101"
    end_date = "20251130"


def func(start_date, end_date):
    """Run the full AndroMoney pipeline for the given date range.

    Args:
        start_date: Period start in YYYYMMDD format (e.g. '20251101').
        end_date:   Period end   in YYYYMMDD format (e.g. '20251130').
    """

    andro_control.start_andro(start_date, end_date)


if __name__ == '__main__':
    func(start_date, end_date)