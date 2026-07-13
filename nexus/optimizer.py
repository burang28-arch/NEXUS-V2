from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from nexus.backtest import calculate_statistics, run_backtest
from nexus.indicators import add_indicators
from nexus.signals import add_signal_columns


def load_optimizer_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Optimizer config not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    if not isinstance(config, dict):
        raise ValueError("Optimizer config root must be a mapping.")
    if "parameters" not in config:
        raise ValueError("Optimizer config requires a parameters section.")
    return config


def _set_nested(config: dict[str, Any], dotted_key: str, value: Any) -> None:
    keys = dotted_key.split(".")
    target = config
    for key in keys[:-1]:
        target = target[key]
    target[keys[-1]] = value


def _monthly_trade_stats(trades: pd.DataFrame) -> tuple[float, int]:
    if trades.empty:
        return 0.0, 0

    entry_time = pd.to_datetime(trades["entry_time"], utc=True)
    monthly = trades.assign(
        month=entry_time.dt.to_period("M").astype(str)
    ).groupby("month").size()

    return float(monthly.mean()), int(monthly.min())


def _objective_value(
    stats: dict[str, float],
    average_trades_per_month: float,
    minimum_trades: int,
    minimum_average_trades_per_month: float,
) -> float:
    if int(stats["trades"]) < minimum_trades:
        return float("-inf")
    if average_trades_per_month < minimum_average_trades_per_month:
        return float("-inf")

    profit_factor = float(stats["profit_factor"])
    if not pd.notna(profit_factor):
        return float("-inf")

    return profit_factor


class SequentialOptimizer:
    """
    Small coordinate-descent optimizer.

    Each parameter is tested independently. The best value becomes the
    starting point for the next parameter, keeping the number of runs small.
    """

    def __init__(
        self,
        base_strategy_config: dict[str, Any],
        optimizer_config: dict[str, Any],
    ) -> None:
        self.base_strategy_config = deepcopy(base_strategy_config)
        self.optimizer_config = optimizer_config

    def run(self, market: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
        current_config = deepcopy(self.base_strategy_config)
        results: list[dict[str, Any]] = []

        objective_config = self.optimizer_config.get("objective", {})
        minimum_trades = int(objective_config.get("minimum_trades", 0))
        minimum_average = float(
            objective_config.get("minimum_average_trades_per_month", 0.0)
        )

        for parameter, values in self.optimizer_config["parameters"].items():
            parameter_results: list[dict[str, Any]] = []

            for value in values:
                trial_config = deepcopy(current_config)
                _set_nested(trial_config, parameter, value)

                enriched = add_indicators(market, trial_config)
                enriched = add_signal_columns(enriched, trial_config)
                trades, equity_curve = run_backtest(enriched, trial_config)
                stats = calculate_statistics(
                    trades,
                    equity_curve,
                    float(trial_config["risk"]["initial_equity"]),
                )
                average_monthly, minimum_monthly = _monthly_trade_stats(trades)
                objective = _objective_value(
                    stats,
                    average_monthly,
                    minimum_trades,
                    minimum_average,
                )

                row = {
                    "parameter": parameter,
                    "value": value,
                    "objective": objective,
                    "trades": int(stats["trades"]),
                    "win_rate_pct": float(stats["win_rate_pct"]),
                    "profit_factor": float(stats["profit_factor"]),
                    "net_profit": float(stats["net_profit"]),
                    "return_pct": float(stats["return_pct"]),
                    "max_drawdown_pct": float(stats["max_drawdown_pct"]),
                    "average_trades_per_month": average_monthly,
                    "minimum_trades_per_month": minimum_monthly,
                }
                results.append(row)
                parameter_results.append(row)

            valid = [
                row for row in parameter_results
                if row["objective"] != float("-inf")
            ]
            if valid:
                best = max(
                    valid,
                    key=lambda row: (
                        row["objective"],
                        row["net_profit"],
                        row["trades"],
                    ),
                )
                _set_nested(current_config, parameter, best["value"])

        return pd.DataFrame(results), current_config

    @staticmethod
    def export_results(results: pd.DataFrame, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        results.to_csv(output_path, index=False)

    @staticmethod
    def export_best_config(config: dict[str, Any], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(
                config,
                handle,
                sort_keys=False,
                allow_unicode=True,
            )
