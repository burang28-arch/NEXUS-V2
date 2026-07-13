from pathlib import Path

import pandas as pd
import pytest

from nexus.reports.monthly_report import MonthlyReport


def sample_trades() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "entry_time": "2026-01-01T00:00:00Z",
                "side": "LONG",
                "net_pnl": 10.0,
                "holding_bars": 4,
            },
            {
                "entry_time": "2026-01-15T00:00:00Z",
                "side": "SHORT",
                "net_pnl": -5.0,
                "holding_bars": 6,
            },
            {
                "entry_time": "2026-02-01T00:00:00Z",
                "side": "LONG",
                "net_pnl": 8.0,
                "holding_bars": 2,
            },
        ]
    )


def test_monthly_report_groups_and_calculates() -> None:
    report = MonthlyReport.prepare(sample_trades())

    january = report.loc[report["month"] == "2026-01"].iloc[0]
    february = report.loc[report["month"] == "2026-02"].iloc[0]

    assert january["trades"] == 2
    assert january["long_trades"] == 1
    assert january["short_trades"] == 1
    assert january["wins"] == 1
    assert january["losses"] == 1
    assert january["win_rate_pct"] == pytest.approx(50.0)
    assert january["profit_factor"] == pytest.approx(2.0)
    assert january["net_profit"] == pytest.approx(5.0)
    assert january["average_holding_bars"] == pytest.approx(5.0)

    assert february["trades"] == 1
    assert february["profit_factor"] == pytest.approx(float("inf"))


def test_monthly_report_export(tmp_path: Path) -> None:
    output = tmp_path / "monthly_report.csv"
    MonthlyReport.export(sample_trades(), output)

    assert output.exists()
    saved = pd.read_csv(output)
    assert list(saved["month"]) == ["2026-01", "2026-02"]
