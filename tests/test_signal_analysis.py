from pathlib import Path

import pandas as pd
import pytest

from nexus.reports.signal_analysis import SignalAnalyzer


def sample_trades() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"side": "LONG", "score": 0, "adx": 14.0, "rsi": 19.0, "net_pnl": 10.0},
            {"side": "LONG", "score": 1, "adx": 18.0, "rsi": 28.0, "net_pnl": -5.0},
            {"side": "SHORT", "score": 1, "adx": 22.0, "rsi": 67.0, "net_pnl": 8.0},
            {"side": "SHORT", "score": 2, "adx": 27.0, "rsi": 76.0, "net_pnl": -4.0},
        ]
    )


def test_signal_analysis_side_summary() -> None:
    report = SignalAnalyzer.prepare(sample_trades())

    long_row = report[
        (report["category"] == "side") & (report["value"] == "LONG")
    ].iloc[0]

    assert long_row["trades"] == 2
    assert long_row["wins"] == 1
    assert long_row["losses"] == 1
    assert long_row["win_rate_pct"] == pytest.approx(50.0)
    assert long_row["profit_factor"] == pytest.approx(2.0)
    assert long_row["net_profit"] == pytest.approx(5.0)


def test_signal_analysis_contains_buckets() -> None:
    report = SignalAnalyzer.prepare(sample_trades())

    assert ((report["category"] == "score") & (report["value"] == "2")).any()
    assert ((report["category"] == "adx") & (report["value"] == "15-20")).any()
    assert ((report["category"] == "rsi") & (report["value"] == "65-70")).any()


def test_signal_analysis_export(tmp_path: Path) -> None:
    output = tmp_path / "signal_analysis.csv"
    SignalAnalyzer.export(sample_trades(), output)

    assert output.exists()
    saved = pd.read_csv(output)
    assert "profit_factor" in saved.columns
