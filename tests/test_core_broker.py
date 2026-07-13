import pytest

from nexus.core.broker import BacktestBroker


def test_long_entry_and_exit_slippage() -> None:
    broker = BacktestBroker(fee_rate_pct=0.055, slippage_rate_pct=0.02)

    entry = broker.entry_fill(raw_price=100.0, side="LONG", notional=1000.0)
    exit_fill = broker.exit_fill(raw_price=110.0, side="LONG", quantity=10.0)

    assert entry.price == pytest.approx(100.02)
    assert exit_fill.price == pytest.approx(109.978)
    assert entry.fee == pytest.approx(0.55)



def test_limit_entry_has_no_adverse_slippage() -> None:
    broker = BacktestBroker(fee_rate_pct=0.055, slippage_rate_pct=0.02)
    fill = broker.limit_entry_fill(
        fill_price=99.7,
        side="LONG",
        notional=1000.0,
    )

    assert fill.price == pytest.approx(99.7)
    assert fill.fee == pytest.approx(0.55)
