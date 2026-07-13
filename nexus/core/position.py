from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal

import pandas as pd


Side = Literal["LONG", "SHORT"]


class PositionState(str, Enum):
    OPEN = "OPEN"
    TP1_DONE = "TP1_DONE"
    CLOSED = "CLOSED"


@dataclass
class Position:
    side: Side
    signal_index: int
    entry_index: int
    entry_time: pd.Timestamp
    entry_price: float
    stop_price: float
    tp1_price: float
    tp2_price: float
    score: int
    size_multiplier: float
    margin_used: float
    notional: float
    quantity: float
    fee_open: float
    remaining_fraction: float = 1.0
    realized_pnl: float = 0.0
    holding_bars: int = 0
    state: PositionState = PositionState.OPEN

    @property
    def is_open(self) -> bool:
        return self.state is not PositionState.CLOSED

    @property
    def tp1_done(self) -> bool:
        return self.state is PositionState.TP1_DONE

    def mark_tp1_done(self) -> None:
        if self.state is PositionState.CLOSED:
            raise RuntimeError("Cannot mark TP1 on a closed position.")
        self.state = PositionState.TP1_DONE

    def close(self) -> None:
        self.remaining_fraction = 0.0
        self.state = PositionState.CLOSED

    def reduce(self, fraction: float) -> None:
        if self.state is PositionState.CLOSED:
            raise RuntimeError("Cannot reduce a closed position.")
        if fraction <= 0:
            raise ValueError("Reduction fraction must be positive.")
        if fraction > self.remaining_fraction + 1e-12:
            raise ValueError("Reduction fraction exceeds remaining position.")

        self.remaining_fraction = max(0.0, self.remaining_fraction - fraction)
        if self.remaining_fraction <= 1e-12:
            self.close()

    def increase_holding_bars(self) -> None:
        self.holding_bars += 1

    def gross_pnl(self, exit_price: float, fraction: float) -> float:
        if fraction <= 0:
            raise ValueError("PnL fraction must be positive.")
        if fraction > self.remaining_fraction + 1e-12:
            raise ValueError("PnL fraction exceeds remaining position.")

        quantity = self.quantity * fraction
        if self.side == "LONG":
            return (exit_price - self.entry_price) * quantity
        return (self.entry_price - exit_price) * quantity
