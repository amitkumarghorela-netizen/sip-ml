"""
core/backtest.py
Backtesting Engine (Phase 5): loops through monthly prices, runs the
strategy engine, updates the portfolio, and records the full transaction
history required by the project's "Required Report Columns" spec.
"""

from __future__ import annotations
import pandas as pd
from core.strategy_engine import build_strategy, build_strategy_from_dict
from core.portfolio import PortfolioState
from core import metrics as metrics_engine


def run_backtest(price_df: pd.DataFrame, strategy_yaml_path: str, asset_name: str = "ASSET") -> dict:
    """
    price_df: DataFrame with columns ['Date', 'Price'] (one row per period)
    strategy_yaml_path: path to a strategy definition (see /strategies)

    Returns dict with:
        'transactions' -> list of row dicts (Required Report Columns)
        'summary'      -> metrics summary dict
        'strategy_name'-> str
    """
    engine, strategy_name = build_strategy(strategy_yaml_path)
    return _run_with_engine(price_df, engine, strategy_name, asset_name)


def run_backtest_with_config(price_df: pd.DataFrame, strategy_cfg: dict, asset_name: str = "ASSET") -> dict:
    """Same as run_backtest but takes an in-memory strategy config dict
    (see core.strategy_engine.build_strategy_from_dict) -- used by the
    grid-search optimizer to avoid writing a YAML file per combination."""
    engine, strategy_name = build_strategy_from_dict(strategy_cfg)
    return _run_with_engine(price_df, engine, strategy_name, asset_name)


def _run_with_engine(price_df: pd.DataFrame, engine, strategy_name: str, asset_name: str = "ASSET") -> dict:
    portfolio = PortfolioState()

    transactions = []

    for _, row in price_df.iterrows():
        date = row["Date"]
        price = float(row["Price"])

        result = engine.on_month(price)
        investment = result["Investment"]

        units = portfolio.buy(investment, price)

        txn = {
            "Date": date,
            "Asset": asset_name,
            "Price": result["Price"],
            "High Water Mark": result["High Water Mark"],
            "Drawdown %": result["Drawdown %"],
            "Drawdown Slabs": result["Drawdown Slabs"],
            "Market State": result["Market State"],
            "Previous SIP": result["Previous SIP"],
            "Current SIP": result["Current SIP"],
            "Reduction Amount": result["Reduction Amount"],
            "Add-on Amount": result["Add-on Amount"],
            "Investment": investment,
            "Units Purchased": round(units, 6),
            "Total Units": round(portfolio.total_units, 6),
            "Total Investment": round(portfolio.total_investment, 2),
            "Average Cost": round(portfolio.average_cost, 4),
            "Portfolio Value": round(portfolio.portfolio_value(price), 2),
            "Profit/Loss": round(portfolio.profit_loss(price), 2),
            "Reason": result["Reason"],
        }
        transactions.append(txn)

    engine.finish()

    final_price = float(price_df.iloc[-1]["Price"])
    summary = metrics_engine.summarize(transactions, final_price)

    return {
        "strategy_name": strategy_name,
        "transactions": transactions,
        "summary": summary,
    }


def compare_strategies(price_df: pd.DataFrame, strategy_paths: dict, asset_name: str = "ASSET") -> dict:
    """
    strategy_paths: dict like {'traditional': 'strategies/traditional_sip.yaml',
                                'adaptive':    'strategies/adaptive_sip_v1_1.yaml'}
    Returns dict of results keyed the same way, plus a 'comparison' summary.
    """
    results = {}
    for key, path in strategy_paths.items():
        results[key] = run_backtest(price_df, path, asset_name=asset_name)

    comparison_rows = []
    for key, res in results.items():
        s = res["summary"]
        comparison_rows.append({
            "Strategy": res["strategy_name"],
            "XIRR %": s["XIRR %"],
            "CAGR %": s["CAGR %"],
            "Total Investment": s["Total Investment"],
            "Portfolio Value": s["Portfolio Value"],
            "Profit/Loss": s["Profit/Loss"],
            "Profit %": s["Profit %"],
            "Average Cost": s["Average Cost"],
            "Max Drawdown %": s["Max Drawdown %"],
        })

    comparison_df = pd.DataFrame(comparison_rows)
    if not comparison_df.empty:
        best_idx = comparison_df["XIRR %"].idxmax()
        comparison_df["Winner"] = ""
        comparison_df.loc[best_idx, "Winner"] = "BEST"

    return {"results": results, "comparison": comparison_df}
