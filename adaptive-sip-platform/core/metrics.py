"""
core/metrics.py
Metrics Engine: XIRR, CAGR, Max Drawdown, Volatility, Sharpe, etc.
"""

from __future__ import annotations
from datetime import datetime
from typing import List, Tuple
import numpy as np


def xirr(cashflows: List[Tuple[datetime, float]], guess: float = 0.1) -> float:
    """
    Compute XIRR given a list of (date, cashflow) tuples.
    Investments are negative cashflows, final redemption is positive.
    Uses Newton-Raphson with a bisection fallback for robustness.
    """
    if not cashflows:
        return 0.0

    t0 = cashflows[0][0]
    years = np.array([(d - t0).days / 365.0 for d, _ in cashflows])
    amounts = np.array([cf for _, cf in cashflows])

    def npv(rate):
        return np.sum(amounts / (1.0 + rate) ** years)

    def dnpv(rate):
        return np.sum(-years * amounts / (1.0 + rate) ** (years + 1))

    rate = guess
    for _ in range(100):
        f = npv(rate)
        fprime = dnpv(rate)
        if abs(fprime) < 1e-12:
            break
        new_rate = rate - f / fprime
        if not np.isfinite(new_rate):
            break
        if abs(new_rate - rate) < 1e-8:
            rate = new_rate
            break
        rate = new_rate

    # sanity fallback: bisection search between -0.99 and 10
    if not np.isfinite(rate) or rate <= -1:
        lo, hi = -0.99, 10.0
        for _ in range(200):
            mid = (lo + hi) / 2
            if npv(lo) * npv(mid) <= 0:
                hi = mid
            else:
                lo = mid
        rate = (lo + hi) / 2

    return rate * 100.0  # as %


def cagr(begin_value: float, end_value: float, years: float) -> float:
    if begin_value <= 0 or years <= 0:
        return 0.0
    return ((end_value / begin_value) ** (1 / years) - 1) * 100.0


def max_drawdown(prices: List[float]) -> float:
    peak = -np.inf
    max_dd = 0.0
    for p in prices:
        peak = max(peak, p)
        dd = (peak - p) / peak * 100.0 if peak > 0 else 0.0
        max_dd = max(max_dd, dd)
    return max_dd


def volatility(returns: List[float], annualize_factor: int = 12) -> float:
    if len(returns) < 2:
        return 0.0
    return float(np.std(returns, ddof=1) * np.sqrt(annualize_factor) * 100.0)


def sharpe_ratio(returns: List[float], risk_free_annual: float = 6.0,
                  annualize_factor: int = 12) -> float:
    if len(returns) < 2:
        return 0.0
    rf_monthly = risk_free_annual / 100.0 / annualize_factor
    excess = np.array(returns) - rf_monthly
    if np.std(excess, ddof=1) == 0:
        return 0.0
    return float(np.mean(excess) / np.std(excess, ddof=1) * np.sqrt(annualize_factor))


def sortino_ratio(returns: List[float], risk_free_annual: float = 6.0,
                   annualize_factor: int = 12) -> float:
    if len(returns) < 2:
        return 0.0
    rf_monthly = risk_free_annual / 100.0 / annualize_factor
    excess = np.array(returns) - rf_monthly
    downside = excess[excess < 0]
    if len(downside) == 0 or np.std(downside, ddof=1) == 0:
        return 0.0
    return float(np.mean(excess) / np.std(downside, ddof=1) * np.sqrt(annualize_factor))


def calmar_ratio(cagr_pct: float, max_dd_pct: float) -> float:
    if max_dd_pct == 0:
        return 0.0
    return cagr_pct / max_dd_pct


def summarize(transactions: list, final_price: float) -> dict:
    """
    transactions: list of dicts each with keys 'Date' (datetime), 'Investment',
                  'Price', 'Units Purchased'
    """
    total_units = sum(t["Units Purchased"] for t in transactions)
    total_investment = sum(t["Investment"] for t in transactions)
    portfolio_value = total_units * final_price
    avg_cost = total_investment / total_units if total_units else 0.0

    cashflows = [(t["Date"], -t["Investment"]) for t in transactions]
    cashflows.append((transactions[-1]["Date"], portfolio_value))
    irr = xirr(cashflows)

    prices = [t["Price"] for t in transactions]
    mdd = max_drawdown(prices)

    years = (transactions[-1]["Date"] - transactions[0]["Date"]).days / 365.0
    cagr_val = cagr(total_investment, portfolio_value, years) if years > 0 else 0.0

    sips = [t["Investment"] for t in transactions]

    return {
        "Total Units": round(total_units, 4),
        "Total Investment": round(total_investment, 2),
        "Average Cost": round(avg_cost, 4),
        "Portfolio Value": round(portfolio_value, 2),
        "Profit/Loss": round(portfolio_value - total_investment, 2),
        "Profit %": round((portfolio_value - total_investment) / total_investment * 100, 2) if total_investment else 0.0,
        "XIRR %": round(irr, 2),
        "CAGR %": round(cagr_val, 2),
        "Max Drawdown %": round(mdd, 2),
        "Average SIP": round(np.mean(sips), 2),
        "Maximum SIP": round(np.max(sips), 2),
        "Minimum SIP": round(np.min(sips), 2),
    }
