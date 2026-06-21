"""
Excel output writers for AndroMoney pivot and raw transaction data.

Writes to two configured output files (see AndroMoney/settings.py):
    TABLE_FILE_PATH  — main pivot + raw data workbook (Sheet1 / Sheet2).
    xlsx2_file_path  — secondary credit-card history workbook (家計簿 sheet).
"""
import datetime
import pandas as pd
import openpyxl
import AndroMoney.settings

xlsx_file_path = AndroMoney.settings.TABLE_FILE_PATH
xlsx2_file_path = AndroMoney.settings.xlsx2_file_path


def andro_pivotwriter(pivot_andromoney, df):
    """Write the pivot table and raw transactions to the main output workbook.

    Args:
        pivot_andromoney: Category × currency pivot DataFrame (with 'sum' col).
        df:               Full raw transaction DataFrame.
    """
    with pd.ExcelWriter(xlsx_file_path, engine='openpyxl', mode='w+') as ew:
        pivot_andromoney.to_excel(ew, sheet_name='Sheet1', startrow=3, startcol=7)
        df.to_excel(ew, sheet_name='Sheet2')


def andro_excelwriter(pivot_andromoney, start_date=None):
    """Write pivot values into the matching month column of the 家計簿 sheet.

    Scans row 17 of the credit-card workbook to find the column whose header
    matches start_date, then writes 19 category totals into that column.

    Args:
        pivot_andromoney: Category × currency pivot DataFrame (with 'sum' col).
        start_date:       Period start as 'YYYY-MM-DD'.
    """
    # Retrieve year-date on table to identify new column
    df3 = pd.read_excel(xlsx2_file_path, sheet_name="家計簿", skiprows=16, nrows=1, header=None)
    strd = datetime.datetime.strptime(start_date, "%Y-%m-%d")

    for count, (a, b) in enumerate(df3.iteritems(), start=1):
        if b.iloc[-1] == strd:
            input_data(pivot_andromoney, count)


def input_data(pivot_andromoney, cell):
    """Write 19 rows of pivot data into a specific column of the 家計簿 sheet.

    Args:
        pivot_andromoney: Category × currency pivot DataFrame (with 'sum' col).
        cell:             1-based column index of the target month column.
    """
    wb = openpyxl.load_workbook(xlsx2_file_path)
    ws = wb["家計簿"]
    ws = [ws.cell(row=18+i, column=cell, value=pivot_andromoney.iloc[0+i, 3]) for i in range(19)]
    wb.save(xlsx2_file_path)
    wb.close()