"""
Pipeline controller that orchestrates data loading, pivot creation, and writing.
"""
from andromoney.andro_writer import andro_pivot_writer
from andromoney.andro_data import AndroDataMoney


def start_andro(start_date, end_date):
    """Run the full expense-report pipeline for the given date range.

    Loads raw transaction data, builds a currency-normalised pivot table,
    and writes both the pivot and the raw data to the output Excel file.

    Args:
        start_date: Period start in YYYYMMDD format (e.g. '20251101').
        end_date:   Period end   in YYYYMMDD format (e.g. '20251130').
    """
    try:
        am = AndroDataMoney(start_date=start_date, end_date=end_date)
        pivot_fx = am.andro_pivot_get_fx()
        df = am.andro_rawdata_get()
        andro_pivot_writer(pivot_fx, df)
        # andro_writer.andro_excelwriter(pivot_fx, start_date=start_date)
    except Exception as ex:
        print(f"{ex}")