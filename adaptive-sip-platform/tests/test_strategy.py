"""
tests/test_strategy.py
Basic sanity tests for the Adaptive SIP v1.1 rule engine, checking the
examples given directly in the strategy specification document.
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.strategy_engine import build_strategy


def test_bull_reduction_sequence():
    engine, _ = build_strategy("strategies/adaptive_sip_v1_1.yaml")
    # START
    r0 = engine.on_month(100)
    assert r0["Current SIP"] == 10000
    # New high -> reduce
    r1 = engine.on_month(110)
    assert r1["Current SIP"] == 5000
    r2 = engine.on_month(125)
    assert r2["Current SIP"] == 2500
    # Below minimum floor stays at 2500
    r3 = engine.on_month(150)
    assert r3["Current SIP"] == 2500


def test_drawdown_slabs_bear_market():
    engine, _ = build_strategy("strategies/adaptive_sip_v1_1.yaml")
    engine.on_month(200)          # START, HWM = 200
    r = engine.on_month(190)      # 5% drawdown -> slab 1
    assert r["Drawdown Slabs"] == 1
    assert r["Current SIP"] == 15000  # 10000 * 1.5
    r2 = engine.on_month(180)     # 10% drawdown -> slab 2
    assert r2["Drawdown Slabs"] == 2
    assert r2["Current SIP"] == 20000  # 10000 * 2.0


def test_recovery_holds_sip():
    engine, _ = build_strategy("strategies/adaptive_sip_v1_1.yaml")
    engine.on_month(200)          # HWM = 200
    engine.on_month(160)          # 20% dd -> slab 4 -> SIP 30000
    r = engine.on_month(165)      # dd shrinks to ~18%, still slab < previous? check hold
    assert r["Current SIP"] == 30000  # held, not reduced
    assert r["Market State"] in ("RECOVERY",)


def test_max_sip_cap():
    engine, _ = build_strategy("strategies/adaptive_sip_v1_1.yaml")
    engine.on_month(1000)
    r = engine.on_month(550)   # 45% drawdown -> would be slab 9 -> 5.5x, capped to 5x
    assert r["Current SIP"] <= 50000


if __name__ == "__main__":
    test_bull_reduction_sequence()
    test_drawdown_slabs_bear_market()
    test_recovery_holds_sip()
    test_max_sip_cap()
    print("All tests passed!")
