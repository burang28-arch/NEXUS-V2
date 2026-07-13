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


def _pivot_mask(series: pd.Series, left: int, right: int, mode: str) -> pd.Series:
    """Return pivot locations without shifting them to confirmation time."""
    if left < 1 or right < 1:
        raise ValueError("Pivot left/right bars must be at least 1.")
    window = left + right + 1
    rolling = series.rolling(window, center=True, min_periods=window)
    extreme = rolling.min() if mode == "low" else rolling.max()
    return series.eq(extreme).fillna(False)


def _divergence_signals(
    frame: pd.DataFrame,
    side: str,
    left: int,
    l1_right: int,
    l2_right: int,
    l1_rsi_threshold: float,
    min_rsi_difference: float,
    require_band_touch: bool,
) -> pd.DataFrame:
    """
    Pair each fast-confirmed L2 pivot with the most recent eligible L1 pivot.

    L1 uses left/l1_right confirmation. L2 uses left/l2_right confirmation.
    The signal is placed on the L2 confirmation candle, so a backtester that
    enters on the next candle open remains look-ahead safe.
    """
    is_long = side == "LONG"
    price_col = "low" if is_long else "high"
    mode = "low" if is_long else "high"
    band_col = "bb_lower" if is_long else "bb_upper"

    l1_mask = _pivot_mask(frame[price_col], left, l1_right, mode)
    l2_mask = _pivot_mask(frame[price_col], left, l2_right, mode)

    output = pd.DataFrame(index=frame.index)
    output["setup"] = False
    output["l1_index"] = np.nan
    output["l2_index"] = np.nan
    output["l1_price"] = np.nan
    output["l2_price"] = np.nan
    output["l1_rsi"] = np.nan
    output["l2_rsi"] = np.nan
    output["rsi_difference"] = np.nan
    output["band_touch"] = False

    eligible_l1: list[int] = []
    l1_indices = list(frame.index[l1_mask])
    l2_indices = list(frame.index[l2_mask])
    l1_pointer = 0

    for l2_index in l2_indices:
        signal_index = l2_index + l2_right
        if signal_index >= len(frame):
            continue

        # Only L1 pivots confirmed by the current signal candle may be used.
        while l1_pointer < len(l1_indices):
            candidate = l1_indices[l1_pointer]
            confirmation = candidate + l1_right
            if confirmation > signal_index:
                break
            if candidate < l2_index:
                rsi = frame.at[candidate, "rsi"]
                threshold_ok = (
                    pd.notna(rsi)
                    and (rsi <= l1_rsi_threshold if is_long else rsi >= l1_rsi_threshold)
                )
                if threshold_ok:
                    eligible_l1.append(candidate)
            l1_pointer += 1

        if not eligible_l1:
            continue

        l1_index = eligible_l1[-1]
        l1_price = float(frame.at[l1_index, price_col])
        l2_price = float(frame.at[l2_index, price_col])
        l1_rsi = float(frame.at[l1_index, "rsi"])
        l2_rsi = float(frame.at[l2_index, "rsi"])
        if not np.isfinite(l2_rsi):
            continue

        price_condition = l2_price < l1_price if is_long else l2_price > l1_price
        rsi_difference = l2_rsi - l1_rsi if is_long else l1_rsi - l2_rsi
        rsi_condition = rsi_difference >= min_rsi_difference
        band_touch = (
            float(frame.at[l2_index, price_col]) <= float(frame.at[l2_index, band_col])
            if is_long
            else float(frame.at[l2_index, price_col]) >= float(frame.at[l2_index, band_col])
        )
        band_condition = band_touch if require_band_touch else True

        if not (price_condition and rsi_condition and band_condition):
            continue

        output.at[signal_index, "setup"] = True
        output.at[signal_index, "l1_index"] = l1_index
        output.at[signal_index, "l2_index"] = l2_index
        output.at[signal_index, "l1_price"] = l1_price
        output.at[signal_index, "l2_price"] = l2_price
        output.at[signal_index, "l1_rsi"] = l1_rsi
        output.at[signal_index, "l2_rsi"] = l2_rsi
        output.at[signal_index, "rsi_difference"] = rsi_difference
        output.at[signal_index, "band_touch"] = bool(band_touch)

    return output


