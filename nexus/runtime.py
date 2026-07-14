from __future__ import annotations

import json
from pathlib import Path
from statistics import median
from typing import Any


DEFAULT_HISTORY_PATH = Path("reports/runtime_history.json")


def format_duration(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return "측정 기록 없음"

    total = int(round(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours:
        return f"{hours}시간 {minutes}분 {secs}초"
    if minutes:
        return f"{minutes}분 {secs}초"
    return f"{secs}초"


def load_history(path: Path = DEFAULT_HISTORY_PATH) -> dict[str, list[dict[str, Any]]]:
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

    return data if isinstance(data, dict) else {}


def record_runtime(
    command: str,
    seconds: float,
    rows: int,
    workers: int = 1,
    runs: int = 1,
    path: Path = DEFAULT_HISTORY_PATH,
) -> None:
    history = load_history(path)
    records = history.setdefault(command, [])
    records.append(
        {
            "seconds": float(seconds),
            "rows": int(rows),
            "workers": int(workers),
            "runs": int(runs),
        }
    )

    # Keep the file small and favor recent machine-specific measurements.
    history[command] = records[-10:]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(history, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def estimate_backtest_seconds(
    rows: int,
    path: Path = DEFAULT_HISTORY_PATH,
) -> float | None:
    records = load_history(path).get("backtest", [])
    estimates = []

    for record in records:
        old_rows = int(record.get("rows", 0))
        old_seconds = float(record.get("seconds", 0.0))
        if old_rows > 0 and old_seconds > 0:
            estimates.append(old_seconds * rows / old_rows)

    return median(estimates) if estimates else None


def estimate_optimizer_seconds(
    rows: int,
    workers: int,
    runs: int,
    stage_sizes: list[int],
    path: Path = DEFAULT_HISTORY_PATH,
) -> float | None:
    records = load_history(path).get("optimize", [])
    estimates = []

    for record in records:
        old_rows = int(record.get("rows", 0))
        old_seconds = float(record.get("seconds", 0.0))
        old_runs = int(record.get("runs", 0))
        old_workers = max(1, int(record.get("workers", 1)))

        if old_rows <= 0 or old_seconds <= 0 or old_runs <= 0:
            continue

        old_parallel_units = max(1.0, old_runs / old_workers)
        new_parallel_units = sum(
            max(1, (size + max(1, workers) - 1) // max(1, workers))
            for size in stage_sizes
            if size > 0
        )
        row_factor = rows / old_rows
        estimates.append(
            old_seconds
            * row_factor
            * new_parallel_units
            / old_parallel_units
        )

    return median(estimates) if estimates else None


def optimizer_plan(config: dict[str, Any]) -> tuple[int, list[int]]:
    stage_sizes: list[int] = []

    adx_ranges = config.get("adx_ranges", [])
    if adx_ranges:
        stage_sizes.append(len(adx_ranges))

    for values in config.get("parameters", {}).values():
        stage_sizes.append(len(values))

    return sum(stage_sizes), stage_sizes
