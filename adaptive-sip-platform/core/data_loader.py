"""
core/data_loader.py
Data Engine (Phase 2): downloads historical OHLCV data.

Priority: Yahoo Finance -> NSE -> AMFI -> Stooq -> Alpha Vantage
Currently implemented: Yahoo Finance (via yfinance) + local CSV cache/fallback.
NOTE: requires internet access. If offline, use load_from_csv() or
      generate_synthetic() for testing/demo purposes.
"""

from __future__ import annotations
import os
import pandas as pd
import numpy as np


def download_yahoo(ticker: str, start: str, end: str, cache_dir: str = "data/cache") -> pd.DataFrame:
    """Download data from Yahoo Finance. Requires internet + yfinance installed."""
    import yfinance as yf  # imported lazily so the rest of the platform
                            # works even if yfinance/network isn't available
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"{ticker.replace('/', '_')}.csv")

    df = yf.download(ticker, start=start, end=end, progress=False)
    df = df.reset_index()
    df.columns = [c if isinstance(c, str) else c[0] for c in df.columns]
    df.to_csv(cache_file, index=False)
    return df


def load_from_csv(path: str) -> pd.DataFrame:
    """Load OHLCV data from a local CSV file. Expects a 'Date' and 'Close' column."""
    df = pd.read_csv(path, parse_dates=["Date"])
    return df


def generate_synthetic(start: str, end: str, freq: str = "MS",
                        start_price: float = 100.0, seed: int = 42) -> pd.DataFrame:
    """
    Generate a synthetic monthly price series for demo/testing when no
    internet access is available. Produces a realistic bull -> correction ->
    recovery -> new-high cycle so the Adaptive SIP logic can be demonstrated
    end-to-end.
    """
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start=start, end=end, freq=freq)
    n = len(dates)

    # Piece together a cycle: uptrend, drawdown, recovery, new highs, repeat
    prices = [start_price]
    trend_phases = ["up"] * 10 + ["down"] * 8 + ["up"] * 6 + ["down"] * 5 + ["up"] * 12
    phase_cycle = (trend_phases * (n // len(trend_phases) + 1))[:n]

    for i in range(1, n):
        phase = phase_cycle[i]
        drift = 0.012 if phase == "up" else -0.018
        noise = rng.normal(0, 0.03)
        new_price = prices[-1] * (1 + drift + noise)
        prices.append(max(new_price, 1.0))

    df = pd.DataFrame({"Date": dates, "Close": prices})
    df["Open"] = df["Close"] * (1 - rng.uniform(0, 0.01, n))
    df["High"] = df[["Open", "Close"]].max(axis=1) * (1 + rng.uniform(0, 0.01, n))
    df["Low"] = df[["Open", "Close"]].min(axis=1) * (1 - rng.uniform(0, 0.01, n))
    df["Adj Close"] = df["Close"]
    df["Volume"] = rng.integers(100000, 5000000, n)
    return df


def resample_monthly(df: pd.DataFrame, date_col: str = "Date",
                      price_col: str = "Close") -> pd.DataFrame:
    """Resample a daily OHLCV dataframe down to one price-per-month (month start)."""
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.set_index(date_col)
    monthly = df[price_col].resample("MS").first().dropna().reset_index()
    monthly.columns = ["Date", "Price"]
    return monthly
