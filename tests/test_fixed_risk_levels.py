import pandas as pd
import pytest

from nexus.backtest import _build_position
from nexus.core.broker import BacktestBroker


def base_config():
    return {
        "risk": {
            "base_margin_pct": 2.0,
            "leverage": 1.0,
            "stop_loss_pct": 1.0,
        },
        "exit": {
            "take_profit_pct": 2.2,
        },
    }


def signal_row():
    return pd.Series({"score": 1, "size_multiplier": 1.0})


def test_long_levels_are_entry_based():
    broker = BacktestBroker(0.0, 0.0)
    position = _build_position(
        "LONG",
        signal_row(),
        pd.Series(
            {
                "open": 100.0,
                "timestamp": pd.Timestamp("2026-01-01", tz="UTC"),
            }
        ),
        0,
        1,
        1000.0,
        base_config(),
        broker,
    )

    assert position.stop_price == pytest.approx(99.0)
    assert position.tp1_price == pytest.approx(102.2)
    assert position.tp2_price == pytest.approx(102.2)


def test_short_levels_are_entry_based():
    broker = BacktestBroker(0.0, 0.0)
    position = _build_position(
        "SHORT",
        signal_row(),
        pd.Series(
            {
                "open": 100.0,
                "timestamp": pd.Timestamp("2026-01-01", tz="UTC"),
            }
        ),
        0,
        1,
        1000.0,
        base_config(),
        broker,
    )

    assert position.stop_price == pytest.approx(101.0)
    assert position.tp1_price == pytest.approx(97.8)
    assert position.tp2_price == pytest.approx(97.8)
