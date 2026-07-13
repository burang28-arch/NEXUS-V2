import pandas as pd

from nexus.backtest import _build_position, _process_position_bar
from nexus.core.broker import BacktestBroker


def config():
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
    return pd.Series(
        {
            "timestamp": pd.Timestamp("2026-01-01", tz="UTC"),
            "score": 1,
            "size_multiplier": 1.0,
            "adx": 18.0,
            "rsi": 30.0,
            "atr": 1.0,
            "volume_score": 1,
            "long_candle_score": 0,
            "short_candle_score": 0,
        }
    )


def test_take_profit_closes_full_long_position():
    broker = BacktestBroker(0.0, 0.0)
    position = _build_position(
        "LONG",
        signal_row(),
        pd.Timestamp("2026-01-01 00:15", tz="UTC"),
        0,
        1,
        1000.0,
        config(),
        broker,
        100.0,
    )

    updated, trade = _process_position_bar(
        position,
        pd.Series(
            {
                "timestamp": pd.Timestamp("2026-01-01 00:30", tz="UTC"),
                "high": 101.5,
                "low": 100.0,
            }
        ),
        signal_row(),
        config(),
        broker,
    )

    assert updated is None
    assert trade is not None
    assert trade.exit_reason == "TAKE_PROFIT"
    assert position.remaining_fraction == 0.0
