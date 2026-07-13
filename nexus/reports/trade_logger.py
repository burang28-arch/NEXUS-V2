from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


class TradeLogger:
    """Build and export an analysis-friendly trade log."""

    @staticmethod
    def prepare(trades: pd.DataFrame) -> pd.DataFrame:
        if trades.empty:
            return trades.copy()

        required = {
            "side",
            "signal_time",
            "entry_time",
            "exit_time",
            "entry_price",
            "exit_price",
            "exit_reason",
            "score",
            "net_pnl",
            "notional",
            "holding_bars",
            "volume_score",
            "candle_score",
        }
        missing = sorted(required.difference(trades.columns))
        if missing:
            raise ValueError(
                "Trade log is missing required columns: " + ", ".join(missing)
            )

        log = trades.copy()
        for column in ("signal_time", "entry_time", "exit_time"):
            log[column] = pd.to_datetime(log[column], utc=True, errors="coerce")

        log.insert(0, "trade_id", np.arange(1, len(log) + 1))
        log["result"] = np.select(
            [log["net_pnl"] > 0, log["net_pnl"] < 0],
            ["WIN", "LOSS"],
            default="BREAKEVEN",
        )
        log["entry_month"] = log["entry_time"].dt.strftime("%Y-%m")
        log["entry_date"] = log["entry_time"].dt.strftime("%Y-%m-%d")
        log["entry_hour_utc"] = log["entry_time"].dt.hour
        log["entry_weekday_utc"] = log["entry_time"].dt.day_name()
        log["duration_minutes"] = (
            (log["exit_time"] - log["entry_time"]).dt.total_seconds() / 60.0
        )
        log["pnl_on_notional_pct"] = np.where(
            log["notional"].abs() > 0,
            log["net_pnl"] / log["notional"].abs() * 100.0,
            0.0,
        )
        log["confirmation"] = np.select(
            [
                (log["volume_score"] == 1) & (log["candle_score"] == 1),
                log["volume_score"] == 1,
                log["candle_score"] == 1,
            ],
            [
                "VOLUME+CANDLE",
                "VOLUME",
                "CANDLE",
            ],
            default="NONE",
        )
        log["setup_summary"] = (
            log["side"].astype(str)
            + " | score="
            + log["score"].astype(str)
            + " | "
            + log["confirmation"].astype(str)
        )
        log["exit_summary"] = (
            log["exit_reason"].astype(str)
            + " | pnl="
            + log["net_pnl"].map(lambda value: f"{value:.6f}")
        )

        preferred = [
            "trade_id",
            "result",
            "side",
            "signal_time",
            "entry_time",
            "exit_time",
            "entry_month",
            "entry_date",
            "entry_hour_utc",
            "entry_weekday_utc",
            "duration_minutes",
            "holding_bars",
            "entry_price",
            "stop_price",
            "tp1_price",
            "tp2_price",
            "exit_price",
            "exit_reason",
            "score",
            "confirmation",
            "volume_score",
            "candle_score",
            "size_multiplier",
            "margin_used",
            "notional",
            "quantity",
            "gross_pnl",
            "fees",
            "net_pnl",
            "return_on_margin_pct",
            "pnl_on_notional_pct",
            "adx",
            "rsi",
            "atr",
            "setup_summary",
            "exit_summary",
        ]
        ordered = [column for column in preferred if column in log.columns]
        remaining = [column for column in log.columns if column not in ordered]
        return log[ordered + remaining]

    @classmethod
    def export(cls, trades: pd.DataFrame, output_path: Path) -> pd.DataFrame:
        log = cls.prepare(trades)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        log.to_csv(output_path, index=False)
        return log
