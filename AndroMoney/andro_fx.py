"""
FX rate retrieval using Yahoo Finance.

Fetches SGD-based exchange rates (SGD/JPY, SGD/HKD, SGD/THB) for a given
date range so that multi-currency amounts can be normalised to SGD.
"""
import yfinance as yfin
import time


def get_exchange_rate(pair, start, end):
    """Download OHLCV data for a currency pair from Yahoo Finance.

    Args:
        pair:  Currency pair string without suffix, e.g. 'SGDJPY'.
        start: Period start date as 'YYYY-MM-DD'.
        end:   Period end   date as 'YYYY-MM-DD'.

    Returns:
        DataFrame with columns [Open, High, Low, Close, …] indexed by date.
    """
    selected = f'{pair}=X'
    df3 = yfin.download(selected, start, end)
    print(f'{selected} : Complete Getting Data')
    return df3


def return_fx(start, end):
    """Fetch closing SGD exchange rates for JPY, HKD, and THB.

    Args:
        start: Period start date as 'YYYY-MM-DD'.
        end:   Period end   date as 'YYYY-MM-DD'.

    Returns:
        Tuple (sgd_jpy, sgd_hkd, sgd_thb) of closing rates on the first
        available trading day in the range. Returns None on failure.
    """
    try:
        pairs = ['SGDJPY', 'SGDHKD', 'SGDTHB']
        dat_jpy = get_exchange_rate(pairs[0], start, end)
        time.sleep(2)
        dat_hkd = get_exchange_rate(pairs[1], start, end)
        time.sleep(2)
        dat_thb = get_exchange_rate(pairs[2], start, end)
        fx = (dat_jpy.iloc[0,3], dat_hkd.iloc[0,3],dat_thb.iloc[0,3])
        return fx
    except Exception as e:
        print(e)

