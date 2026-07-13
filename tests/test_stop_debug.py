import pandas as pd

from nexus.reports.stop_debug import StopDebugReport


def test_stop_debug_shows_wrong_side_values() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range(
                "2026-01-01",
                periods=3,
                freq="15min",
                tz="UTC",
            ),
            "open": [100.0, 100.0, 101.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 99.5, 100.0],
            "close": [100.5, 101.0, 102.0],
            "atr": [1.0, 1.0, 1.0],
            "swing_low": [102.0, 102.0, 102.0],
            "swing_high": [98.0, 98.0, 98.0],
            "stop_price": [101.8, 98.2, None],
            "long_setup": [True, False, False],
            "short_setup": [False, True, False],
        }
    )
    config = {
        "risk": {
            "slippage_rate_pct": 0.0,
            "atr_stop_buffer": 0.2,
        }
    }

    report = StopDebugReport.prepare(frame, config, max_rows=10)

    assert len(report) == 2
    assert set(report["reason"]) == {"stop_wrong_side"}
    assert report.loc[report["side"] == "LONG", "swing_price"].iloc[0] == 102.0
    assert report.loc[report["side"] == "SHORT", "swing_price"].iloc[0] == 98.0
