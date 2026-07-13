import pandas as pd

from nexus.reports.trade_frequency import TradeFrequencyAnalyzer


def test_trade_frequency_outputs_divergence_stages():
    frame = pd.DataFrame(
        {
            "long_setup": [True, False, False, False],
            "short_setup": [False, True, False, False],
            "long_band_touch": [True, False, True, False],
            "short_band_touch": [False, True, False, True],
        }
    )
    trades = pd.DataFrame([{"side": "LONG"}, {"side": "SHORT"}])
    frequency, rejects = TradeFrequencyAnalyzer.prepare(frame, trades, {})
    assert "confirmed_rsi_divergence" in set(frequency["stage"])
    assert "position_open_or_margin_limit" in set(rejects["reason"])
    assert frequency.loc[frequency.stage == "executed_trades", "total_count"].iloc[0] == 2
