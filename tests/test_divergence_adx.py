import pandas as pd

from nexus.signals import _divergence_signals


def _frame(adx_at_signal: float) -> pd.DataFrame:
    n = 24
    frame = pd.DataFrame(
        {
            "low": [110.0] * n,
            "high": [120.0] * n,
            "rsi": [50.0] * n,
            "adx": [18.0] * n,
        }
    )
    frame.loc[2:8, "low"] = [108, 106, 104, 100, 104, 106, 108]
    frame.at[5, "rsi"] = 25.0
    frame.loc[11:15, "low"] = [105, 102, 99, 95, 101]
    frame.at[14, "rsi"] = 34.0
    frame.at[15, "adx"] = adx_at_signal
    return frame


def test_divergence_requires_adx_inside_range() -> None:
    accepted = _divergence_signals(
        _frame(25.0),
        "LONG",
        3,
        3,
        1,
        30.0,
        8.0,
        20.0,
        30.0,
    )
    below = _divergence_signals(
        _frame(19.0),
        "LONG",
        3,
        3,
        1,
        30.0,
        8.0,
        20.0,
        30.0,
    )
    above = _divergence_signals(
        _frame(31.0),
        "LONG",
        3,
        3,
        1,
        30.0,
        8.0,
        20.0,
        30.0,
    )

    assert accepted["setup"].any()
    assert not below["setup"].any()
    assert not above["setup"].any()
