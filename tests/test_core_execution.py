import pandas as pd

from nexus.core.broker import BacktestBroker
from nexus.core.execution import ExecutionEngine
from nexus.core.position import Position


def make_position() -> Position:
    return Position(
        side="LONG",
        signal_index=1,
        entry_index=2,
        entry_time=pd.Timestamp("2026-01-01", tz="UTC"),
        entry_price=100.0,
        stop_price=95.0,
        tp1_price=105.0,
        tp2_price=110.0,
        score=1,
        size_multiplier=1.0,
        margin_used=20.0,
        notional=100.0,
        quantity=1.0,
        fee_open=0.05,
    )


def test_execution_engine_wraps_handler_result() -> None:
    engine = ExecutionEngine()
    position = make_position()
    broker = BacktestBroker(0.055, 0.02)
    bar = pd.Series({"timestamp": pd.Timestamp("2026-01-01 00:15", tz="UTC")})
    signal = pd.Series({"timestamp": pd.Timestamp("2026-01-01", tz="UTC")})

    def handler(position, bar, signal_row, config, broker):
        return position, None

    result = engine.process_position(
        handler,
        position,
        bar,
        signal,
        {},
        broker,
    )

    assert result.position is position
    assert result.trade is None
