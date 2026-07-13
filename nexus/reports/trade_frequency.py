from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


class TradeFrequencyAnalyzer:
    """Analyze where potential trades are filtered out."""

    @classmethod
    def prepare(
        cls,
        frame: pd.DataFrame,
        trades: pd.DataFrame,
        config: dict[str, Any],
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        cls._validate_frame(frame)

        entry = config["entry"]
        adx_max = float(entry["adx_max"])
        rsi_long_max = float(entry["rsi_long_max"])
        rsi_short_min = float(entry["rsi_short_min"])

        ready = (
            frame["adx"].notna()
            & frame["rsi"].notna()
            & frame["bb_lower"].notna()
            & frame["bb_upper"].notna()
            & frame["atr"].notna()
        )

        long_rsi = ready & (frame["rsi"] <= rsi_long_max)
        short_rsi = ready & (frame["rsi"] >= rsi_short_min)

        long_adx = long_rsi & (frame["adx"] <= adx_max)
        short_adx = short_rsi & (frame["adx"] <= adx_max)

        long_band = long_adx & (frame["low"] <= frame["bb_lower"])
        short_band = short_adx & (frame["high"] >= frame["bb_upper"])

        long_valid = cls._valid_next_open_candidate(frame, long_band, "LONG")
        short_valid = cls._valid_next_open_candidate(frame, short_band, "SHORT")

        executed_long = cls._executed_count(trades, "LONG")
        executed_short = cls._executed_count(trades, "SHORT")

        stages = [
            ("total_candles", len(frame), len(frame)),
            ("indicator_ready", int(ready.sum()), int(ready.sum())),
            ("rsi_pass", int(long_rsi.sum()), int(short_rsi.sum())),
            ("adx_pass", int(long_adx.sum()), int(short_adx.sum())),
            ("bollinger_touch", int(long_band.sum()), int(short_band.sum())),
            ("valid_stop_and_targets", int(long_valid.sum()), int(short_valid.sum())),
            ("executed_trades", executed_long, executed_short),
        ]

        frequency_rows: list[dict[str, float | int | str]] = []
        previous_total: int | None = None

        for stage, long_count, short_count in stages:
            total = long_count + short_count
            if stage in {"total_candles", "indicator_ready"}:
                total = long_count

            dropped = 0 if previous_total is None else max(0, previous_total - total)
            pass_rate = (
                100.0
                if previous_total is None or previous_total == 0
                else total / previous_total * 100.0
            )

            frequency_rows.append(
                {
                    "stage": stage,
                    "long_count": long_count,
                    "short_count": short_count,
                    "total_count": total,
                    "dropped_from_previous": dropped,
                    "pass_rate_from_previous_pct": pass_rate,
                }
            )
            previous_total = total

        rejects = cls._reject_reason_rows(
            frame=frame,
            ready=ready,
            long_rsi=long_rsi,
            short_rsi=short_rsi,
            long_adx=long_adx,
            short_adx=short_adx,
            long_band=long_band,
            short_band=short_band,
            long_valid=long_valid,
            short_valid=short_valid,
            executed_long=executed_long,
            executed_short=executed_short,
        )

        return (
            pd.DataFrame(frequency_rows),
            pd.DataFrame(rejects),
        )

    @classmethod
    def export(
        cls,
        frame: pd.DataFrame,
        trades: pd.DataFrame,
        config: dict[str, Any],
        frequency_output: Path,
        rejects_output: Path,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        frequency, rejects = cls.prepare(frame, trades, config)

        frequency_output.parent.mkdir(parents=True, exist_ok=True)
        rejects_output.parent.mkdir(parents=True, exist_ok=True)

        frequency.to_csv(frequency_output, index=False)
        rejects.to_csv(rejects_output, index=False)
        return frequency, rejects

    @staticmethod
    def _valid_next_open_candidate(
        frame: pd.DataFrame,
        setup: pd.Series,
        side: str,
    ) -> pd.Series:
        # Fixed percentage stops and targets are always on the correct side
        # of a valid next-open entry.
        return setup & frame["open"].shift(-1).notna()

    @staticmethod
    def _executed_count(trades: pd.DataFrame, side: str) -> int:
        if trades.empty or "side" not in trades.columns:
            return 0
        return int((trades["side"] == side).sum())

    @classmethod
    def _reject_reason_rows(
        cls,
        frame: pd.DataFrame,
        ready: pd.Series,
        long_rsi: pd.Series,
        short_rsi: pd.Series,
        long_adx: pd.Series,
        short_adx: pd.Series,
        long_band: pd.Series,
        short_band: pd.Series,
        long_valid: pd.Series,
        short_valid: pd.Series,
        executed_long: int,
        executed_short: int,
    ) -> list[dict[str, float | int | str]]:
        total_candles = len(frame)

        reasons = [
            (
                "indicator_not_ready",
                int((~ready).sum()),
                int((~ready).sum()),
            ),
            (
                "rsi_filter",
                int((ready & ~long_rsi).sum()),
                int((ready & ~short_rsi).sum()),
            ),
            (
                "adx_filter_after_rsi",
                int((long_rsi & ~long_adx).sum()),
                int((short_rsi & ~short_adx).sum()),
            ),
            (
                "bollinger_not_touched",
                int((long_adx & ~long_band).sum()),
                int((short_adx & ~short_band).sum()),
            ),
            (
                "invalid_stop_or_targets",
                int((long_band & ~long_valid).sum()),
                int((short_band & ~short_valid).sum()),
            ),
            (
                "position_open_or_margin_limit",
                max(0, int(long_valid.sum()) - executed_long),
                max(0, int(short_valid.sum()) - executed_short),
            ),
        ]

        rows: list[dict[str, float | int | str]] = []
        for reason, long_count, short_count in reasons:
            total = long_count + short_count
            rows.append(
                {
                    "reason": reason,
                    "long_count": long_count,
                    "short_count": short_count,
                    "total_count": total,
                    "share_of_all_direction_checks_pct": (
                        total / (total_candles * 2) * 100.0
                        if total_candles > 0
                        else 0.0
                    ),
                }
            )

        return sorted(
            rows,
            key=lambda row: int(row["total_count"]),
            reverse=True,
        )

    @staticmethod
    def _validate_frame(frame: pd.DataFrame) -> None:
        required = {
            "open",
            "high",
            "low",
            "rsi",
            "adx",
            "atr",
            "bb_lower",
            "bb_middle",
            "bb_upper",
        }
        missing = sorted(required.difference(frame.columns))
        if missing:
            raise ValueError(
                "Trade frequency analysis is missing columns: "
                + ", ".join(missing)
            )
