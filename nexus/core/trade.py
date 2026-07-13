from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd


Side = Literal["LONG", "SHORT"]


@dataclass(frozen=True)
class TradeRecord:
    side: Side
    signal_time: pd.Timestamp
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry_price: float
    stop_price: float
    tp1_price: float
    tp2_price: float
    exit_price: float
    exit_reason: str
    score: int
    size_multiplier: float
    margin_used: float
    notional: float
    quantity: float
    gross_pnl: float
    fees: float
    net_pnl: float
    return_on_margin_pct: float
    holding_bars: int
    adx: float
    rsi: float
    atr: float
    volume_score: int
    candle_score: int
