import pandas as pd
import pytest

from nexus.core.account import Account
from nexus.core.portfolio import Portfolio
from nexus.core.position import Position


def make_position(side: str, margin_used: float = 20.0) -> Position:
    return Position(
        side=side,
        signal_index=10,
        entry_index=11,
        entry_time=pd.Timestamp("2026-01-01", tz="UTC"),
        entry_price=100.0,
        stop_price=95.0 if side == "LONG" else 105.0,
        tp1_price=105.0 if side == "LONG" else 95.0,
        tp2_price=110.0 if side == "LONG" else 90.0,
        score=1,
        size_multiplier=1.0,
        margin_used=margin_used,
        notional=100.0,
        quantity=1.0,
        fee_open=0.05,
    )


def test_portfolio_allows_hedged_positions() -> None:
    portfolio = Portfolio(Account.create(1000.0))

    portfolio.open_position(make_position("LONG", 20.0))
    portfolio.open_position(make_position("SHORT", 30.0))

    assert portfolio.has_open_position("LONG")
    assert portfolio.has_open_position("SHORT")
    assert portfolio.used_margin == pytest.approx(50.0)
    assert portfolio.account.free_margin == pytest.approx(950.0)


def test_portfolio_prevents_duplicate_side() -> None:
    portfolio = Portfolio(Account.create(1000.0))
    portfolio.open_position(make_position("LONG"))

    with pytest.raises(RuntimeError):
        portfolio.open_position(make_position("LONG"))
