import numpy as np
import pandas as pd
import yfinance as yf

sector_etfs = ["XLK", "XLE", "XLF", "XLV", "XLI", "XLY", "XLP", "XLB", "XLU", "XLRE", "XLC"]

benchmarks = ["SPY", "RSP", "QQQ"]

# Use yahoo finance to get the daily closes for the sector ETFs and benchmarks
def load_prices(tickers, start="2015-01-01", end=None):
    raw = yf.download(list(tickers), start=start, end=end, auto_adjust=True, progress=False)
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
    return close.reindex(columns=[t for t in tickers if t in close.columns]).sort_index()


def daily_returns(prices):
    return prices.pct_change(fill_method=None)

# get a comparable view of the stocks
def rebased_100(prices, tickers) -> pd.DataFrame:
    out = {}
    for t in tickers:
        s = prices[t].dropna()
        out[t] = 100 * s / s.iloc[0]
    return pd.DataFrame(out)


def daily_prices(tickers, period="1d", interval="5m"):
    raw = yf.download(list(tickers), period=period, interval=interval,
                      auto_adjust=True, progress=False)
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
    return close.dropna(how="all")

# get the last days % change
def pct_change_1d(prices, ticker) -> float:
    s = prices[ticker].dropna()
    return (s.iloc[-1] / s.iloc[-2] - 1) * 100


## get volatility by ticket
def forward_realized_vol(prices, ticker="SPY", window=21) -> pd.Series:
    r = prices[ticker].pct_change(fill_method=None)
    fwd = (r.rolling(window).std() * np.sqrt(252)).shift(-window)
    return fwd


# build pairwise correlation matrix between sectors then take the mean of all entries
# accounting for diagonal all 1s
def rolling_avg_pairwise_corr(returns: pd.DataFrame, window=63) -> pd.Series:
    n = returns.shape[1]
    cmat = returns.rolling(window).corr()
    full_sum = cmat.groupby(level=0).sum().sum(axis=1)
    avg = (full_sum - n) / (n * (n - 1))
    enough = returns.notna().all(axis=1).rolling(window).sum() >= window
    return avg.where(enough.reindex(avg.index))


# create the equal weight vs cap weight ratio for the s&p trackers
def concentration_ratio(prices: pd.DataFrame) -> pd.Series:
    ratio = (prices["RSP"] / prices["SPY"]).dropna()
    return 100 * ratio / ratio.iloc[0]


# create the table for the signal tab
def signal_frame(breadth_series, benchmark_prices, benchmark="SPY", vol_window=21) -> pd.DataFrame:
    df = pd.DataFrame({
        "breadth": breadth_series,
        "fwd_vol": forward_realized_vol(benchmark_prices, benchmark, vol_window),
    })
    # prior 21-day index return
    prior_ret = benchmark_prices[benchmark].pct_change(21)
    df["mkt_up"] = prior_ret.reindex(df.index) > 0
    return df.dropna()


# create a least squares line to test correlation
def ols(x, y) -> dict:
    x = np.asarray(x, float); y = np.asarray(y, float)
    b, a = np.polyfit(x, y, 1)
    yhat = a + b * x
    r2 = 1 - np.sum((y - yhat) ** 2) / np.sum((y - y.mean()) ** 2)
    return {"slope": b, "intercept": a, "r2": r2, "n": len(x)}
