import pandas as pd

from nexus.reports.stop_analysis import StopAnalysis


def test_fixed_levels_are_valid_when_next_open_exists():
    frame = pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0],
            "long_setup": [True, False, False],
            "short_setup": [False, True, False],
        }
    )
    config = {
        "risk": {"stop_loss_pct": 1.0},
        "exit": {"take_profit_pct": 2.2},
    }

    report = StopAnalysis.prepare(frame, config)

    valid_count = report[
        (report.side == "ALL") & (report.reason == "valid")
    ]["count"].iloc[0]
    assert valid_count == 2
