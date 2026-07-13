from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

import numpy as np
import pandas as pd

from nexus.core.broker import BacktestBroker


Side = Literal["LONG", "SHORT"]


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
    tp1_done: bool = False
    realized_pnl: float = 0.0
    exit_reason: str = ""
    exit_time: pd.Timestamp | None = None
    exit_price: float | None = None
    holding_bars: int = 0


@dataclass
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


def _pnl_for_fraction(position: Position, exit_price: float, fraction: float) -> float:
    qty = position.quantity * fraction
    if position.side == "LONG":
        return (exit_price - position.entry_price) * qty
    return (position.entry_price - exit_price) * qty


def _close_fraction(
    position: Position,
    exit_price: float,
    fraction: float,
    broker: BacktestBroker,
) -> tuple[float, float]:
    gross = _pnl_for_fraction(position, exit_price, fraction)
    close_notional = abs(position.quantity * fraction * exit_price)
    close_fee = broker.fee(close_notional)
    position.realized_pnl += gross - close_fee
    position.remaining_fraction -= fraction
    return gross, close_fee


def _position_margin_pct(config: dict[str, Any], size_multiplier: float) -> float:
    return float(config["risk"]["base_margin_pct"]) * size_multiplier


def _build_position(
    side: Side,
    signal_row: pd.Series,
    entry_row: pd.Series,
    signal_index: int,
    entry_index: int,
    equity: float,
    config: dict[str, Any],
    broker: BacktestBroker,
) -> Position | None:
    leverage = float(config["risk"].get("leverage", 1.0))
    tp1_fraction = float(config["exit"]["tp1_fraction"])

    score = int(signal_row["score"])
    size_multiplier = float(signal_row["size_multiplier"])
    stop_price = float(signal_row["stop_price"])

    if not np.isfinite(stop_price):
        return None

    raw_entry = float(entry_row["open"])
    margin_pct = _position_margin_pct(config, size_multiplier)
    margin_used = equity * margin_pct / 100.0
    notional = margin_used * leverage
    if margin_used <= 0 or notional <= 0:
        return None

    entry_fill = broker.entry_fill(raw_entry, side, notional)
    entry_price = entry_fill.price

    if side == "LONG":
        tp1_price = float(signal_row["bb_middle"])
        tp2_price = float(signal_row["bb_upper"])
        if not (stop_price < entry_price and tp1_price > entry_price and tp2_price > entry_price):
            return None
    else:
        tp1_price = float(signal_row["bb_middle"])
        tp2_price = float(signal_row["bb_lower"])
        if not (stop_price > entry_price and tp1_price < entry_price and tp2_price < entry_price):
            return None

    quantity = notional / entry_price
    fee_open = entry_fill.fee

    return Position(
        side=side,
        signal_index=signal_index,
        entry_index=entry_index,
        entry_time=entry_row["timestamp"],
        entry_price=entry_price,
        stop_price=stop_price,
        tp1_price=tp1_price,
        tp2_price=tp2_price,
        score=score,
        size_multiplier=size_multiplier,
        margin_used=margin_used,
        notional=notional,
        quantity=quantity,
        fee_open=fee_open,
        realized_pnl=-fee_open,
    )


def _finalize_trade(
    position: Position,
    signal_row: pd.Series,
    exit_time: pd.Timestamp,
    exit_price: float,
    exit_reason: str,
    total_fees: float,
) -> TradeRecord:
    gross_pnl = position.realized_pnl + total_fees
    net_pnl = position.realized_pnl
    return TradeRecord(
        side=position.side,
        signal_time=signal_row["timestamp"],
        entry_time=position.entry_time,
        exit_time=exit_time,
        entry_price=position.entry_price,
        stop_price=position.stop_price,
        tp1_price=position.tp1_price,
        tp2_price=position.tp2_price,
        exit_price=exit_price,
        exit_reason=exit_reason,
        score=position.score,
        size_multiplier=position.size_multiplier,
        margin_used=position.margin_used,
        notional=position.notional,
        quantity=position.quantity,
        gross_pnl=gross_pnl,
        fees=total_fees,
        net_pnl=net_pnl,
        return_on_margin_pct=(net_pnl / position.margin_used * 100.0) if position.margin_used else 0.0,
        holding_bars=position.holding_bars,
        adx=float(signal_row["adx"]),
        rsi=float(signal_row["rsi"]),
        atr=float(signal_row["atr"]),
        volume_score=int(signal_row["volume_score"]),
        candle_score=int(
            signal_row["long_candle_score"]
            if position.side == "LONG"
            else signal_row["short_candle_score"]
        ),
    )


