"""
core/batch_runner.py
Batch Backtesting Engine: runs one strategy across N tickers (e.g. Nifty50,
ETF lists) automatically, using the DuckDB price cache to avoid
re-downloading data that's already been fetched.
"""

from __future__ import annotations
from typing import Callable, Optional
import pandas as pd

from core.data_loader import download_yahoo, resample_monthly
from core.backtest import run_backtest
from database import db_manager


def fetch_price_series(ticker: str, start: str, end: str,
                        db_path: str = db_manager.DEFAULT_DB_PATH,
                        use_cache: bool = True) -> pd.DataFrame:
    """Returns ['Date', 'Price'] monthly series for `ticker`, transparently
    using the DuckDB cache before falling back to a Yahoo Finance download."""
    if use_cache:
        cached = db_manager.get_cached_prices(ticker, start, end, db_path=db_path)
        if cached is not None and len(cached) > 0:
            return cached

    raw = download_yahoo(ticker, start, end)
    price_df = resample_monthly(raw)

    if use_cache and not price_df.empty:
        db_manager.store_prices(ticker, price_df, db_path=db_path)

    return price_df


def run_batch(strategy_yaml_path: str, tickers: list[str], start: str, end: str,
              batch_tag: str = "", use_cache: bool = True,
              db_path: str = db_manager.DEFAULT_DB_PATH,
              save_to_db: bool = True,
              progress_cb: Optional[Callable[[int, int, str], None]] = None) -> dict:
    """
    Runs `strategy_yaml_path` across every ticker in `tickers`.

    Returns:
        {
          'results': {ticker: backtest_result_dict, ...},
          'errors':  {ticker: error_message, ...},
          'leaderboard': pd.DataFrame (see core.comparator.build_leaderboard)
        }
    """
    from core.comparator import build_leaderboard  # local import: avoid cycle

    results = {}
    errors = {}
    total = len(tickers)

    for i, ticker in enumerate(tickers, start=1):
        if progress_cb:
            progress_cb(i, total, ticker)
        try:
            price_df = fetch_price_series(ticker, start, end, db_path=db_path, use_cache=use_cache)
            if price_df.empty or len(price_df) < 3:
                errors[ticker] = "Not enough price history returned."
                continue

            result = run_backtest(price_df, strategy_yaml_path, asset_name=ticker)
            results[ticker] = result

            if save_to_db:
                db_manager.save_backtest_result(
                    ticker=ticker,
                    asset_name=ticker,
                    strategy_name=result["strategy_name"],
                    summary=result["summary"],
                    batch_tag=batch_tag,
                    db_path=db_path,
                )
        except Exception as exc:  # noqa: BLE001 -- batch must keep going on per-ticker failure
            errors[ticker] = str(exc)

    leaderboard = build_leaderboard(results)

    return {"results": results, "errors": errors, "leaderboard": leaderboard}
