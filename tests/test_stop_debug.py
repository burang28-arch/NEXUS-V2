import pandas as pd
import pytest

from nexus.reports.stop_debug import StopDebugReport


def test_stop_debug_calculates_fixed_levels():
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range(
                "2026-01-01",
                periods=3,
                freq="15min",
                tz="UTC",
            ),
            "open": [100.0, 100.0, 101.0],
            "long_setup": [True, False, False],
            "short_setup": [False, True, False],
        }
    )
    config = {
        "risk": {
            "slippage_rate_pct": 0.0,
            "stop_loss_pct": 1.0,
        },
        "exit": {
            "take_profit_pct": 2.2,
        },
    }

    report = StopDebugReport.prepare(frame, config, 10)
    long_row = report[report.side == "LONG"].iloc[0]
    short_row = report[report.side == "SHORT"].iloc[0]

    assert long_row.stop_price == pytest.approx(99.0)
    assert long_row.take_profit_price == pytest.approx(102.2)
    assert short_row.stop_price == pytest.approx(102.01)
    assert short_row.take_profit_price == pytest.approx(98.778)
