# Adaptive SIP Research Platform (ASRP)
### Author: Amit Kumar | Official Strategy: Professional Adaptive SIP v1.1 (Logic Freeze)

A modular, rule-based quantitative investment research platform. The
Adaptive SIP strategy is **not hardcoded** — it's defined in
`strategies/adaptive_sip_v1_1.yaml` and interpreted by the Rule Engine in
`core/strategy_engine.py`. You can add new strategies by simply adding a
new YAML file — no Python changes required.

## What's included in this build (v0.9)

| Phase | Status | Location |
|---|---|---|
| 1. Foundation / project skeleton | ✅ Done | whole repo |
| 2. Data Engine (Yahoo Finance + synthetic demo data) | ✅ Done | `core/data_loader.py` |
| 3. Strategy Engine (rule-based, YAML-driven) | ✅ Done | `core/strategy_engine.py`, `strategies/*.yaml` |
| 4. Portfolio Engine | ✅ Done | `core/portfolio.py` |
| 5. Backtesting Engine | ✅ Done | `core/backtest.py` |
| 6. Metrics Engine (XIRR, CAGR, Drawdown, Sharpe, Sortino, Calmar) | ✅ Done | `core/metrics.py` |
| 9. Report Generator (Excel, multi-sheet, charts) | ✅ Done | `reports/report_generator.py` |
| 7. Batch backtesting (many assets) | 🔜 Next | extend `main.py` loop |
| 8. Comparison engine | ✅ Basic version done | `core/backtest.compare_strategies()` |
| 10. Streamlit Dashboard | 🔜 Next | `dashboard/` (empty, scaffolded) |
| 11-15. Visualization, Research, Optimization, AI, Deployment | 🔜 Future phases | — |

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run tests (validates strategy logic against the spec's own examples)
python tests/test_strategy.py

# 3. Run a demo backtest (no internet required, uses synthetic price data)
python main.py --demo --asset "DEMO_NIFTY" --start 2015-01-01 --end 2025-01-01

# 4. Run with REAL data (requires internet + yfinance)
python main.py --ticker "^NSEI" --asset "NIFTY 50" --start 2015-01-01 --end 2025-01-01
python main.py --ticker "RELIANCE.NS" --start 2018-01-01 --end 2025-01-01
python main.py --ticker "SPY" --start 2015-01-01 --end 2025-01-01
```

Output: an Excel report at `reports/output/ASRP_Report.xlsx` with:
- **Comparison** sheet (Traditional vs Adaptive SIP: XIRR, CAGR, Profit, Winner)
- One sheet per strategy with the **full transaction history** (Date, Price,
  HWM, Drawdown %, Drawdown Slabs, Market State, Previous/Current SIP,
  Reduction/Add-on Amount, Units, Total Units, Average Cost, Portfolio
  Value, Profit/Loss, Reason) + a Portfolio Value chart.

## Why no internet in this sandbox build?

This build was generated inside a sandboxed environment without outbound
internet access, so live Yahoo Finance/NSE downloads couldn't be tested
here. The `--demo` flag uses a synthetic price generator
(`core/data_loader.generate_synthetic`) that produces a realistic
bull → drawdown → recovery → new-high cycle, so you can see the full
Adaptive SIP state machine (BULL/SIDEWAYS/BEAR/RECOVERY/NEW HIGH) in
action. On your own machine (with internet), just drop the `--demo` flag
and pass `--ticker` — `core/data_loader.download_yahoo()` will fetch real
data via `yfinance` automatically.

## Adding a new strategy (no code change needed)

Create a new YAML file in `strategies/`, e.g. `strategies/adaptive_sip_v2.yaml`,
following the same structure as `adaptive_sip_v1_1.yaml`. Then reference it
in `main.py`'s `strategy_paths` dict (or pass it dynamically once the
dashboard/CLI argument for strategy selection is added in a later phase).

## Project structure

```
adaptive-sip-platform/
├── app/                  # (reserved for CLI sub-commands, Phase 1+)
├── core/                 # Strategy, Portfolio, Backtest, Metrics, Data engines
├── strategies/           # YAML rule definitions (Adaptive v1.1, Traditional)
├── data/cache/           # Downloaded/cached price data
├── database/             # (reserved for DuckDB, Phase 2)
├── reports/              # Report generator + output/ folder for Excel files
├── dashboard/            # (reserved for Streamlit app, Phase 10)
├── tests/                # Unit tests validating strategy logic vs spec examples
├── docs/                 # (reserved)
├── config/config.yaml    # Central configuration
├── notebooks/            # (reserved for research notebooks)
├── assets/               # (reserved)
└── main.py               # CLI entry point
```

## Strategy Logic Reference (v1.1, Logic Freeze)

```
BASE_SIP        = 10,000
MINIMUM_SIP     = 2,500
REDUCTION_FACTOR= 0.50   (Bull: SIP = max(prev_SIP * 0.5, MIN_SIP))
DRAWDOWN_STEP   = 5%     (Bear: 1 slab per 5% drawdown)
STEP_MULTIPLIER = 0.50   (Bear: SIP = BASE_SIP * (1 + slabs * 0.5))
MAX_MULTIPLIER  = 5.0    (Cap: SIP never exceeds 5x BASE_SIP)
```

- **BULL**: price makes a new High Water Mark → SIP reduces (half each new high, floor at MINIMUM_SIP)
- **SIDEWAYS**: no new HWM, no new drawdown slab → SIP unchanged
- **BEAR**: drawdown deepens into a new 5% slab → SIP steps up from BASE_SIP reference
- **RECOVERY**: drawdown shrinking but no new HWM yet → SIP held at the elevated level (no reduction)
- **NEW HIGH**: price exceeds the previous HWM → cycle repeats, SIP reduces gradually again

## Next steps (roadmap for future sessions)

1. **Phase 2b**: DuckDB persistence layer (`database/`) for cached price data
2. **Phase 7**: Batch backtesting loop over a list of tickers (Nifty50, all ETFs, etc.)
3. **Phase 10**: Streamlit dashboard (`streamlit run dashboard/app.py`) with pages
   for Asset Search, Run Backtest, Strategy Comparison, Charts
4. **Phase 13**: Grid-search optimizer over `drawdown_step`, `reduction_factor`, etc.
5. **Phase 14**: Natural-language research assistant on top of the batch results