def _process_position_bar(
    position: Position,
    bar: pd.Series,
    signal_row: pd.Series,
    config: dict[str, Any],
    broker: BacktestBroker,
) -> tuple[Position | None, TradeRecord | None]:
    """
    Conservative same-bar assumption:
    if stop and profit target are both touched in one candle, stop is processed first.
    """
    tp1_fraction = float(config["exit"]["tp1_fraction"])
    tp2_fraction = float(config["exit"]["tp2_fraction"])

    position.holding_bars += 1
    total_fees = position.fee_open

    if position.side == "LONG":
        if float(bar["low"]) <= position.stop_price:
            exit_price = broker.exit_fill(position.stop_price, "LONG", position.quantity * position.remaining_fraction).price
            _, close_fee = _close_fraction(
                position, exit_price, position.remaining_fraction, broker
            )
            total_fees += close_fee
            trade = _finalize_trade(
                position, signal_row, bar["timestamp"], exit_price, "STOP", total_fees
            )
            return None, trade

        if (not position.tp1_done) and float(bar["high"]) >= position.tp1_price:
            exit_price = broker.exit_fill(position.tp1_price, "LONG", position.quantity * tp1_fraction).price
            _, close_fee = _close_fraction(position, exit_price, tp1_fraction, broker)
            total_fees += close_fee
            position.tp1_done = True

        if position.tp1_done and float(bar["high"]) >= position.tp2_price:
            exit_price = broker.exit_fill(position.tp2_price, "LONG", position.quantity * position.remaining_fraction).price
            _, close_fee = _close_fraction(
                position, exit_price, position.remaining_fraction, broker
            )
            total_fees += close_fee
            trade = _finalize_trade(
                position, signal_row, bar["timestamp"], exit_price, "TP2", total_fees
            )
            return None, trade

    else:
        if float(bar["high"]) >= position.stop_price:
            exit_price = broker.exit_fill(position.stop_price, "SHORT", position.quantity * position.remaining_fraction).price
            _, close_fee = _close_fraction(
                position, exit_price, position.remaining_fraction, broker
            )
            total_fees += close_fee
            trade = _finalize_trade(
                position, signal_row, bar["timestamp"], exit_price, "STOP", total_fees
            )
            return None, trade

        if (not position.tp1_done) and float(bar["low"]) <= position.tp1_price:
            exit_price = broker.exit_fill(position.tp1_price, "SHORT", position.quantity * tp1_fraction).price
            _, close_fee = _close_fraction(position, exit_price, tp1_fraction, broker)
            total_fees += close_fee
            position.tp1_done = True

        if position.tp1_done and float(bar["low"]) <= position.tp2_price:
            exit_price = broker.exit_fill(position.tp2_price, "SHORT", position.quantity * position.remaining_fraction).price
            _, close_fee = _close_fraction(
                position, exit_price, position.remaining_fraction, broker
            )
            total_fees += close_fee
            trade = _finalize_trade(
                position, signal_row, bar["timestamp"], exit_price, "TP2", total_fees
            )
            return None, trade

    return position, None


