import pandas as pd
import pytest

from nexus.backtest import (
    _create_pending_limit_order,
    _limit_fill_price,
)


def config():
    return {
        "entry": {
            "limit_offset_pct": 0.3,
            "limit_expiry_bars": 2,
        }
    }


def test_long_limit_is_point_three_percent_below_reference_open():
    reference_bar = pd.Series({"open": 100.0}, name=10)
    order = _create_pending_limit_order(
        "LONG",
        pd.Series(),
        9,
        reference_bar,
        config(),
    )

    assert order.limit_price == pytest.approx(99.7)
    assert order.bars_remaining == 2


def test_short_limit_is_point_three_percent_above_reference_open():
    reference_bar = pd.Series({"open": 100.0}, name=10)
    order = _create_pending_limit_order(
        "SHORT",
        pd.Series(),
        9,
        reference_bar,
        config(),
    )

    assert order.limit_price == pytest.approx(100.3)


def test_limit_touch_and_gap_fill_prices():
    long_order = _create_pending_limit_order(
        "LONG",
        pd.Series(),
        0,
        pd.Series({"open": 100.0}, name=1),
        config(),
    )

    touched_price, touched_at_open = _limit_fill_price(
        long_order,
        pd.Series({"open": 100.0, "low": 99.6, "high": 101.0}),
    )
    assert touched_price == pytest.approx(99.7)
    assert touched_at_open is False

    gap_price, gap_at_open = _limit_fill_price(
        long_order,
        pd.Series({"open": 99.5, "low": 99.0, "high": 100.0}),
    )
    assert gap_price == pytest.approx(99.5)
    assert gap_at_open is True
