from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import json
import math
import os
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import yaml

from nexus.backtest import calculate_statistics, run_backtest
from nexus.indicators import add_indicators
from nexus.signals import add_signal_columns


_WORKER_MARKET: pd.DataFrame | None = None
_WORKER_INDICATOR_CACHE: dict[str, pd.DataFrame] = {}
_WORKER_SIGNAL_CACHE: dict[str, pd.DataFrame] = {}


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


def _stable_key(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _indicator_cache_key(config: dict[str, Any]) -> str:
    return _stable_key(config["indicators"])


def _signal_cache_key(config: dict[str, Any]) -> str:
    return _stable_key(
        {
            "indicators": config["indicators"],
            "entry": config["entry"],
            "scoring": config["scoring"],
        }
    )


def _worker_initialize(market: pd.DataFrame) -> None:
    global _WORKER_MARKET
    global _WORKER_INDICATOR_CACHE
    global _WORKER_SIGNAL_CACHE

    _WORKER_MARKET = market
    _WORKER_INDICATOR_CACHE = {}
    _WORKER_SIGNAL_CACHE = {}


def _cached_enriched_frame(
    market: pd.DataFrame,
    config: dict[str, Any],
    indicator_cache: dict[str, pd.DataFrame],
    signal_cache: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, bool, bool]:
    indicator_key = _indicator_cache_key(config)
    signal_key = _signal_cache_key(config)

    indicator_hit = indicator_key in indicator_cache
    if indicator_hit:
        indicator_frame = indicator_cache[indicator_key]
    else:
        indicator_frame = add_indicators(market, config)
        indicator_cache[indicator_key] = indicator_frame

    signal_hit = signal_key in signal_cache
    if signal_hit:
        signal_frame = signal_cache[signal_key]
    else:
        signal_frame = add_signal_columns(indicator_frame, config)
        signal_cache[signal_key] = signal_frame

    return signal_frame, indicator_hit, signal_hit


def _monthly_trade_stats(trades: pd.DataFrame) -> tuple[float, int]:
    if trades.empty:
        return 0.0, 0

    entry_time = pd.to_datetime(trades["entry_time"], utc=True)
    monthly = trades.assign(
        month=entry_time.dt.to_period("M").astype(str)
    ).groupby("month").size()

    return float(monthly.mean()), int(monthly.min())


def _score(
    profit_factor: float,
    trades: int,
    max_drawdown_pct: float,
    target_trades: int,
) -> float:
    if not np.isfinite(profit_factor) or profit_factor < 0:
        return float("-inf")
    if target_trades <= 0:
        raise ValueError("target_total_trades must be positive.")

    trade_factor = trades / target_trades
    drawdown_factor = max(0.0, 1.0 - max_drawdown_pct / 100.0)
    return float(profit_factor * trade_factor * drawdown_factor)


def _equity_curve_from_trades(
    trades: pd.DataFrame,
    initial_equity: float,
) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame(columns=["timestamp", "equity"])

    ordered = trades.copy()
    ordered["exit_time"] = pd.to_datetime(
        ordered["exit_time"], utc=True, errors="coerce"
    )
    ordered = ordered.dropna(subset=["exit_time"]).sort_values("exit_time")
    equity = initial_equity + ordered["net_pnl"].astype(float).cumsum()

    return pd.DataFrame(
        {
            "timestamp": ordered["exit_time"].to_numpy(),
            "equity": equity.to_numpy(),
        }
    )


def _yearly_statistics(
    run_id: int,
    trades: pd.DataFrame,
    initial_equity: float,
    target_total_trades: int,
) -> pd.DataFrame:
    columns = [
        "run_id",
        "year",
        "trades",
        "wins",
        "losses",
        "win_rate_pct",
        "profit_factor",
        "net_profit",
        "return_pct",
        "max_drawdown_pct",
        "score",
    ]
    if trades.empty:
        return pd.DataFrame(columns=columns)

    data = trades.copy()
    data["exit_time"] = pd.to_datetime(
        data["exit_time"], utc=True, errors="coerce"
    )
    data = data.dropna(subset=["exit_time"])
    data["year"] = data["exit_time"].dt.year

    years = sorted(int(year) for year in data["year"].unique())
    yearly_target = max(1, int(round(target_total_trades / max(1, len(years)))))
    rows: list[dict[str, Any]] = []

    for year, group in data.groupby("year", sort=True):
        curve = _equity_curve_from_trades(group, initial_equity)
        stats = calculate_statistics(group, curve, initial_equity)
        score = _score(
            float(stats["profit_factor"]),
            int(stats["trades"]),
            float(stats["max_drawdown_pct"]),
            yearly_target,
        )
        rows.append(
            {
                "run_id": run_id,
                "year": int(year),
                "trades": int(stats["trades"]),
                "wins": int(stats["wins"]),
                "losses": int(stats["losses"]),
                "win_rate_pct": float(stats["win_rate_pct"]),
                "profit_factor": float(stats["profit_factor"]),
                "net_profit": float(stats["net_profit"]),
                "return_pct": float(stats["return_pct"]),
                "max_drawdown_pct": float(stats["max_drawdown_pct"]),
                "score": score,
            }
        )

    return pd.DataFrame(rows, columns=columns)


def _valid_trial(config: dict[str, Any]) -> bool:
    adx_min = float(config["entry"]["adx_min"])
    adx_max = float(config["entry"]["adx_max"])
    tp1 = float(config["exit"]["tp1_pct"])
    tp2 = float(config["exit"]["tp2_pct"])
    stop = float(config["risk"]["stop_loss_pct"])

    return (
        adx_min < adx_max
        and stop > 0
        and tp1 > 0
        and tp2 > tp1
    )


def _parameter_snapshot(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "adx_min": float(config["entry"]["adx_min"]),
        "adx_max": float(config["entry"]["adx_max"]),
        "l1_rsi_long_max": float(config["entry"]["l1_rsi_long_max"]),
        "l1_rsi_short_min": float(config["entry"]["l1_rsi_short_min"]),
        "min_rsi_difference": float(config["entry"]["min_rsi_difference"]),
        "pivot_left_bars": int(config["entry"]["pivot_left_bars"]),
        "l1_right_bars": int(config["entry"]["l1_right_bars"]),
        "l2_right_bars": int(config["entry"]["l2_right_bars"]),
        "stop_loss_pct": float(config["risk"]["stop_loss_pct"]),
        "tp1_pct": float(config["exit"]["tp1_pct"]),
        "tp2_pct": float(config["exit"]["tp2_pct"]),
    }


def _evaluate_trial(
    run_id: int,
    parameter: str,
    display_value: Any,
    trial_config: dict[str, Any],
    market: pd.DataFrame,
    indicator_cache: dict[str, pd.DataFrame],
    signal_cache: dict[str, pd.DataFrame],
    minimum_trades: int,
    minimum_average: float,
    target_trades: int,
) -> tuple[dict[str, Any], pd.DataFrame]:
    enriched, indicator_hit, signal_hit = _cached_enriched_frame(
        market,
        trial_config,
        indicator_cache,
        signal_cache,
    )
    trades, equity_curve = run_backtest(enriched, trial_config)
    initial_equity = float(trial_config["risk"]["initial_equity"])
    stats = calculate_statistics(
        trades,
        equity_curve,
        initial_equity,
    )
    average_monthly, minimum_monthly = _monthly_trade_stats(trades)

    yearly = _yearly_statistics(
        run_id,
        trades,
        initial_equity,
        target_trades,
    )

    evaluated_years = int(len(yearly))
    profitable_years = (
        int((yearly["net_profit"] > 0).sum())
        if not yearly.empty else 0
    )
    yearly_consistency = (
        profitable_years / evaluated_years
        if evaluated_years > 0 else 0.0
    )
    worst_year_pf = (
        float(yearly["profit_factor"].replace(np.inf, np.nan).min())
        if not yearly.empty else 0.0
    )
    if not np.isfinite(worst_year_pf):
        worst_year_pf = 0.0
    worst_year_return = (
        float(yearly["return_pct"].min())
        if not yearly.empty else 0.0
    )

    total_score = _score(
        float(stats["profit_factor"]),
        int(stats["trades"]),
        float(stats["max_drawdown_pct"]),
        target_trades,
    )
    final_score = (
        total_score * yearly_consistency
        if np.isfinite(total_score) else float("-inf")
    )
    eligibility = (
        int(stats["trades"]) >= minimum_trades
        and average_monthly >= minimum_average
    )
    objective_value = final_score if eligibility else float("-inf")

    row = {
        "run_id": run_id,
        "parameter": parameter,
        "value": display_value,
        "objective": objective_value,
        "final_score": final_score,
        "total_score": total_score,
        "yearly_consistency": yearly_consistency,
        "profitable_years": profitable_years,
        "evaluated_years": evaluated_years,
        "worst_year_profit_factor": worst_year_pf,
        "worst_year_return_pct": worst_year_return,
        "trades": int(stats["trades"]),
        "wins": int(stats["wins"]),
        "losses": int(stats["losses"]),
        "win_rate_pct": float(stats["win_rate_pct"]),
        "profit_factor": float(stats["profit_factor"]),
        "net_profit": float(stats["net_profit"]),
        "return_pct": float(stats["return_pct"]),
        "max_drawdown_pct": float(stats["max_drawdown_pct"]),
        "average_trade": float(stats["avg_trade"]),
        "average_trades_per_month": average_monthly,
        "minimum_trades_per_month": minimum_monthly,
        "indicator_cache_hit": indicator_hit,
        "signal_cache_hit": signal_hit,
        **_parameter_snapshot(trial_config),
    }
    return row, yearly


def _worker_evaluate(payload: tuple[Any, ...]) -> tuple[dict[str, Any], pd.DataFrame]:
    if _WORKER_MARKET is None:
        raise RuntimeError("Optimizer worker was not initialized.")

    (
        run_id,
        parameter,
        display_value,
        trial_config,
        minimum_trades,
        minimum_average,
        target_trades,
    ) = payload

    return _evaluate_trial(
        run_id,
        parameter,
        display_value,
        trial_config,
        _WORKER_MARKET,
        _WORKER_INDICATOR_CACHE,
        _WORKER_SIGNAL_CACHE,
        minimum_trades,
        minimum_average,
        target_trades,
    )


class SequentialOptimizer:
    """
    Coordinate-descent optimizer with parallel trials inside each stage.

    Stages remain sequential because the best result from one stage becomes
    the base configuration for the next stage. Values inside the same stage
    are independent and can run concurrently.
    """

    def __init__(
        self,
        base_strategy_config: dict[str, Any],
        optimizer_config: dict[str, Any],
        workers: int = 1,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> None:
        self.base_strategy_config = deepcopy(base_strategy_config)
        self.optimizer_config = optimizer_config
        self.workers = max(1, int(workers))
        self.progress_callback = progress_callback
        self.yearly_results = pd.DataFrame()
        self.indicator_cache_hits = 0
        self.signal_cache_hits = 0

    def run(self, market: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
        current_config = deepcopy(self.base_strategy_config)
        result_rows: list[dict[str, Any]] = []
        yearly_frames: list[pd.DataFrame] = []
        run_id = 0

        local_indicator_cache: dict[str, pd.DataFrame] = {}
        local_signal_cache: dict[str, pd.DataFrame] = {}

        objective = self.optimizer_config.get("objective", {})
        minimum_trades = int(objective.get("minimum_trades", 0))
        minimum_average = float(
            objective.get("minimum_average_trades_per_month", 0.0)
        )
        target_trades = int(objective.get("target_total_trades", 500))

        stages: list[tuple[str, list[Any]]] = []
        adx_ranges = self.optimizer_config.get("adx_ranges", [])
        if adx_ranges:
            stages.append(("entry.adx_range", adx_ranges))
        stages.extend(
            (parameter, values)
            for parameter, values in self.optimizer_config["parameters"].items()
        )
        total_stage_count = len(stages)

        executor: ProcessPoolExecutor | None = None
        if self.workers > 1:
            executor = ProcessPoolExecutor(
                max_workers=self.workers,
                initializer=_worker_initialize,
                initargs=(market,),
            )

        try:
            for stage_index, (parameter, values) in enumerate(stages, start=1):
                tasks: list[tuple[Any, ...]] = []

                for value in values:
                    trial_config = deepcopy(current_config)
                    if parameter == "entry.adx_range":
                        adx_min = float(value["min"])
                        adx_max = float(value["max"])
                        trial_config["entry"]["adx_min"] = adx_min
                        trial_config["entry"]["adx_max"] = adx_max
                        display_value: Any = f"{adx_min:g}-{adx_max:g}"
                    else:
                        _set_nested(trial_config, parameter, value)
                        display_value = value

                    if not _valid_trial(trial_config):
                        continue

                    run_id += 1
                    tasks.append(
                        (
                            run_id,
                            parameter,
                            display_value,
                            trial_config,
                            minimum_trades,
                            minimum_average,
                            target_trades,
                        )
                    )

                if not tasks:
                    continue

                if executor is None:
                    evaluated = [
                        _evaluate_trial(
                            task[0],
                            task[1],
                            task[2],
                            task[3],
                            market,
                            local_indicator_cache,
                            local_signal_cache,
                            minimum_trades,
                            minimum_average,
                            target_trades,
                        )
                        for task in tasks
                    ]
                else:
                    evaluated = list(executor.map(_worker_evaluate, tasks))

                stage_rows: list[dict[str, Any]] = []
                for row, yearly in evaluated:
                    result_rows.append(row)
                    stage_rows.append(row)
                    yearly_frames.append(yearly)
                    self.indicator_cache_hits += int(row["indicator_cache_hit"])
                    self.signal_cache_hits += int(row["signal_cache_hit"])

                valid_rows = [
                    row for row in stage_rows
                    if np.isfinite(float(row["objective"]))
                ]
                if valid_rows:
                    best = max(
                        valid_rows,
                        key=lambda row: (
                            float(row["objective"]),
                            float(row["profit_factor"]),
                            int(row["trades"]),
                        ),
                    )
                    if parameter == "entry.adx_range":
                        current_config["entry"]["adx_min"] = best["adx_min"]
                        current_config["entry"]["adx_max"] = best["adx_max"]
                    else:
                        _set_nested(current_config, parameter, best["value"])

                if self.progress_callback is not None:
                    self.progress_callback(
                        stage_index,
                        total_stage_count,
                        parameter,
                    )
        finally:
            if executor is not None:
                executor.shutdown(wait=True)

        results = pd.DataFrame(result_rows)
        if not results.empty:
            results = results.sort_values(
                ["objective", "profit_factor", "trades"],
                ascending=[False, False, False],
                na_position="last",
            ).reset_index(drop=True)

        self.yearly_results = (
            pd.concat(yearly_frames, ignore_index=True)
            if yearly_frames
            else pd.DataFrame()
        )
        return results, current_config

    @staticmethod
    def export_results(results: pd.DataFrame, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        results.to_csv(output_path, index=False)

    def export_yearly_results(self, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.yearly_results.to_csv(output_path, index=False)

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


def recommended_workers() -> int:
    cpu_count = os.cpu_count() or 4
    # 16 GB laptops can become slower from memory pressure above this.
    return max(1, min(10, cpu_count - 2))
