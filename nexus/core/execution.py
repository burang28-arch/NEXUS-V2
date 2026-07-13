from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from nexus.core.broker import BacktestBroker
from nexus.core.position import Position
from nexus.core.trade import TradeRecord


@dataclass
class ExecutionResult:
    position: Position | None
    trade: TradeRecord | None


class ExecutionEngine:
    """
    Position bar-processing interface.

    DEV6 only introduces the interface.
    Existing backtest execution logic remains unchanged.
    """

    def process_position(
        self,
        handler: Any,
        position: Position,
        bar: pd.Series,
        signal_row: pd.Series,
        config: dict[str, Any],
        broker: BacktestBroker,
    ) -> ExecutionResult:
        updated_position, trade = handler(
            position,
            bar,
            signal_row,
            config,
            broker,
        )
        return ExecutionResult(
            position=updated_position,
            trade=trade,
        )
