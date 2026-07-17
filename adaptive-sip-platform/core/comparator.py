"""
core/comparator.py
Comparison Engine: ranks batch-backtest results best-to-worst across a
universe of tickers, on XIRR by default (configurable metric).
"""

from __future__ import annotations
import pandas as pd


def build_leaderboard(batch_results: dict, metric: str = "XIRR %") -> pd.DataFrame:
    """
    batch_results: {ticker: backtest_result_dict} as produced by
                    core.batch_runner.run_batch()['results']
    """
    rows = []
    for ticker, res in batch_results.items():
        s = res["summary"]
        rows.append({
            "Ticker": ticker,
            "Strategy": res["strategy_name"],
            "XIRR %": s["XIRR %"],
            "CAGR %": s["CAGR %"],
            "Total Investment": s["Total Investment"],
            "Portfolio Value": s["Portfolio Value"],
            "Profit/Loss": s["Profit/Loss"],
            "Profit %": s["Profit %"],
            "Max Drawdown %": s["Max Drawdown %"],
            "Average SIP": s["Average SIP"],
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df = df.sort_values(metric, ascending=False).reset_index(drop=True)
    df.insert(0, "Rank", range(1, len(df) + 1))

    df["Tag"] = ""
    if len(df) > 0:
        df.loc[df.index[0], "Tag"] = "BEST"
        df.loc[df.index[-1], "Tag"] = "WORST"

    return df


def compare_two_batches(batch_a: dict, batch_b: dict, label_a: str = "A",
                         label_b: str = "B", metric: str = "XIRR %") -> pd.DataFrame:
    """Side-by-side comparison of the same ticker universe run under two
    different strategies/params (e.g. traditional vs adaptive batches)."""
    rows = []
    tickers = sorted(set(batch_a.keys()) | set(batch_b.keys()))
    for ticker in tickers:
        row = {"Ticker": ticker}
        a = batch_a.get(ticker)
        b = batch_b.get(ticker)
        row[f"{label_a} {metric}"] = a["summary"][metric] if a else None
        row[f"{label_b} {metric}"] = b["summary"][metric] if b else None
        if a and b:
            row["Delta"] = round(a["summary"][metric] - b["summary"][metric], 2)
            row["Winner"] = label_a if row["Delta"] > 0 else (label_b if row["Delta"] < 0 else "Tie")
        rows.append(row)
    return pd.DataFrame(rows)
