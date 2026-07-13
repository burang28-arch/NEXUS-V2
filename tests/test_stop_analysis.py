import pandas as pd

from nexus.reports.stop_analysis import StopAnalysis


def test_fixed_levels_are_valid_for_both_sides():
    frame = pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0],
            "long_setup": [True, False, False],
            "short_setup": [False, True, False],
        }
    )
    config = {
        "risk": {"stop_loss_pct": 1.0},
        "exit": {"tp1_pct": 2.0, "tp2_pct": 4.0},
    }
    report = StopAnalysis.prepare(frame, config)
    assert report.loc[(report.side == "LONG") & (report.reason == "valid"), "count"].iloc[0] == 1
    assert report.loc[(report.side == "SHORT") & (report.reason == "valid"), "count"].iloc[0] == 1
