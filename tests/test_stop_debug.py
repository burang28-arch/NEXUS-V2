import pandas as pd
import pytest

from nexus.reports.stop_debug import StopDebugReport


def test_stop_debug_calculates_limit_levels():
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range(
                "2026-01-01",
                periods=4,
                freq="15min",
                tz="UTC",
            ),
            "open": [100.0, 100.0, 101.0, 102.0],
            "high": [101.0, 101.0, 102.0, 103.0],
            "low": [99.0, 99.6, 100.0, 101.0],
            "long_setup": [True, False, False, False],
            "short_setup": [False, False, False, False],
        }
    )
    config = {
        "entry": {
            "limit_offset_pct": 0.3,
            "limit_expiry_bars": 2,
        },
        "risk": {
            "stop_loss_pct": 1.0,
        },
        "exit": {
            "take_profit_pct": 1.5,
        },
    }

    report = StopDebugReport.prepare(frame, config, 10)
    row = report.iloc[0]

    assert row.limit_price == pytest.approx(99.7)
    assert bool(row.fillable_within_expiry) is True
    assert row.stop_price == pytest.approx(98.703)
    assert row.take_profit_price == pytest.approx(101.1955)
