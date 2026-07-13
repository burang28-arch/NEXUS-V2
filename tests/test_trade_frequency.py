import pandas as pd

from nexus.reports.trade_frequency import TradeFrequencyAnalyzer


def test_trade_frequency_outputs_expected_stages() -> None:
    frame = pd.DataFrame(
        {
            "open": [100.0, 100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0, 104.0],
            "low": [99.0, 98.0, 100.0, 101.0],
            "rsi": [30.0, 32.0, 68.0, 50.0],
            "adx": [18.0, 20.0, 19.0, 18.0],
            "atr": [2.0, 2.0, 2.0, 2.0],
            "bb_lower": [99.5, 99.0, 99.5, 100.0],
            "bb_middle": [101.0, 101.0, 101.5, 102.5],
            "bb_upper": [102.5, 103.0, 102.5, 104.0],
            "swing_low": [98.0, 98.0, 98.0, 98.0],
            "swing_high": [103.0, 103.0, 103.0, 103.0],
            "stop_price": [97.5, 97.5, 103.5, None],
        }
    )
    trades = pd.DataFrame(
        [
            {"side": "LONG"},
            {"side": "SHORT"},
        ]
    )
    config = {
        "entry": {
            "adx_max": 22.0,
            "rsi_long_max": 35.0,
            "rsi_short_min": 65.0,
        }
    }

    frequency, rejects = TradeFrequencyAnalyzer.prepare(
        frame,
        trades,
        config,
    )

    assert "executed_trades" in set(frequency["stage"])
    assert "position_open_or_margin_limit" in set(rejects["reason"])
    assert frequency.loc[
        frequency["stage"] == "executed_trades",
        "total_count",
    ].iloc[0] == 2