def add_signal_columns(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    result = frame.copy()
    entry_cfg = config["entry"]
    scoring_cfg = config["scoring"]

    left = int(entry_cfg["pivot_left_bars"])
    l1_right = int(entry_cfg["l1_right_bars"])
    l2_right = int(entry_cfg["l2_right_bars"])
    min_rsi_difference = float(entry_cfg["min_rsi_difference"])
    require_band_touch = bool(entry_cfg.get("require_band_touch", True))

    components = _candle_components(result)
    body = components["body"]
    candle_range = components["range"]
    upper_wick = components["upper_wick"]
    lower_wick = components["lower_wick"]
    prev_open = result["open"].shift(1)
    prev_close = result["close"].shift(1)

    result["bullish_engulfing"] = (
        (prev_close < prev_open) & (result["close"] > result["open"])
        & (result["open"] <= prev_close) & (result["close"] >= prev_open)
    )
    result["bearish_engulfing"] = (
        (prev_close > prev_open) & (result["close"] < result["open"])
        & (result["open"] >= prev_close) & (result["close"] <= prev_open)
    )
    result["long_lower_wick"] = (
        (lower_wick >= body * 1.5) & (upper_wick <= body)
        & (result["close"] >= result["low"] + candle_range * 0.6)
        & (body >= candle_range * 0.15)
    )
    result["long_upper_wick"] = (
        (upper_wick >= body * 1.5) & (lower_wick <= body)
        & (result["close"] <= result["low"] + candle_range * 0.4)
        & (body >= candle_range * 0.15)
    )
    result["long_candle_confirm"] = result["bullish_engulfing"] | result["long_lower_wick"]
    result["short_candle_confirm"] = result["bearish_engulfing"] | result["long_upper_wick"]
    result["volume_score"] = (result["volume"] > result["volume_ma"]).astype("int8")
    result["long_candle_score"] = result["long_candle_confirm"].astype("int8")
    result["short_candle_score"] = result["short_candle_confirm"].astype("int8")

    long_div = _divergence_signals(
        result, "LONG", left, l1_right, l2_right,
        float(entry_cfg["l1_rsi_long_max"]), min_rsi_difference,
        require_band_touch,
    )
    short_div = _divergence_signals(
        result, "SHORT", left, l1_right, l2_right,
        float(entry_cfg["l1_rsi_short_min"]), min_rsi_difference,
        require_band_touch,
    )

    result["long_setup"] = long_div["setup"].astype(bool)
    result["short_setup"] = short_div["setup"].astype(bool)
    for prefix, source in (("long", long_div), ("short", short_div)):
        for column in (
            "l1_index", "l2_index", "l1_price", "l2_price",
            "l1_rsi", "l2_rsi", "rsi_difference", "band_touch",
        ):
            result[f"{prefix}_{column}"] = source[column]

    result["long_score"] = (
        result["volume_score"] + result["long_candle_score"]
    ).where(result["long_setup"], 0).astype("int8")
    result["short_score"] = (
        result["volume_score"] + result["short_candle_score"]
    ).where(result["short_setup"], 0).astype("int8")

    size_map = {int(k): float(v) for k, v in scoring_cfg["size_multipliers"].items()}
    result["long_size_multiplier"] = result["long_score"].map(size_map).where(result["long_setup"])
    result["short_size_multiplier"] = result["short_score"].map(size_map).where(result["short_setup"])
    result["long_stop"] = np.nan
    result["short_stop"] = np.nan

    result["signal"] = np.select(
        [result["long_setup"], result["short_setup"]], ["LONG", "SHORT"], default=""
    )
    result["score"] = np.select(
        [result["long_setup"], result["short_setup"]],
        [result["long_score"], result["short_score"]], default=0,
    ).astype("int8")
    result["size_multiplier"] = np.select(
        [result["long_setup"], result["short_setup"]],
        [result["long_size_multiplier"], result["short_size_multiplier"]],
        default=np.nan,
    )
    result["stop_price"] = np.nan
    result["signal_reason"] = np.select(
        [result["long_setup"], result["short_setup"]],
        [
            "Bullish RSI divergence + BB lower touch",
            "Bearish RSI divergence + BB upper touch",
        ], default="",
    )
    result["divergence_l1_price"] = np.select(
        [result["long_setup"], result["short_setup"]],
        [result["long_l1_price"], result["short_l1_price"]], default=np.nan,
    )
    result["divergence_l2_price"] = np.select(
        [result["long_setup"], result["short_setup"]],
        [result["long_l2_price"], result["short_l2_price"]], default=np.nan,
    )
    result["divergence_l1_rsi"] = np.select(
        [result["long_setup"], result["short_setup"]],
        [result["long_l1_rsi"], result["short_l1_rsi"]], default=np.nan,
    )
    result["divergence_l2_rsi"] = np.select(
        [result["long_setup"], result["short_setup"]],
        [result["long_l2_rsi"], result["short_l2_rsi"]], default=np.nan,
    )
    result["divergence_rsi_difference"] = np.select(
        [result["long_setup"], result["short_setup"]],
        [result["long_rsi_difference"], result["short_rsi_difference"]], default=np.nan,
    )
    result["band_touch"] = np.select(
        [result["long_setup"], result["short_setup"]],
        [result["long_band_touch"], result["short_band_touch"]], default=False,
    ).astype(bool)
    return result


def extract_signals(frame: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "timestamp", "signal", "signal_reason", "open", "high", "low", "close",
        "volume", "adx", "rsi", "atr", "bb_lower", "bb_middle", "bb_upper",
        "volume_score", "long_candle_score", "short_candle_score", "score",
        "size_multiplier", "stop_price", "divergence_l1_price",
        "divergence_l2_price", "divergence_l1_rsi", "divergence_l2_rsi",
        "divergence_rsi_difference", "band_touch",
    ]
    return frame.loc[frame["signal"] != "", columns].copy()
