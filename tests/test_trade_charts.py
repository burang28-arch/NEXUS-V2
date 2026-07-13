from pathlib import Path

import pandas as pd

from nexus.reports.trade_charts import TradeChartGenerator


def test_trade_chart_generator_creates_png(tmp_path: Path) -> None:
    timestamps = pd.date_range(
        "2026-01-01",
        periods=40,
        freq="15min",
        tz="UTC",
    )
    market = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": [100 + index * 0.1 for index in range(40)],
            "high": [101 + index * 0.1 for index in range(40)],
            "low": [99 + index * 0.1 for index in range(40)],
            "close": [100.5 + index * 0.1 for index in range(40)],
        }
    )

    trades = pd.DataFrame(
        [
            {
                "trade_id": 1,
                "side": "LONG",
                "result": "WIN",
                "entry_time": timestamps[10],
                "exit_time": timestamps[20],
                "entry_price": 101.0,
                "stop_price": 98.0,
                "tp1_price": 103.0,
                "tp2_price": 105.0,
                "exit_price": 105.0,
                "net_pnl": 4.0,
            }
        ]
    )

    generator = TradeChartGenerator(
        candles_before=5,
        candles_after=5,
        max_charts=10,
    )
    paths = generator.generate(
        market,
        trades,
        tmp_path / "charts",
    )

    assert len(paths) == 1
    assert paths[0].exists()
    assert paths[0].suffix == ".png"
