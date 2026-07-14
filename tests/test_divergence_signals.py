import pandas as pd
from nexus.signals import _divergence_signals


def _frame(adx_at_signal: float = 18.0):
    n = 24
    frame = pd.DataFrame({
        "low": [110.0] * n,
        "high": [120.0] * n,
        "rsi": [50.0] * n,
        "adx": [18.0] * n,
    })
    frame.loc[2:8, "low"] = [108, 106, 104, 100, 104, 106, 108]
    frame.at[5, "rsi"] = 25.0
    frame.loc[11:15, "low"] = [105, 102, 99, 95, 101]
    frame.at[14, "rsi"] = 34.0
    frame.at[15, "adx"] = adx_at_signal
    return frame


def test_bullish_divergence_signal_uses_l1_3_right_l2_1_right():
    result = _divergence_signals(_frame(), "LONG", 3, 3, 1, 30.0, 8.0, 0.0, 22.0)
    assert bool(result.at[15, "setup"])
    assert result.at[15, "l1_price"] == 100.0
    assert result.at[15, "l2_price"] == 95.0
    assert result.at[15, "rsi_difference"] == 9.0
    assert result.at[15, "adx_value"] == 18.0


def test_adx_above_threshold_rejects_signal():
    result = _divergence_signals(_frame(23.0), "LONG", 3, 3, 1, 30.0, 8.0, 0.0, 22.0)
    assert not bool(result["setup"].any())
