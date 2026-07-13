from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


_REQUIRED_COLUMNS = ("open_time", "open", "high", "low", "close", "volume")
_PRICE_COLUMNS = ("open", "high", "low", "close", "volume")


def load_ohlcv_csv(path: Path) -> pd.DataFrame:
    """Load Binance/Gate-compatible OHLCV CSV data and validate it."""
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    frame = pd.read_csv(path)
    missing = [column for column in _REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(
            "CSV is missing required columns: " + ", ".join(missing)
        )

    frame = frame.loc[:, _REQUIRED_COLUMNS].copy()

    for column in _PRICE_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    timestamp_numeric = pd.to_numeric(frame["open_time"], errors="coerce")
    if timestamp_numeric.notna().all():
        unit = "ms" if float(timestamp_numeric.abs().median()) > 10_000_000_000 else "s"
        frame["timestamp"] = pd.to_datetime(
            timestamp_numeric, unit=unit, utc=True, errors="coerce"
        )
    else:
        frame["timestamp"] = pd.to_datetime(
            frame["open_time"], utc=True, errors="coerce"
        )

    frame.replace([np.inf, -np.inf], np.nan, inplace=True)
    frame.dropna(subset=["timestamp", *_PRICE_COLUMNS], inplace=True)
    frame.sort_values("timestamp", inplace=True)
    frame.drop_duplicates(subset=["timestamp"], keep="last", inplace=True)
    frame.reset_index(drop=True, inplace=True)

    if frame.empty:
        raise ValueError("CSV contains no valid OHLCV rows.")

    invalid = (
        (frame["high"] < frame[["open", "close", "low"]].max(axis=1))
        | (frame["low"] > frame[["open", "close", "high"]].min(axis=1))
        | (frame["volume"] < 0)
    )
    if invalid.any():
        count = int(invalid.sum())
        raise ValueError(f"CSV contains {count} invalid OHLCV rows.")

    return frame[
        ["timestamp", "open", "high", "low", "close", "volume"]
    ].copy()
