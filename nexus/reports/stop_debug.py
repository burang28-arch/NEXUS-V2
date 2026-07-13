from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


class StopDebugReport:
    """Export entry-based fixed stop and single take-profit calculations."""

    @classmethod
    def prepare(
        cls,
        frame: pd.DataFrame,
        config: dict[str, Any],
        max_rows: int = 200,
    ) -> pd.DataFrame:
        cls._validate_frame(frame)

        slip = float(config["risk"]["slippage_rate_pct"]) / 100.0
        stop_pct = float(config["risk"]["stop_loss_pct"]) / 100.0
        take_profit_pct = float(config["exit"]["take_profit_pct"]) / 100.0

        rows = []
        for side, setup_col in (("LONG", "long_setup"), ("SHORT", "short_setup")):
            for index in frame.index[frame[setup_col].fillna(False)]:
                if index + 1 >= len(frame):
                    continue

                raw = float(frame.iloc[index + 1]["open"])
                entry = raw * (1 + slip if side == "LONG" else 1 - slip)

                if side == "LONG":
                    stop = entry * (1 - stop_pct)
                    take_profit = entry * (1 + take_profit_pct)
                    is_valid = stop < entry < take_profit
                else:
                    stop = entry * (1 + stop_pct)
                    take_profit = entry * (1 - take_profit_pct)
                    is_valid = stop > entry > take_profit

                rows.append(
                    {
                        "timestamp": frame.loc[index, "timestamp"],
                        "side": side,
                        "next_open_raw": raw,
                        "entry_after_slippage": entry,
                        "stop_loss_pct": stop_pct * 100,
                        "take_profit_pct": take_profit_pct * 100,
                        "stop_price": stop,
                        "take_profit_price": take_profit,
                        "stop_distance": abs(entry - stop),
                        "take_profit_distance": abs(take_profit - entry),
                        "is_valid": is_valid,
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
        required = {"timestamp", "open", "long_setup", "short_setup"}
        missing = sorted(required.difference(frame.columns))
        if missing:
            raise ValueError(
                "Stop debug report is missing columns: " + ", ".join(missing)
            )
