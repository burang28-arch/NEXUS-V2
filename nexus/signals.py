from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _candle_components(frame: pd.DataFrame) -> pd.DataFrame:
    result = pd.DataFrame(index=frame.index)
    result["body"] = (frame["close"] - frame["open"]).abs()
    result["range"] = (frame["high"] - frame["low"]).replace(0.0, np.nan)
    result["upper_wick"] = frame["high"] - frame[["open", "close"]].max(axis=1)
    result["lower_wick"] = frame[["open", "close"]].min(axis=1) - frame["low"]
    return result


def add_signal_columns(
    frame: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    """
    Add long/short setup flags, score components, position multiplier,
    and structure-based stop prices.

    Signals are calculated on the completed candle. A later backtester
    should enter on the next candle open to avoid look-ahead bias.
    """
    result = frame.copy()

    entry_cfg = config["entry"]
    scoring_cfg = config["scoring"]
    risk_cfg = config["risk"]

    adx_max = float(entry_cfg["adx_max"])
    rsi_long_max = float(entry_cfg["rsi_long_max"])
    rsi_short_min = float(entry_cfg["rsi_short_min"])

    components = _candle_components(result)
    body = components["body"]
    candle_range = components["range"]
    upper_wick = components["upper_wick"]
    lower_wick = components["lower_wick"]

    prev_open = result["open"].shift(1)
    prev_close = result["close"].shift(1)

    result["bullish_engulfing"] = (
        (prev_close < prev_open)
        & (result["close"] > result["open"])
        & (result["open"] <= prev_close)
        & (result["close"] >= prev_open)
    )

    result["bearish_engulfing"] = (
        (prev_close > prev_open)
        & (result["close"] < result["open"])
        & (result["open"] >= prev_close)
        & (result["close"] <= prev_open)
    )

    result["long_lower_wick"] = (
        (lower_wick >= body * 1.5)
        & (upper_wick <= body)
        & (result["close"] >= result["low"] + candle_range * 0.6)
        & (body >= candle_range * 0.15)
    )

    result["long_upper_wick"] = (
        (upper_wick >= body * 1.5)
        & (lower_wick <= body)
        & (result["close"] <= result["low"] + candle_range * 0.4)
        & (body >= candle_range * 0.15)
    )

    result["long_candle_confirm"] = (
        result["bullish_engulfing"] | result["long_lower_wick"]
    )
    result["short_candle_confirm"] = (
        result["bearish_engulfing"] | result["long_upper_wick"]
    )

    result["volume_score"] = (
        result["volume"] > result["volume_ma"]
    ).astype("int8")

    result["long_candle_score"] = result["long_candle_confirm"].astype("int8")
    result["short_candle_score"] = result["short_candle_confirm"].astype("int8")

    valid_common = (
        result["adx"].notna()
        & result["rsi"].notna()
        & result["bb_lower"].notna()
        & result["bb_upper"].notna()
        & result["atr"].notna()
    )

    result["long_setup"] = (
        valid_common
        & (result["adx"] <= adx_max)
        & (result["rsi"] <= rsi_long_max)
        & (result["low"] <= result["bb_lower"])
    )

    result["short_setup"] = (
        valid_common
        & (result["adx"] <= adx_max)
        & (result["rsi"] >= rsi_short_min)
        & (result["high"] >= result["bb_upper"])
    )

    result["long_score"] = (
        result["volume_score"] + result["long_candle_score"]
    ).where(result["long_setup"], 0).astype("int8")

    result["short_score"] = (
        result["volume_score"] + result["short_candle_score"]
    ).where(result["short_setup"], 0).astype("int8")

    size_map = {
        int(score): float(multiplier)
        for score, multiplier in scoring_cfg["size_multipliers"].items()
    }

    result["long_size_multiplier"] = (
        result["long_score"].map(size_map).where(result["long_setup"])
    )
    result["short_size_multiplier"] = (
        result["short_score"].map(size_map).where(result["short_setup"])
    )

    # Actual stop and target prices depend on the next candle entry fill.
    # They are calculated in the backtest engine from configurable percentages.
    result["long_stop"] = np.nan
    result["short_stop"] = np.nan

    result["signal"] = np.select(
        [result["long_setup"], result["short_setup"]],
        ["LONG", "SHORT"],
        default="",
    )

    result["score"] = np.select(
        [result["long_setup"], result["short_setup"]],
        [result["long_score"], result["short_score"]],
        default=0,
    ).astype("int8")

    result["size_multiplier"] = np.select(
        [result["long_setup"], result["short_setup"]],
        [result["long_size_multiplier"], result["short_size_multiplier"]],
        default=np.nan,
    )

    result["stop_price"] = np.select(
        [result["long_setup"], result["short_setup"]],
        [result["long_stop"], result["short_stop"]],
        default=np.nan,
    )

    result["signal_reason"] = np.select(
        [result["long_setup"], result["short_setup"]],
        [
            "ADX range + RSI oversold + BB lower touch",
            "ADX range + RSI overbought + BB upper touch",
        ],
        default="",
    )

    return result


def extract_signals(frame: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "timestamp",
        "signal",
        "signal_reason",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "adx",
        "rsi",
        "atr",
        "bb_lower",
        "bb_middle",
        "bb_upper",
        "swing_low",
        "swing_high",
        "volume_score",
        "long_candle_score",
        "short_candle_score",
        "score",
        "size_multiplier",
        "stop_price",
    ]
    return frame.loc[frame["signal"] != "", columns].copy()
