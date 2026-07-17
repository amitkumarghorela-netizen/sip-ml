"""
database/db_manager.py
Phase: DuckDB persistence layer.

Caches downloaded price series (so repeated batch/grid-search runs don't
re-hit Yahoo Finance) and stores backtest result summaries so batch runs
and the dashboard can query history without re-running backtests.
"""

from __future__ import annotations
import os
from datetime import datetime
from typing import Optional
import pandas as pd
import duckdb


DEFAULT_DB_PATH = "database/asrp.duckdb"


def get_connection(db_path: str = DEFAULT_DB_PATH) -> duckdb.DuckDBPyConnection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    con = duckdb.connect(db_path)
    _init_schema(con)
    return con


def _init_schema(con: duckdb.DuckDBPyConnection):
    con.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            ticker VARCHAR,
            date TIMESTAMP,
            price DOUBLE,
            PRIMARY KEY (ticker, date)
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS price_meta (
            ticker VARCHAR PRIMARY KEY,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            last_updated TIMESTAMP
        )
    """)
    con.execute("""
        CREATE SEQUENCE IF NOT EXISTS backtest_results_id_seq START 1
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS backtest_results (
            id BIGINT PRIMARY KEY DEFAULT nextval('backtest_results_id_seq'),
            run_date TIMESTAMP,
            ticker VARCHAR,
            asset_name VARCHAR,
            strategy_name VARCHAR,
            params_json VARCHAR,
            xirr_pct DOUBLE,
            cagr_pct DOUBLE,
            total_investment DOUBLE,
            portfolio_value DOUBLE,
            profit_loss DOUBLE,
            profit_pct DOUBLE,
            average_cost DOUBLE,
            max_drawdown_pct DOUBLE,
            batch_tag VARCHAR
        )
    """)


# --------------------------------------------------------------------------
# Price cache
# --------------------------------------------------------------------------

def get_cached_prices(ticker: str, start: str, end: str,
                       db_path: str = DEFAULT_DB_PATH) -> Optional[pd.DataFrame]:
    """Return cached ['Date', 'Price'] rows for ticker within [start, end] if
    the cache fully covers that range, else None (caller should download)."""
    con = get_connection(db_path)
    meta = con.execute(
        "SELECT start_date, end_date FROM price_meta WHERE ticker = ?", [ticker]
    ).fetchone()
    con.close()
    if meta is None:
        return None
    cached_start, cached_end = meta
    if pd.Timestamp(cached_start) > pd.Timestamp(start) or pd.Timestamp(cached_end) < pd.Timestamp(end):
        return None

    con = get_connection(db_path)
    df = con.execute(
        "SELECT date AS Date, price AS Price FROM prices "
        "WHERE ticker = ? AND date BETWEEN ? AND ? ORDER BY date",
        [ticker, start, end],
    ).fetchdf()
    con.close()
    if df.empty:
        return None
    return df


def store_prices(ticker: str, price_df: pd.DataFrame, db_path: str = DEFAULT_DB_PATH):
    """price_df must have ['Date', 'Price'] columns."""
    con = get_connection(db_path)
    rows = [(ticker, pd.Timestamp(d), float(p)) for d, p in zip(price_df["Date"], price_df["Price"])]
    con.executemany(
        "INSERT OR REPLACE INTO prices (ticker, date, price) VALUES (?, ?, ?)", rows
    )
    start_date = price_df["Date"].min()
    end_date = price_df["Date"].max()
    con.execute(
        "INSERT OR REPLACE INTO price_meta (ticker, start_date, end_date, last_updated) "
        "VALUES (?, ?, ?, ?)",
        [ticker, pd.Timestamp(start_date), pd.Timestamp(end_date), datetime.now()],
    )
    con.close()


def list_cached_tickers(db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    con = get_connection(db_path)
    df = con.execute(
        "SELECT ticker, start_date, end_date, last_updated FROM price_meta ORDER BY ticker"
    ).fetchdf()
    con.close()
    return df


# --------------------------------------------------------------------------
# Backtest result history
# --------------------------------------------------------------------------

def save_backtest_result(ticker: str, asset_name: str, strategy_name: str,
                          summary: dict, params_json: str = "{}",
                          batch_tag: str = "", db_path: str = DEFAULT_DB_PATH):
    con = get_connection(db_path)
    con.execute("""
        INSERT INTO backtest_results (
            run_date, ticker, asset_name, strategy_name, params_json,
            xirr_pct, cagr_pct, total_investment, portfolio_value,
            profit_loss, profit_pct, average_cost, max_drawdown_pct, batch_tag
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        datetime.now(), ticker, asset_name, strategy_name, params_json,
        summary.get("XIRR %", 0.0), summary.get("CAGR %", 0.0),
        summary.get("Total Investment", 0.0), summary.get("Portfolio Value", 0.0),
        summary.get("Profit/Loss", 0.0), summary.get("Profit %", 0.0),
        summary.get("Average Cost", 0.0), summary.get("Max Drawdown %", 0.0),
        batch_tag,
    ])
    con.close()


def load_backtest_results(batch_tag: Optional[str] = None,
                           db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    con = get_connection(db_path)
    if batch_tag:
        df = con.execute(
            "SELECT * FROM backtest_results WHERE batch_tag = ? ORDER BY run_date DESC",
            [batch_tag],
        ).fetchdf()
    else:
        df = con.execute("SELECT * FROM backtest_results ORDER BY run_date DESC").fetchdf()
    con.close()
    return df
