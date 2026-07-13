from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


class StopAnalysis:
    """Explain why completed setup candles fail stop/target validation."""

    REASONS = (
        "valid",
        "no_next_open",
        "stop_missing",
        "stop_wrong_side",
        "tp1_wrong_side",
        "tp2_wrong_side",
    )

    @classmethod
    def prepare(
        cls,
        frame: pd.DataFrame,
        config: dict[str, Any],
    ) -> pd.DataFrame:
        cls._validate_frame(frame)
        slippage_rate = float(config["risk"]["slippage_rate_pct"]) / 100.0

        long_results = cls._analyze_side(
            frame,
            side="LONG",
            setup=frame["long_setup"].fillna(False),
            slippage_rate=slippage_rate,
        )
        short_results = cls._analyze_side(
            frame,
            side="SHORT",
            setup=frame["short_setup"].fillna(False),
            slippage_rate=slippage_rate,
        )

        rows: list[dict[str, float | int | str]] = []
        rows.extend(cls._summary_rows("LONG", long_results))
        rows.extend(cls._summary_rows("SHORT", short_results))
        rows.extend(
            cls._summary_rows(
                "ALL",
                pd.concat([long_results, short_results], ignore_index=True),
            )
        )
        return pd.DataFrame(rows)

    @classmethod
    def export(
        cls,
        frame: pd.DataFrame,
        config: dict[str, Any],
        output_path: Path,
    ) -> pd.DataFrame:
        report = cls.prepare(frame, config)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report.to_csv(output_path, index=False)
        return report

    @classmethod
    def _summary_rows(
        cls,
        side: str,
        results: pd.Series,
    ) -> list[dict[str, float | int | str]]:
        total = int(len(results))
        rows: list[dict[str, float | int | str]] = []
        for reason in cls.REASONS:
            count = int((results == reason).sum())
            rows.append(
                {
                    "side": side,
                    "reason": reason,
                    "count": count,
                    "share_of_side_setups_pct": (
                        count / total * 100.0 if total > 0 else 0.0
                    ),
                }
            )
        return rows

    @staticmethod
    def _analyze_side(
        frame: pd.DataFrame,
        side: str,
        setup: pd.Series,
        slippage_rate: float,
    ) -> pd.Series:
        candidates = frame.loc[setup].copy()
        if candidates.empty:
            return pd.Series(dtype="object")

        next_open = frame["open"].shift(-1).loc[candidates.index]
        stop = candidates["stop_price"]
        tp1 = candidates["bb_middle"]
        tp2 = candidates["bb_upper"] if side == "LONG" else candidates["bb_lower"]

        if side == "LONG":
            entry = next_open * (1.0 + slippage_rate)
            stop_valid = stop < entry
            tp1_valid = tp1 > entry
            tp2_valid = tp2 > entry
        else:
            entry = next_open * (1.0 - slippage_rate)
            stop_valid = stop > entry
            tp1_valid = tp1 < entry
            tp2_valid = tp2 < entry

        reason = pd.Series("valid", index=candidates.index, dtype="object")
        reason = reason.mask(next_open.isna(), "no_next_open")
        reason = reason.mask(next_open.notna() & stop.isna(), "stop_missing")
        reason = reason.mask(
            next_open.notna() & stop.notna() & ~stop_valid,
            "stop_wrong_side",
        )
        reason = reason.mask(
            next_open.notna() & stop.notna() & stop_valid & ~tp1_valid,
            "tp1_wrong_side",
        )
        reason = reason.mask(
            next_open.notna()
            & stop.notna()
            & stop_valid
            & tp1_valid
            & ~tp2_valid,
            "tp2_wrong_side",
        )
        return reason.reset_index(drop=True)

    @staticmethod
    def _validate_frame(frame: pd.DataFrame) -> None:
        required = {
            "open",
            "bb_lower",
            "bb_middle",
            "bb_upper",
            "stop_price",
            "long_setup",
            "short_setup",
        }
        missing = sorted(required.difference(frame.columns))
        if missing:
            raise ValueError(
                "Stop analysis is missing columns: " + ", ".join(missing)
            )
