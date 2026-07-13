from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Account:
    initial_balance: float
    balance: float
    equity: float
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    used_margin: float = 0.0
    free_margin: float = 0.0

    @classmethod
    def create(cls, initial_balance: float) -> "Account":
        if initial_balance <= 0:
            raise ValueError("initial_balance must be positive.")

        return cls(
            initial_balance=initial_balance,
            balance=initial_balance,
            equity=initial_balance,
            free_margin=initial_balance,
        )

    def reset(self) -> None:
        self.balance = self.initial_balance
        self.equity = self.initial_balance
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.used_margin = 0.0
        self.free_margin = self.initial_balance

    def update_margin(self, used_margin: float) -> None:
        if used_margin < 0:
            raise ValueError("used_margin cannot be negative.")
        if used_margin > self.equity + 1e-12:
            raise ValueError("used_margin cannot exceed equity.")

        self.used_margin = used_margin
        self.free_margin = self.equity - used_margin

    def apply_realized_pnl(self, pnl: float) -> None:
        self.realized_pnl += pnl
        self.balance += pnl
        self.update_equity(self.unrealized_pnl)

    def update_equity(self, unrealized_pnl: float = 0.0) -> None:
        self.unrealized_pnl = unrealized_pnl
        self.equity = self.balance + unrealized_pnl
        self.free_margin = self.equity - self.used_margin
