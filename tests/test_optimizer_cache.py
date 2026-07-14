import pandas as pd

from nexus.optimizer import (
    _cached_enriched_frame,
    _indicator_cache_key,
    _signal_cache_key,
    recommended_workers,
)


def _config() -> dict:
    return {
        "indicators": {
            "rsi": {"length": 2},
            "adx": {"length": 2},
            "bollinger": {"length": 2, "stddev": 2.0},
            "atr": {"length": 2},
            "volume": {"ma_length": 2},
            "swing": {"left_bars": 1, "right_bars": 1},
        },
        "entry": {
            "strategy": "rsi_divergence",
            "l1_rsi_long_max": 30.0,
            "l1_rsi_short_min": 70.0,
            "min_rsi_difference": 8.0,
            "pivot_left_bars": 1,
            "l1_right_bars": 1,
            "l2_right_bars": 1,
            "adx_min": 0.0,
            "adx_max": 60.0,
        },
        "scoring": {
            "size_multipliers": {0: 0.5, 1: 1.0, 2: 1.5},
        },
    }


def _market() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.date_range(
                "2026-01-01", periods=10, freq="15min", tz="UTC"
            ),
            "open": [100.0] * 10,
            "high": [101.0] * 10,
            "low": [99.0] * 10,
            "close": [100.0] * 10,
            "volume": [100.0] * 10,
        }
    )


def test_indicator_and_signal_cache_keys_change_only_when_needed() -> None:
    first = _config()
    second = _config()
    second["risk"] = {"stop_loss_pct": 2.0}

    assert _indicator_cache_key(first) == _indicator_cache_key(second)
    assert _signal_cache_key(first) == _signal_cache_key(second)

    second["entry"]["adx_max"] = 50.0
    assert _signal_cache_key(first) != _signal_cache_key(second)


def test_cached_enriched_frame_reports_hits() -> None:
    indicator_cache = {}
    signal_cache = {}

    _, first_indicator_hit, first_signal_hit = _cached_enriched_frame(
        _market(), _config(), indicator_cache, signal_cache
    )
    _, second_indicator_hit, second_signal_hit = _cached_enriched_frame(
        _market(), _config(), indicator_cache, signal_cache
    )

    assert not first_indicator_hit
    assert not first_signal_hit
    assert second_indicator_hit
    assert second_signal_hit


def test_recommended_workers_is_positive_and_bounded() -> None:
    assert 1 <= recommended_workers() <= 10
