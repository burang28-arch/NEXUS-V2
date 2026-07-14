from pathlib import Path

from nexus.runtime import (
    estimate_backtest_seconds,
    format_duration,
    optimizer_plan,
    record_runtime,
)


def test_format_duration() -> None:
    assert format_duration(65) == "1분 5초"
    assert format_duration(None) == "측정 기록 없음"


def test_runtime_history_scales_by_rows(tmp_path: Path) -> None:
    history = tmp_path / "runtime.json"
    record_runtime(
        "backtest",
        seconds=10.0,
        rows=100,
        path=history,
    )

    assert estimate_backtest_seconds(200, path=history) == 20.0


def test_optimizer_plan_excludes_removed_parameters() -> None:
    config = {
        "adx_ranges": [{"min": 0, "max": 10}, {"min": 10, "max": 20}],
        "parameters": {
            "risk.stop_loss_pct": [0.8, 1.0],
            "exit.tp1_pct": [1.0, 2.0, 3.0],
        },
    }

    runs, stages = optimizer_plan(config)
    assert runs == 7
    assert stages == [2, 2, 3]
