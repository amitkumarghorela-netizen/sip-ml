"""
core/portfolio.py
Portfolio Engine: tracks cash invested, units purchased, average cost,
portfolio value and profit/loss over the course of a backtest.
"""

from dataclasses import dataclass


@dataclass
class PortfolioState:
    total_units: float = 0.0
    total_investment: float = 0.0

    def buy(self, investment_amount: float, price: float) -> float:
        """Invest `investment_amount` at `price`, return units purchased."""
        units = investment_amount / price if price > 0 else 0.0
        self.total_units += units
        self.total_investment += investment_amount
        return units

    @property
    def average_cost(self) -> float:
        if self.total_units == 0:
            return 0.0
        return self.total_investment / self.total_units

    def portfolio_value(self, current_price: float) -> float:
        return self.total_units * current_price

    def profit_loss(self, current_price: float) -> float:
        return self.portfolio_value(current_price) - self.total_investment

    def profit_pct(self, current_price: float) -> float:
        if self.total_investment == 0:
            return 0.0
        return self.profit_loss(current_price) / self.total_investment * 100.0
