from copy import deepcopy

import pandas as pd

from nexus.optimizer import SequentialOptimizer, _set_nested


def test_set_nested_updates_value() -> None:
    config = {"entry": {"adx_max": 22.0}}
    _set_nested(config, "entry.adx_max", 18.0)
    assert config["entry"]["adx_max"] == 18.0


def test_optimizer_keeps_base_config_unchanged() -> None:
    base = {
        "entry": {"adx_max": 22.0},
        "risk": {"initial_equity": 1000.0},
    }
    optimizer_config = {"parameters": {}}

    optimizer = SequentialOptimizer(base, optimizer_config)
    _, best = optimizer.run(pd.DataFrame())

    assert base["entry"]["adx_max"] == 22.0
    assert best["entry"]["adx_max"] == 22.0
    assert best is not base
