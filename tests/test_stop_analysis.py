import pandas as pd

from nexus.reports.stop_analysis import StopAnalysis


def test_stop_analysis_counts_reasons() -> None:
    frame = pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0, 103.0],
            "bb_lower": [95.0, 96.0, 100.0, 98.0],
            "bb_middle": [102.0, 103.0, 102.0, 105.0],
            "bb_upper": [105.0, 106.0, 107.0, 108.0],
            "stop_price": [98.0, 102.0, 106.0, None],
            "long_setup": [True, True, False, False],
            "short_setup": [False, False, True, False],
        }
    )
    config = {"risk": {"slippage_rate_pct": 0.0}}

    report = StopAnalysis.prepare(frame, config)

    def count(side: str, reason: str) -> int:
        return int(
            report.loc[
                (report["side"] == side) & (report["reason"] == reason),
                "count",
            ].iloc[0]
        )

    assert count("LONG", "valid") == 1
    assert count("LONG", "stop_wrong_side") == 1
    assert count("SHORT", "valid") == 1
