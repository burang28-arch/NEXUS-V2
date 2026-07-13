from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Side = Literal["LONG", "SHORT"]


@dataclass(frozen=True)
class Fill:
    price: float
    notional: float
    fee: float


class BacktestBroker:
    """Deterministic fee and slippage model used by the backtester."""

    def __init__(self, fee_rate_pct: float, slippage_rate_pct: float) -> None:
        if fee_rate_pct < 0:
            raise ValueError("fee_rate_pct cannot be negative.")
        if slippage_rate_pct < 0:
            raise ValueError("slippage_rate_pct cannot be negative.")

        self.fee_rate = fee_rate_pct / 100.0
        self.slippage_rate = slippage_rate_pct / 100.0

    def entry_fill(self, raw_price: float, side: Side, notional: float) -> Fill:
        self._validate(raw_price, notional)
        if side == "LONG":
            price = raw_price * (1.0 + self.slippage_rate)
        else:
            price = raw_price * (1.0 - self.slippage_rate)
        return Fill(price=price, notional=notional, fee=self.fee(notional))

    def limit_entry_fill(
        self,
        fill_price: float,
        side: Side,
        notional: float,
    ) -> Fill:
        """
        Fill a touched limit order at the supplied price.

        The caller may pass the limit price or a better opening price when the
        candle gaps through the limit. No additional adverse slippage is added
        to a limit entry.
        """
        self._validate(fill_price, notional)
        return Fill(
            price=fill_price,
            notional=notional,
            fee=self.fee(notional),
        )

    def exit_fill(
        self,
        raw_price: float,
        side: Side,
        quantity: float,
    ) -> Fill:
        if raw_price <= 0:
            raise ValueError("raw_price must be positive.")
        if quantity <= 0:
            raise ValueError("quantity must be positive.")

        if side == "LONG":
            price = raw_price * (1.0 - self.slippage_rate)
        else:
            price = raw_price * (1.0 + self.slippage_rate)

        notional = abs(price * quantity)
        return Fill(price=price, notional=notional, fee=self.fee(notional))

    def fee(self, notional: float) -> float:
        if notional < 0:
            raise ValueError("notional cannot be negative.")
        return notional * self.fee_rate

    @staticmethod
    def _validate(raw_price: float, notional: float) -> None:
        if raw_price <= 0:
            raise ValueError("raw_price must be positive.")
        if notional <= 0:
            raise ValueError("notional must be positive.")
