from copy import deepcopy

import pandas as pd
import pytest

from nexus.optimizer import (
    SequentialOptimizer,
    _score,
    _set_nested,
    _valid_trial,
)


def test_set_nested_updates_value() -> None:
    config = {"entry": {"adx_max": 22.0}}
    _set_nested(config, "entry.adx_max", 18.0)
    assert config["entry"]["adx_max"] == 18.0


def test_score_uses_pf_trades_and_drawdown() -> None:
    value = _score(
        profit_factor=1.2,
        trades=500,
        max_drawdown_pct=10.0,
        target_trades=500,
    )
    assert value == pytest.approx(1.08)


def test_invalid_adx_and_tp_ranges_are_rejected() -> None:
    config = {
        "entry": {"adx_min": 20.0, "adx_max": 20.0},
        "risk": {"stop_loss_pct": 1.0},
        "exit": {"tp1_pct": 2.0, "tp2_pct": 4.0},
    }
    assert not _valid_trial(config)

    config["entry"]["adx_max"] = 30.0
    config["exit"]["tp2_pct"] = 2.0
    assert not _valid_trial(config)


def test_optimizer_keeps_base_config_unchanged() -> None:
    base = {
        "entry": {
            "adx_min": 0.0,
            "adx_max": 25.0,
            "l1_rsi_long_max": 30.0,
            "l1_rsi_short_min": 75.0,
            "min_rsi_difference": 10.0,
            "pivot_left_bars": 3,
            "l1_right_bars": 2,
            "l2_right_bars": 1,
        },
        "risk": {
            "initial_equity": 1000.0,
            "stop_loss_pct": 1.0,
        },
        "exit": {
            "tp1_pct": 2.0,
            "tp2_pct": 4.0,
        },
    }
    optimizer_config = {
        "objective": {"target_total_trades": 500},
        "parameters": {},
    }

    optimizer = SequentialOptimizer(base, optimizer_config)
    _, best = optimizer.run(pd.DataFrame())

    assert base["entry"]["adx_max"] == 25.0
    assert best["entry"]["adx_max"] == 25.0
    assert best is not base
