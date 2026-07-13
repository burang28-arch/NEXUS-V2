from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


class StopDebugReport:
    """Export fixed stop/target calculations for limit-entry candidates."""

    @classmethod
    def prepare(
        cls,
        frame: pd.DataFrame,
        config: dict[str, Any],
        max_rows: int = 200,
    ) -> pd.DataFrame:
        cls._validate_frame(frame)

        offset = float(config["entry"]["limit_offset_pct"]) / 100.0
        expiry = int(config["entry"]["limit_expiry_bars"])
        stop_pct = float(config["risk"]["stop_loss_pct"]) / 100.0
        take_profit_pct = float(config["exit"]["take_profit_pct"]) / 100.0

        rows = []
        for side, setup_col in (("LONG", "long_setup"), ("SHORT", "short_setup")):
            for index in frame.index[frame[setup_col].fillna(False)]:
                first_bar = index + 1
                if first_bar >= len(frame):
                    continue

                reference_open = float(frame.iloc[first_bar]["open"])
                limit_price = (
                    reference_open * (1.0 - offset)
                    if side == "LONG"
                    else reference_open * (1.0 + offset)
                )
                end_bar = min(len(frame), first_bar + expiry)
                window = frame.iloc[first_bar:end_bar]

                if side == "LONG":
                    fillable = bool((window["low"] <= limit_price).any())
                    stop = limit_price * (1.0 - stop_pct)
                    take_profit = limit_price * (1.0 + take_profit_pct)
                else:
                    fillable = bool((window["high"] >= limit_price).any())
                    stop = limit_price * (1.0 + stop_pct)
                    take_profit = limit_price * (1.0 - take_profit_pct)

                rows.append(
                    {
                        "timestamp": frame.loc[index, "timestamp"],
                        "side": side,
                        "reference_next_open": reference_open,
                        "limit_offset_pct": offset * 100.0,
                        "limit_price": limit_price,
                        "limit_expiry_bars": expiry,
                        "fillable_within_expiry": fillable,
                        "stop_loss_pct": stop_pct * 100.0,
                        "take_profit_pct": take_profit_pct * 100.0,
                        "stop_price": stop,
                        "take_profit_price": take_profit,
                    }
                )

        report = pd.DataFrame(rows)
        return report.head(max_rows).copy() if max_rows > 0 else report

    @classmethod
    def export(cls, frame, config, output_path: Path, max_rows: int = 200):
        report = cls.prepare(frame, config, max_rows)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report.to_csv(output_path, index=False)
        return report

    @staticmethod
    def _validate_frame(frame):
        required = {
            "timestamp",
            "open",
            "high",
            "low",
            "long_setup",
            "short_setup",
        }
        missing = sorted(required.difference(frame.columns))
        if missing:
            raise ValueError(
                "Stop debug report is missing columns: " + ", ".join(missing)
            )
