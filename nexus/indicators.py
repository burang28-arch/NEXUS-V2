from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _wilder_smoothing(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()


def calculate_rsi(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    average_gain = _wilder_smoothing(gain, length)
    average_loss = _wilder_smoothing(loss, length)

    relative_strength = average_gain / average_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + relative_strength))

    rsi = rsi.where(average_loss != 0.0, 100.0)
    rsi = rsi.where(average_gain != 0.0, 0.0)
    both_zero = (average_gain == 0.0) & (average_loss == 0.0)
    return rsi.where(~both_zero, 50.0)


def calculate_true_range(frame: pd.DataFrame) -> pd.Series:
    previous_close = frame["close"].shift(1)
    return pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)


def calculate_atr(frame: pd.DataFrame, length: int = 14) -> pd.Series:
    return _wilder_smoothing(calculate_true_range(frame), length)


def calculate_adx(
    frame: pd.DataFrame, length: int = 14
) -> tuple[pd.Series, pd.Series, pd.Series]:
    upward_move = frame["high"].diff()
    downward_move = -frame["low"].diff()

    plus_dm = pd.Series(
        np.where(
            (upward_move > downward_move) & (upward_move > 0.0),
            upward_move,
            0.0,
        ),
        index=frame.index,
        dtype=float,
    )
    minus_dm = pd.Series(
        np.where(
            (downward_move > upward_move) & (downward_move > 0.0),
            downward_move,
            0.0,
        ),
        index=frame.index,
        dtype=float,
    )

    atr = calculate_atr(frame, length)
    plus_di = 100.0 * _wilder_smoothing(plus_dm, length) / atr.replace(0.0, np.nan)
    minus_di = 100.0 * _wilder_smoothing(minus_dm, length) / atr.replace(0.0, np.nan)

    denominator = (plus_di + minus_di).replace(0.0, np.nan)
    directional_index = 100.0 * (plus_di - minus_di).abs() / denominator
    adx = _wilder_smoothing(directional_index, length)
    return adx, plus_di, minus_di


def calculate_bollinger(
    close: pd.Series,
    length: int = 20,
    stddev: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    middle = close.rolling(length, min_periods=length).mean()
    deviation = close.rolling(length, min_periods=length).std(ddof=0)
    upper = middle + deviation * stddev
    lower = middle - deviation * stddev
    return lower, middle, upper


def calculate_swings(
    frame: pd.DataFrame,
    left_bars: int = 2,
    right_bars: int = 2,
) -> tuple[pd.Series, pd.Series]:
    """
    Confirmed pivot values.

    A pivot at candle i becomes usable only after right_bars candles have closed.
    The returned value is forward-filled from that confirmation point to avoid
    look-ahead bias in later backtests.
    """
    window = left_bars + right_bars + 1
    centered_low = frame["low"].rolling(window, center=True).min()
    centered_high = frame["high"].rolling(window, center=True).max()

    pivot_low = frame["low"].where(frame["low"].eq(centered_low))
    pivot_high = frame["high"].where(frame["high"].eq(centered_high))

    confirmed_low = pivot_low.shift(right_bars).ffill()
    confirmed_high = pivot_high.shift(right_bars).ffill()
    return confirmed_low, confirmed_high


def add_indicators(
    frame: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    result = frame.copy()
    indicator_config = config["indicators"]

    rsi_length = int(indicator_config["rsi"]["length"])
    atr_length = int(indicator_config["atr"]["length"])
    adx_length = int(indicator_config["adx"]["length"])
    bb_length = int(indicator_config["bollinger"]["length"])
    bb_stddev = float(indicator_config["bollinger"]["stddev"])
    volume_length = int(indicator_config["volume"]["ma_length"])
    left_bars = int(indicator_config["swing"]["left_bars"])
    right_bars = int(indicator_config["swing"]["right_bars"])

    result["rsi"] = calculate_rsi(result["close"], rsi_length)
    result["atr"] = calculate_atr(result, atr_length)
    result["adx"], result["plus_di"], result["minus_di"] = calculate_adx(
        result, adx_length
    )
    (
        result["bb_lower"],
        result["bb_middle"],
        result["bb_upper"],
    ) = calculate_bollinger(result["close"], bb_length, bb_stddev)
    result["volume_ma"] = result["volume"].rolling(
        volume_length,
        min_periods=volume_length,
    ).mean()
    result["swing_low"], result["swing_high"] = calculate_swings(
        result,
        left_bars,
        right_bars,
    )
    return result
