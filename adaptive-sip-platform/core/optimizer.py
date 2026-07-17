"""
core/optimizer.py
Grid-Search Optimizer: sweeps Adaptive SIP parameters
(drawdown_step, reduction_factor, step_multiplier, max_multiplier) to find
the combination that maximizes a chosen metric (default XIRR %) on a given
price series. Still goes through the YAML-driven rule engine
(build_strategy_from_dict) -- only the config values are swept, the logic
itself stays in core/strategy_engine.py.
"""

from __future__ import annotations
from itertools import product
from typing import Callable, Optional
import copy
import pandas as pd

from core.backtest import run_backtest_with_config


DEFAULT_GRID = {
    "drawdown_step": [5, 7.5, 10],
    "reduction_factor": [0.3, 0.5, 0.7],
    "step_multiplier": [0.3, 0.5, 0.75],
    "max_multiplier": [3.0, 5.0, 7.0],
}


def grid_search(price_df: pd.DataFrame, base_config: dict, param_grid: dict = None,
                 metric: str = "XIRR %", asset_name: str = "ASSET",
                 progress_cb: Optional[Callable[[int, int], None]] = None) -> dict:
    """
    base_config: a strategy config dict shaped like strategies/adaptive_sip_v1_1.yaml
                 (already loaded, e.g. via strategy_engine.load_strategy_config)
    param_grid:  dict of {param_name: [values...]} to sweep inside base_config['config'].
                 Defaults to DEFAULT_GRID.

    Returns:
        {
          'results_df': pd.DataFrame of every combination + its metrics,
          'best': {'params': {...}, 'summary': {...}},
          'worst': {'params': {...}, 'summary': {...}},
        }
    """
    grid = param_grid or DEFAULT_GRID
    keys = list(grid.keys())
    combos = list(product(*[grid[k] for k in keys]))
    total = len(combos)

    rows = []
    best = None
    worst = None

    for i, combo in enumerate(combos, start=1):
        params = dict(zip(keys, combo))
        cfg = copy.deepcopy(base_config)
        cfg["config"].update(params)

        result = run_backtest_with_config(price_df, cfg, asset_name=asset_name)
        summary = result["summary"]

        row = {**params, **summary}
        rows.append(row)

        candidate = {"params": params, "summary": summary}
        if best is None or summary[metric] > best["summary"][metric]:
            best = candidate
        if worst is None or summary[metric] < worst["summary"][metric]:
            worst = candidate

        if progress_cb:
            progress_cb(i, total)

    results_df = pd.DataFrame(rows).sort_values(metric, ascending=False).reset_index(drop=True)

    return {"results_df": results_df, "best": best, "worst": worst}
