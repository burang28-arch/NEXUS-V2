from pathlib import Path

import pandas as pd

from nexus.reports.trade_charts import TradeChartGenerator


def _trade(
    trade_id: int,
    result: str,
    pnl: float,
    entry_time,
    exit_time,
) -> dict:
    return {
        "trade_id": trade_id,
        "result": result,
        "side": "LONG" if trade_id % 2 else "SHORT",
        "signal_time": entry_time - pd.Timedelta(minutes=15),
        "entry_time": entry_time,
        "exit_time": exit_time,
        "entry_price": 101.0,
        "stop_price": 99.0,
        "tp1_price": 103.0,
        "tp2_price": 104.0,
        "exit_price": 104.0 if pnl > 0 else 99.0,
        "exit_reason": "TP2" if pnl > 0 else "STOP",
        "score": 1,
        "holding_bars": 4,
        "rsi": 30.0,
        "adx": 25.0,
        "net_pnl": pnl,
    }


def test_trade_chart_generator_creates_three_review_groups(
    tmp_path: Path,
) -> None:
    timestamps = pd.date_range(
        "2026-01-01",
        periods=80,
        freq="15min",
        tz="UTC",
    )
    market = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": [100 + index * 0.05 for index in range(80)],
            "high": [101 + index * 0.05 for index in range(80)],
            "low": [99 + index * 0.05 for index in range(80)],
            "close": [100.5 + index * 0.05 for index in range(80)],
            "rsi": [45.0 + (index % 10) for index in range(80)],
            "adx": [20.0 + (index % 8) for index in range(80)],
            "signal_reason": ["Bullish RSI divergence + ADX filter"] * 80,
            "divergence_l1_price": [100.0] * 80,
            "divergence_l2_price": [99.0] * 80,
            "divergence_l1_rsi": [20.0] * 80,
            "divergence_l2_rsi": [32.0] * 80,
            "divergence_rsi_difference": [12.0] * 80,
            "divergence_adx": [25.0] * 80,
        }
    )

    trades = pd.DataFrame(
        [
            _trade(1, "WIN", 4.0, timestamps[15], timestamps[20]),
            _trade(2, "LOSS", -2.0, timestamps[25], timestamps[30]),
            _trade(3, "WIN", 3.0, timestamps[35], timestamps[40]),
            _trade(4, "LOSS", -1.0, timestamps[45], timestamps[50]),
        ]
    )

    output = tmp_path / "trade_charts"
    generator = TradeChartGenerator(
        candles_before=5,
        candles_after=5,
        max_charts=2,
    )
    paths = generator.generate(market, trades, output)

    assert len(paths) == 6
    assert len(list((output / "successful").glob("*.png"))) == 2
    assert len(list((output / "failed").glob("*.png"))) == 2
    assert len(list((output / "recent").glob("*.png"))) == 2
    assert (output / "chart_index.csv").exists()
