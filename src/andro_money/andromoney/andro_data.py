"""
Data loading and transformation layer for AndroMoney transaction exports.

Provides two classes:
    AndroData       — base class handling source resolution (local or Google Drive).
    AndroDataMoney  — subclass that reads, filters, pivots, and applies FX
                      conversion to produce a SGD-normalised expense summary.
"""
import pandas as pd
import numpy as np
from . import andro_fx
from . import settings
import datetime


class AndroData(object):
    """Base class for AndroMoney data sources.

    Attributes:
        xlsx_file:  Local path fallback used when USE_GOOGLE_DRIVE is False.
        start_date: Filter start in YYYYMMDD format.
        end_date:   Filter end   in YYYYMMDD format.
    """

    def __init__(self, xlsx_file=None, start_date=None, end_date=None):
        self.xlsx_file = xlsx_file or settings.XLSX_FILE_PATH
        self.start_date = start_date
        self.end_date = end_date

    def get_source(self):
        """Return (source, format) for the pipeline data source.

        Returns:
            (io.StringIO, 'csv') when USE_GOOGLE_DRIVE is True —
                downloads AndroMoney.csv from Google Drive into memory.
            (str path, 'excel') when USE_GOOGLE_DRIVE is False —
                uses the local xlsx path from settings.
        """
        if settings.USE_GOOGLE_DRIVE:
            from . import andro_drive as _drive
            from googleapiclient.discovery import build
            creds = _drive.authenticate()
            service = build("drive", "v3", credentials=creds)
            file_id = _drive.search_file(service, settings.DRIVE_FILENAME)
            sio = _drive.download_csv(service, file_id)
            return sio, "csv"
        return self.xlsx_file, "excel"


class AndroDataMoney(AndroData):
    """Reads and transforms AndroMoney transaction data."""

    def andro_rawdata_get(self):
        """Load the full transaction history from the configured source.

        Drops the sentinel row (Date == 10100101) and parses the Date column
        to datetime.

        Caches the result on the instance so that multiple callers within the
        same pipeline run do not trigger repeated OAuth + Drive download
        round-trips.

        Returns:
            DataFrame with all transactions, Date as datetime.
        """
        if hasattr(self, '_rawdata'):
            return self._rawdata
        source, fmt = self.get_source()
        if fmt == "csv":
            df = pd.read_csv(source, index_col=0, header=1)
        else:
            df = pd.read_excel(source, index_col=0, header=1)
        drop_index = df.index[df["Date"] == 10100101]
        df = df.drop(drop_index)
        df["Date"] = pd.to_datetime(df["Date"].astype(str))
        self._rawdata = df
        return self._rawdata

    def andro_data_get(self):
        """Filter raw transactions to the configured date range.

        Returns:
            DataFrame containing only rows where start_date <= Date <= end_date.
        """
        df = self.andro_rawdata_get()
        df1 = df.query("@self.end_date>=Date>=@self.start_date")
        return df1

    def andro_pivot_get(self):
        """Build a category × currency pivot table for the date range.

        Rows are the predefined Japanese expense categories (plus Business
        Expense). Columns are currency codes (e.g. SGD, JPY, HKD).
        Missing category/currency combinations are filled with 0.

        Returns:
            DataFrame pivot with categories as index and currencies as columns.
        """
        lst = ['住居費', '食料品', '光熱費', '通信費', '保険', '年金', '日常生活', '医療関連', '教育関連', '交通関係',
               'アパレル', '人間関係', 'レジャー・娯楽', '電子製品・モバイル', '自動車・バイク', '奨学金', '仕送り', 'その他', 'Business Expense', '資金運用']
        pivot_andromoney = pd.pivot_table(self.andro_data_get(), index=['Category'], columns='Currency', values='Amount',
                                          aggfunc=np.sum, fill_value=0)
        return pivot_andromoney.reindex(lst, axis='index', fill_value=0)

    def andro_pivot_get_fx(self):
        """Return the pivot table with a SGD-normalised 'sum' column.

        Fetches SGD/JPY and SGD/HKD closing rates via Yahoo Finance for the
        period, then converts each currency column to SGD and sums them.

        Returns:
            DataFrame pivot with an added 'sum' column (SGD equivalent),
            values rounded to 2 decimal places.
        """
        std = self.start_date[:4] + '-' + self.start_date[4:6] + '-' + self.start_date[6:]
        edd = self.end_date[:4] + '-' + self.end_date[4:6] + '-' + self.end_date[6:]
        pivot_andromoney = self.andro_pivot_get()
        fx = andro_fx.return_fx(std, edd)

        has_jpy = 'JPY' in pivot_andromoney.columns
        has_hkd = 'HKD' in pivot_andromoney.columns
        sgd = pivot_andromoney.get('SGD', 0) #0 if no SGD transactions

        if has_jpy and has_hkd:
            pivot_andromoney['sum'] = pivot_andromoney['HKD'] / fx[1] + pivot_andromoney['JPY'] / fx[0] + sgd
        elif has_jpy:
            pivot_andromoney['sum'] = pivot_andromoney['JPY'] / fx[0] + sgd
        elif has_hkd:
            pivot_andromoney['sum'] = pivot_andromoney['HKD'] / fx[1] + sgd
        else:
            pivot_andromoney['sum'] = sgd

        pivot_andromoney = pivot_andromoney.round(2)
        print(pivot_andromoney)
        return pivot_andromoney
