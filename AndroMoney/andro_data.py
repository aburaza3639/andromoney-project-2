import pandas as pd
import numpy as np
import AndroMoney.andro_fx
import AndroMoney.settings
import datetime


class AndroData(object):

    def __init__(self, xlsx_file=None, start_date=None, end_date=None):

        if not xlsx_file:
            self.xlsx_file = self.get_xlsx_file_path()
        self.start_date = start_date
        self.end_date = end_date

    @staticmethod
    def get_xlsx_file_path():

        xlsx_file_path = AndroMoney.settings.xlsx_FILE_PATH
        return xlsx_file_path


class AndroDataMoney(AndroData):

    def andro_rawdata_get(self):
        df = pd.read_excel(self.xlsx_file, index_col=0, header=1)
        # 条件にマッチしたIndexを取得
        drop_index = df.index[df['Date'] == 10100101]
        # 条件にマッチしたIndexを削除
        df = df.drop(drop_index)
        df['Date'] = pd.to_datetime(df['Date'].astype(str))
        return df

    def andro_data_get(self):
        df = self.andro_rawdata_get()
        df1 = df.query("@self.end_date>=Date>=@self.start_date")
        return df1

    def andro_pivot_get(self):
        lst = ['住居費', '食料品', '光熱費', '通信費', '保険', '年金', '日常生活', '医療関連', '教育関連', '交通関係',
               'アパレル', '人間関係', 'レジャー・娯楽', '電子製品・モバイル', '自動車・バイク', '奨学金', '仕送り', 'その他', 'Business Expense']
        pivot_andromoney = pd.pivot_table(self.andro_data_get(), index=['Category'], columns='Currency', values='Amount',
                                          aggfunc=np.sum, fill_value=0)
        pivot_andromoney = pivot_andromoney.reindex(lst, axis='index', fill_value=0)
        return pivot_andromoney

    def andro_pivot_get_fx(self):
        std = self.start_date[:4] + '-' + self.start_date[4:6] + '-' + self.start_date[6:]
        edd = self.end_date[:4] + '-' + self.end_date[4:6] + '-' + self.end_date[6:]
        pivot_andromoney = self.andro_pivot_get()
        fx = AndroMoney.andro_fx.return_fx(std, edd)

        has_jpy = 'JPY' in pivot_andromoney.columns
        has_hkd = 'HKD' in pivot_andromoney.columns

        if has_jpy and has_hkd:
            pivot_andromoney['sum'] = pivot_andromoney['HKD'] / fx[1] + pivot_andromoney['JPY'] / fx[0] + pivot_andromoney['SGD']
        elif has_jpy:
            pivot_andromoney['sum'] = pivot_andromoney['JPY'] / fx[0] + pivot_andromoney['SGD']
        elif has_hkd:
            pivot_andromoney['sum'] = pivot_andromoney['HKD'] / fx[1] + pivot_andromoney['SGD']
        else:
            pivot_andromoney['sum'] = pivot_andromoney['SGD']

        pivot_andromoney = pivot_andromoney.round(2)
        print(pivot_andromoney)
        return pivot_andromoney
