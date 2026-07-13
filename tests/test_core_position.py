import pandas as pd
import pytest

from nexus.core.position import Position, PositionState


def make_position() -> Position:
    return Position(
        side="LONG",
        signal_index=10,
        entry_index=11,
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


def test_position_reduction_and_state() -> None:
    position = make_position()

    assert position.state is PositionState.OPEN
    position.reduce(0.70)
    position.mark_tp1_done()

    assert position.tp1_done
    assert position.remaining_fraction == pytest.approx(0.30)

    position.reduce(0.30)
    assert position.state is PositionState.CLOSED
    assert position.remaining_fraction == 0.0


def test_long_gross_pnl() -> None:
    position = make_position()
    assert position.gross_pnl(110.0, 0.5) == pytest.approx(5.0)
