"""
main.py - ASRP Command Line Interface

Usage examples:
  # Demo run with synthetic data (no internet needed):
  python main.py --demo --asset "DEMO_NIFTY" --start 2015-01-01 --end 2025-01-01

  # Real data via Yahoo Finance (needs internet + yfinance):
  python main.py --ticker "^NSEI" --start 2015-01-01 --end 2025-01-01
"""

import argparse
import os
import pandas as pd

from core.data_loader import generate_synthetic, download_yahoo, resample_monthly
from core.backtest import compare_strategies
from reports.report_generator import generate_excel_report, generate_csv_reports


def run_batch_cli(args):
    from core.batch_runner import run_batch
    from core.ticker_lists import TICKER_UNIVERSES

    tickers = TICKER_UNIVERSES.get(args.universe)
    if tickers is None:
        raise SystemExit(f"Unknown --universe '{args.universe}'. Choices: {list(TICKER_UNIVERSES)}")

    def progress(i, total, ticker):
        print(f"[ASRP][batch] ({i}/{total}) {ticker} ...")

    print(f"[ASRP] Running batch backtest: {args.universe} ({len(tickers)} tickers) "
          f"with strategy {args.strategy}")
    batch = run_batch(args.strategy, tickers, args.start, args.end,
                       batch_tag=args.universe, progress_cb=progress)

    print("\n=== LEADERBOARD (top 10) ===")
    print(batch["leaderboard"].head(10).to_string(index=False))
    if batch["errors"]:
        print(f"\n[ASRP] {len(batch['errors'])} tickers failed:")
        for t, err in batch["errors"].items():
            print(f"  - {t}: {err}")

    out_csv = os.path.join("reports/output", f"batch_leaderboard_{args.universe.replace(' ', '_')}.csv")
    os.makedirs("reports/output", exist_ok=True)
    batch["leaderboard"].to_csv(out_csv, index=False)
    print(f"\n[ASRP] Leaderboard saved to {out_csv}")


def run_optimize_cli(args):
    from core.optimizer import grid_search
    from core.strategy_engine import load_strategy_config

    if args.demo or not args.ticker:
        raw = generate_synthetic(args.start, args.end)
        price_df = raw[["Date", "Close"]].rename(columns={"Close": "Price"})
        asset_name = args.asset if args.asset != "ASSET" else "DEMO_ASSET"
    else:
        raw = download_yahoo(args.ticker, args.start, args.end)
        price_df = resample_monthly(raw)
        asset_name = args.asset if args.asset != "ASSET" else args.ticker

    base_config = load_strategy_config(args.strategy)
    print(f"[ASRP] Grid-searching Adaptive SIP params on {asset_name} ...")
    result = grid_search(price_df, base_config, asset_name=asset_name)

    print("\n=== TOP 10 PARAMETER COMBINATIONS (by XIRR %) ===")
    print(result["results_df"].head(10).to_string(index=False))
    print(f"\n[ASRP] BEST: {result['best']['params']} -> XIRR {result['best']['summary']['XIRR %']}%")

    out_csv = "reports/output/grid_search_results.csv"
    os.makedirs("reports/output", exist_ok=True)
    result["results_df"].to_csv(out_csv, index=False)
    print(f"[ASRP] Full grid results saved to {out_csv}")


def main():
    parser = argparse.ArgumentParser(description="Adaptive SIP Research Platform (ASRP)")
    parser.add_argument("--demo", action="store_true", help="Use synthetic demo data (no internet required)")
    parser.add_argument("--ticker", type=str, help="Yahoo Finance ticker, e.g. ^NSEI, RELIANCE.NS, SPY")
    parser.add_argument("--asset", type=str, default="ASSET", help="Display name for the asset")
    parser.add_argument("--start", type=str, default="2015-01-01")
    parser.add_argument("--end", type=str, default="2025-01-01")
    parser.add_argument("--out", type=str, default="reports/output/ASRP_Report.xlsx")
    parser.add_argument("--batch", action="store_true", help="Run batch backtest across a ticker universe")
    parser.add_argument("--universe", type=str, default="Nifty50", help="Ticker universe for --batch (see core/ticker_lists.py)")
    parser.add_argument("--strategy", type=str, default="strategies/adaptive_sip_v1_1.yaml", help="Strategy YAML path for --batch/--optimize")
    parser.add_argument("--optimize", action="store_true", help="Run grid-search parameter optimization")
    args = parser.parse_args()

    if args.batch:
        run_batch_cli(args)
        return
    if args.optimize:
        run_optimize_cli(args)
        return

    if args.demo or not args.ticker:
        print(f"[ASRP] Generating synthetic demo price series ({args.start} -> {args.end}) ...")
        raw = generate_synthetic(args.start, args.end)
        price_df = raw[["Date", "Close"]].rename(columns={"Close": "Price"})
        asset_name = args.asset if args.asset != "ASSET" else "DEMO_ASSET"
    else:
        print(f"[ASRP] Downloading {args.ticker} from Yahoo Finance ...")
        raw = download_yahoo(args.ticker, args.start, args.end)
        price_df = resample_monthly(raw)
        asset_name = args.asset if args.asset != "ASSET" else args.ticker

    print(f"[ASRP] {len(price_df)} monthly price points loaded for {asset_name}.")

    strategy_paths = {
        "traditional": "strategies/traditional_sip.yaml",
        "adaptive": "strategies/adaptive_sip_v1_1.yaml",
    }

    print("[ASRP] Running Traditional SIP and Adaptive SIP v1.1 backtests ...")
    result = compare_strategies(price_df, strategy_paths, asset_name=asset_name)

    print("\n=== COMPARISON ===")
    print(result["comparison"].to_string(index=False))

    print(f"\n[ASRP] Writing Excel report to {args.out} ...")
    generate_excel_report(result, args.out, asset_name=asset_name)
    print("[ASRP] Done. Report saved.")


if __name__ == "__main__":
    main()
