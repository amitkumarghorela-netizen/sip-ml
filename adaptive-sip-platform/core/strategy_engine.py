"""
core/strategy_engine.py

Rule-based Strategy Engine for ASRP.

Design goal (per project brief): the Adaptive SIP logic must NOT be
hardcoded in Python. Instead every strategy is described by a YAML file
(see /strategies/*.yaml) and this engine interprets those rules.

This module ships two concrete engines:
  - AdaptiveSIPEngine   -> implements the state machine described in
                           "Professional Adaptive SIP Strategy v1.1"
  - FixedSIPEngine      -> traditional monthly fixed SIP

Both engines expose the same interface so the Backtesting Engine (Phase 5)
can treat every strategy identically:

    initialize()
    on_month(price) -> dict (one row of results)
    finish()
"""

from __future__ import annotations
import math
import yaml
from dataclasses import dataclass, field
from typing import Optional


def load_strategy_config(yaml_path: str) -> dict:
    with open(yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@dataclass
class StrategyState:
    hwm: float = 0.0
    previous_sip: float = 0.0
    previous_slab: int = 0
    previous_drawdown: float = 0.0
    market_state: str = "START"


class AdaptiveSIPEngine:
    """
    Implements Professional Adaptive SIP Strategy v1.1 exactly as specified:

    BULL      : price > previous HWM  -> SIP = max(prev_SIP * reduction_factor, MIN_SIP)
    SIDEWAYS  : no new HWM, no new drawdown slab -> SIP unchanged
    BEAR      : drawdown slab increases -> SIP = BASE_SIP * (1 + slabs * step_multiplier)
    RECOVERY  : drawdown shrinking but no new HWM -> SIP held (no reduction)
    NEW HIGH  : price > previous HWM after a bear cycle -> same as BULL rule
    """

    def __init__(self, config: dict):
        cfg = config["config"]
        self.base_sip = float(cfg["base_sip"])
        self.minimum_sip = float(cfg["minimum_sip"])
        self.reduction_factor = float(cfg["reduction_factor"])
        self.drawdown_step = float(cfg["drawdown_step"])
        self.step_multiplier = float(cfg["step_multiplier"])
        self.use_max_sip = bool(cfg.get("use_max_sip", True))
        self.max_multiplier = float(cfg.get("max_multiplier", 5.0))
        self.max_sip = self.base_sip * self.max_multiplier

        self.state = StrategyState(
            hwm=0.0,
            previous_sip=self.base_sip,
            previous_slab=0,
            previous_drawdown=0.0,
            market_state="START",
        )
        self._initialized = False

    def initialize(self):
        self._initialized = True

    def _drawdown_pct(self, price: float) -> float:
        if self.state.hwm <= 0:
            return 0.0
        return (self.state.hwm - price) / self.state.hwm * 100.0

    def _slabs(self, drawdown_pct: float) -> int:
        return int(math.floor(max(drawdown_pct, 0.0) / self.drawdown_step))

    def on_month(self, price: float) -> dict:
        s = self.state

        # --- First observation: establishes initial HWM, START state ---
        if s.hwm == 0.0:
            s.hwm = price
            current_sip = self.base_sip
            market_state = "START"
            drawdown = 0.0
            slabs = 0
            reduction_amt = 0.0
            addon_amt = 0.0

            reason = "Initial investment (START state), HWM initialised."

            s.previous_sip = current_sip
            s.previous_slab = slabs
            s.previous_drawdown = drawdown
            s.market_state = market_state

            return self._row(price, s.hwm, drawdown, slabs, market_state,
                              self.base_sip, current_sip, reduction_amt,
                              addon_amt, reason)

        previous_sip = s.previous_sip
        previous_hwm = s.hwm
        new_high = price > previous_hwm

        if new_high:
            # BULL / NEW HIGH rule
            s.hwm = price
            current_sip = max(previous_sip * self.reduction_factor, self.minimum_sip)
            market_state = "BULL" if s.market_state in ("START", "BULL", "SIDEWAYS") else "NEW HIGH"
            drawdown = 0.0
            slabs = 0
            reduction_amt = max(previous_sip - current_sip, 0.0)
            addon_amt = 0.0
            reason = (f"Price made a new high ({price} > HWM {previous_hwm}). "
                      f"SIP reduced: {previous_sip:.2f} -> {current_sip:.2f}.")

        else:
            drawdown = self._drawdown_pct(price)
            slabs = self._slabs(drawdown)

            if slabs > s.previous_slab:
                # BEAR rule -- new deeper drawdown slab reached
                current_sip = self.base_sip * (1 + slabs * self.step_multiplier)
                if self.use_max_sip:
                    current_sip = min(current_sip, self.max_sip)
                market_state = "BEAR"
                addon_amt = max(current_sip - self.base_sip, 0.0)
                reduction_amt = 0.0
                reason = (f"Drawdown deepened to {drawdown:.2f}% (slab {slabs}). "
                          f"SIP increased to {current_sip:.2f} "
                          f"({1 + slabs * self.step_multiplier:.1f}x BASE_SIP).")

            elif slabs < s.previous_slab and s.previous_slab > 0:
                # RECOVERY rule -- drawdown shrinking, but no new HWM yet
                current_sip = previous_sip  # hold elevated SIP
                market_state = "RECOVERY"
                reduction_amt = 0.0
                addon_amt = 0.0
                reason = (f"Drawdown recovering ({s.previous_drawdown:.2f}% -> "
                          f"{drawdown:.2f}%) but no new HWM yet. SIP held at "
                          f"{current_sip:.2f} (no reduction during recovery).")

            else:
                # SIDEWAYS rule -- no new HWM, no new drawdown slab
                current_sip = previous_sip
                market_state = "SIDEWAYS" if slabs == 0 else "RECOVERY"
                reduction_amt = 0.0
                addon_amt = 0.0
                reason = "No new HWM and no change in drawdown slab. SIP unchanged."

        s.previous_sip = current_sip
        s.previous_slab = slabs
        s.previous_drawdown = drawdown
        s.market_state = market_state

        return self._row(price, s.hwm, drawdown, slabs, market_state,
                          previous_sip, current_sip, reduction_amt,
                          addon_amt, reason)

    @staticmethod
    def _row(price, hwm, drawdown, slabs, market_state, previous_sip,
              current_sip, reduction_amt, addon_amt, reason) -> dict:
        return {
            "Price": round(price, 4),
            "High Water Mark": round(hwm, 4),
            "Drawdown %": round(drawdown, 2),
            "Drawdown Slabs": slabs,
            "Market State": market_state,
            "Previous SIP": round(previous_sip, 2),
            "Current SIP": round(current_sip, 2),
            "Reduction Amount": round(reduction_amt, 2),
            "Add-on Amount": round(addon_amt, 2),
            "Investment": round(current_sip, 2),
            "Reason": reason,
        }

    def finish(self):
        pass


class FixedSIPEngine:
    """Traditional SIP: same amount invested every period."""

    def __init__(self, config: dict):
        self.base_sip = float(config["config"]["base_sip"])
        self.hwm = 0.0

    def initialize(self):
        pass

    def on_month(self, price: float) -> dict:
        if price > self.hwm:
            self.hwm = price
        drawdown = (self.hwm - price) / self.hwm * 100.0 if self.hwm else 0.0
        return {
            "Price": round(price, 4),
            "High Water Mark": round(self.hwm, 4),
            "Drawdown %": round(drawdown, 2),
            "Drawdown Slabs": 0,
            "Market State": "FIXED",
            "Previous SIP": self.base_sip,
            "Current SIP": self.base_sip,
            "Reduction Amount": 0.0,
            "Add-on Amount": 0.0,
            "Investment": self.base_sip,
            "Reason": "Traditional SIP: fixed amount every period.",
        }

    def finish(self):
        pass


ENGINE_REGISTRY = {
    "adaptive": AdaptiveSIPEngine,
    "fixed": FixedSIPEngine,
}


def build_strategy_from_dict(cfg: dict):
    """
    Factory: builds an engine from an in-memory config dict shaped like the
    YAML strategy files. Used by the grid-search optimizer to sweep
    parameters without writing a YAML file per combination -- the same
    rule-engine classes still interpret the config, so logic stays
    YAML-driven/config-driven rather than hardcoded per-combo.
    """
    strategy_type = cfg.get("type", "fixed")
    engine_cls = ENGINE_REGISTRY.get(strategy_type)
    if engine_cls is None:
        raise ValueError(f"Unknown strategy type '{strategy_type}'")
    engine = engine_cls(cfg)
    engine.initialize()
    return engine, cfg.get("name", strategy_type)


def build_strategy(yaml_path: str):
    """Factory: reads a strategy YAML and returns the correct engine instance."""
    cfg = load_strategy_config(yaml_path)
    return build_strategy_from_dict(cfg)
