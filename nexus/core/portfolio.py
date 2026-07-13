from __future__ import annotations

from dataclasses import dataclass

from nexus.core.account import Account
from nexus.core.position import Position, Side


@dataclass
class Portfolio:
    account: Account
    long_position: Position | None = None
    short_position: Position | None = None

    def get_position(self, side: Side) -> Position | None:
        return self.long_position if side == "LONG" else self.short_position

    def has_open_position(self, side: Side) -> bool:
        position = self.get_position(side)
        return position is not None and position.is_open

    def open_position(self, position: Position) -> None:
        if self.has_open_position(position.side):
            raise RuntimeError(f"{position.side} position is already open.")

        projected_margin = self.used_margin + position.margin_used
        if projected_margin > self.account.equity + 1e-12:
            raise ValueError("Insufficient equity for requested margin.")

        if position.side == "LONG":
            self.long_position = position
        else:
            self.short_position = position

        self.account.update_margin(projected_margin)

    def close_position(self, side: Side, realized_pnl: float) -> Position:
        position = self.get_position(side)
        if position is None:
            raise RuntimeError(f"No {side} position is open.")

        released_margin = position.margin_used
        position.close()

        if side == "LONG":
            self.long_position = None
        else:
            self.short_position = None

        self.account.apply_realized_pnl(realized_pnl)
        self.account.update_margin(max(0.0, self.used_margin - released_margin))
        return position

    def update_unrealized_pnl(
        self,
        long_unrealized_pnl: float = 0.0,
        short_unrealized_pnl: float = 0.0,
    ) -> None:
        self.account.update_equity(long_unrealized_pnl + short_unrealized_pnl)

    @property
    def used_margin(self) -> float:
        total = 0.0
        if self.long_position is not None and self.long_position.is_open:
            total += self.long_position.margin_used
        if self.short_position is not None and self.short_position.is_open:
            total += self.short_position.margin_used
        return total