def run_backtest(
    frame: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    equity = float(config["risk"]["initial_equity"])
    max_total_margin_pct = float(config["risk"].get("max_total_margin_pct", 6.0))
    broker = BacktestBroker(
        fee_rate_pct=float(config["risk"]["fee_rate_pct"]),
        slippage_rate_pct=float(config["risk"]["slippage_rate_pct"]),
    )

    long_position: Position | None = None
    short_position: Position | None = None
    records: list[TradeRecord] = []
    equity_curve: list[dict[str, Any]] = []

    signal_rows: dict[int, pd.Series] = {}

    for i in range(1, len(frame)):
        bar = frame.iloc[i]

        if long_position is not None:
            sig = signal_rows[long_position.signal_index]
            long_position, trade = _process_position_bar(
                long_position, bar, sig, config, broker
            )
            if trade is not None:
                equity += trade.net_pnl
                records.append(trade)

        if short_position is not None:
            sig = signal_rows[short_position.signal_index]
            short_position, trade = _process_position_bar(
                short_position, bar, sig, config, broker
            )
            if trade is not None:
                equity += trade.net_pnl
                records.append(trade)

        signal_row = frame.iloc[i - 1]
        used_margin = 0.0
        if long_position is not None:
            used_margin += long_position.margin_used
        if short_position is not None:
            used_margin += short_position.margin_used

        if signal_row["signal"] == "LONG" and long_position is None:
            candidate = _build_position(
                "LONG", signal_row, bar, i - 1, i, equity, config, broker
            )
            if candidate is not None:
                projected_pct = (used_margin + candidate.margin_used) / equity * 100.0
                if projected_pct <= max_total_margin_pct:
                    long_position = candidate
                    signal_rows[i - 1] = signal_row
                    used_margin += candidate.margin_used

        if signal_row["signal"] == "SHORT" and short_position is None:
            candidate = _build_position(
                "SHORT", signal_row, bar, i - 1, i, equity, config, broker
            )
            if candidate is not None:
                projected_pct = (used_margin + candidate.margin_used) / equity * 100.0
                if projected_pct <= max_total_margin_pct:
                    short_position = candidate
                    signal_rows[i - 1] = signal_row

        equity_curve.append(
            {
                "timestamp": bar["timestamp"],
                "equity": equity,
                "long_open": int(long_position is not None),
                "short_open": int(short_position is not None),
            }
        )

    # Close any remaining positions at final close.
    final_bar = frame.iloc[-1]

    for position in [long_position, short_position]:
        if position is None:
            continue
        sig = signal_rows[position.signal_index]
        exit_price = broker.exit_fill(
            float(final_bar["close"]),
            position.side,
            position.quantity * position.remaining_fraction,
        ).price
        _, close_fee = _close_fraction(
            position, exit_price, position.remaining_fraction, broker
        )
        total_fees = position.fee_open + close_fee
        trade = _finalize_trade(
            position, sig, final_bar["timestamp"], exit_price, "END_OF_DATA", total_fees
        )
        equity += trade.net_pnl
        records.append(trade)

    trades = pd.DataFrame([asdict(record) for record in records])
    curve = pd.DataFrame(equity_curve)
    if not curve.empty:
        curve.loc[curve.index[-1], "equity"] = equity
    return trades, curve


def calculate_statistics(
    trades: pd.DataFrame,
    equity_curve: pd.DataFrame,
    initial_equity: float,
) -> dict[str, float]:
    if trades.empty:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "net_profit": 0.0,
            "return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "avg_trade": 0.0,
        }

    wins = trades.loc[trades["net_pnl"] > 0, "net_pnl"]
    losses = trades.loc[trades["net_pnl"] < 0, "net_pnl"]
    gross_profit = float(wins.sum())
    gross_loss = abs(float(losses.sum()))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    net_profit = float(trades["net_pnl"].sum())

    max_drawdown_pct = 0.0
    if not equity_curve.empty:
        equity = equity_curve["equity"].astype(float)
        running_max = equity.cummax()
        drawdown = (equity - running_max) / running_max.replace(0.0, np.nan) * 100.0
        max_drawdown_pct = abs(float(drawdown.min()))

    return {
        "trades": int(len(trades)),
        "wins": int((trades["net_pnl"] > 0).sum()),
        "losses": int((trades["net_pnl"] < 0).sum()),
        "win_rate_pct": float((trades["net_pnl"] > 0).mean() * 100.0),
        "profit_factor": float(profit_factor),
        "net_profit": net_profit,
        "return_pct": net_profit / initial_equity * 100.0,
        "max_drawdown_pct": max_drawdown_pct,
        "avg_trade": float(trades["net_pnl"].mean()),
    }
