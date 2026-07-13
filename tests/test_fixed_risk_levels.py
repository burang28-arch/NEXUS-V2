import pandas as pd
import pytest

from nexus.backtest import _build_position
from nexus.core.broker import BacktestBroker


def base_config():
    return {
        "risk": {
            "base_margin_pct": 3.0,
            "leverage": 30.0,
            "stop_loss_pct": 1.0,
        },
        "exit": {
            "take_profit_pct": 1.5,
        },
    }


def signal_row():
    return pd.Series({"score": 1, "size_multiplier": 1.0})


def test_long_levels_are_limit_entry_based():
    broker = BacktestBroker(0.0, 0.0)
    position = _build_position(
        "LONG",
        signal_row(),
        pd.Timestamp("2026-01-01", tz="UTC"),
        0,
        1,
        1000.0,
        base_config(),
        broker,
        99.7,
    )

    assert position.entry_price == pytest.approx(99.7)
    assert position.stop_price == pytest.approx(98.703)
    assert position.tp1_price == pytest.approx(101.1955)


def test_short_levels_are_limit_entry_based():
    broker = BacktestBroker(0.0, 0.0)
    position = _build_position(
        "SHORT",
        signal_row(),
        pd.Timestamp("2026-01-01", tz="UTC"),
        0,
        1,
        1000.0,
        base_config(),
        broker,
        100.3,
    )

    assert position.entry_price == pytest.approx(100.3)
    assert position.stop_price == pytest.approx(101.303)
    assert position.tp1_price == pytest.approx(98.7955)
