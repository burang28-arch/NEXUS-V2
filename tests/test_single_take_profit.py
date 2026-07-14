import pandas as pd

from nexus.backtest import _build_position, _process_position_bar
from nexus.core.broker import BacktestBroker


def config() -> dict:
    return {
        "risk": {
            "base_margin_pct": 3.0,
            "leverage": 30.0,
            "stop_loss_pct": 0.8,
        },
        "exit": {
            "tp1_pct": 2.0,
            "tp2_pct": 3.0,
            "tp1_fraction": 0.7,
            "tp2_fraction": 0.3,
        },
    }


def signal_row() -> pd.Series:
    return pd.Series(
        {
            "timestamp": pd.Timestamp("2026-01-01", tz="UTC"),
            "score": 1,
            "size_multiplier": 1.0,
            "adx": 25.0,
            "rsi": 30.0,
            "atr": 1.0,
            "volume_score": 1,
            "long_candle_score": 0,
            "short_candle_score": 0,
        }
    )


def test_tp1_is_partial_and_tp2_closes_remaining_long_position() -> None:
    broker = BacktestBroker(0.0, 0.0)
    position = _build_position(
        "LONG",
        signal_row(),
        pd.Series(
            {
                "open": 100.0,
                "timestamp": pd.Timestamp(
                    "2026-01-01 00:15",
                    tz="UTC",
                ),
            }
        ),
        0,
        1,
        1000.0,
        config(),
        broker,
    )
    assert position is not None

    updated, first_trade = _process_position_bar(
        position,
        pd.Series(
            {
                "timestamp": pd.Timestamp(
                    "2026-01-01 00:30",
                    tz="UTC",
                ),
                "high": 102.0,
                "low": 100.0,
            }
        ),
        signal_row(),
        config(),
        broker,
    )

    assert first_trade is None
    assert updated is not None
    assert updated.tp1_done
    assert round(updated.remaining_fraction, 6) == 0.3

    updated, final_trade = _process_position_bar(
        updated,
        pd.Series(
            {
                "timestamp": pd.Timestamp(
                    "2026-01-01 00:45",
                    tz="UTC",
                ),
                "high": 103.0,
                "low": 101.0,
            }
        ),
        signal_row(),
        config(),
        broker,
    )

    assert updated is None
    assert final_trade is not None
    assert final_trade.exit_reason == "TP2"
