from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


class StopDebugReport:
    """Export raw stop-calculation values for setup candidates."""

    @classmethod
    def prepare(
        cls,
        frame: pd.DataFrame,
        config: dict[str, Any],
        max_rows: int = 200,
    ) -> pd.DataFrame:
        cls._validate_frame(frame)

        slippage_rate = float(config["risk"]["slippage_rate_pct"]) / 100.0
        atr_buffer_ratio = float(config["risk"]["atr_stop_buffer"])
        rows: list[dict[str, float | int | str | bool]] = []

        rows.extend(
            cls._side_rows(
                frame=frame,
                side="LONG",
                setup=frame["long_setup"].fillna(False),
                slippage_rate=slippage_rate,
                atr_buffer_ratio=atr_buffer_ratio,
            )
        )
        rows.extend(
            cls._side_rows(
                frame=frame,
                side="SHORT",
                setup=frame["short_setup"].fillna(False),
                slippage_rate=slippage_rate,
                atr_buffer_ratio=atr_buffer_ratio,
            )
        )

        report = pd.DataFrame(rows)
        if report.empty:
            return report

        report.sort_values(
            ["is_valid", "timestamp", "side"],
            ascending=[True, True, True],
            inplace=True,
        )
        report.reset_index(drop=True, inplace=True)

        if max_rows > 0:
            report = report.head(max_rows).copy()

        return report

    @classmethod
    def export(
        cls,
        frame: pd.DataFrame,
        config: dict[str, Any],
        output_path: Path,
        max_rows: int = 200,
    ) -> pd.DataFrame:
        report = cls.prepare(frame, config, max_rows=max_rows)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report.to_csv(output_path, index=False)
        return report

    @staticmethod
    def _side_rows(
        frame: pd.DataFrame,
        side: str,
        setup: pd.Series,
        slippage_rate: float,
        atr_buffer_ratio: float,
    ) -> list[dict[str, float | int | str | bool]]:
        candidate_indices = frame.index[setup]
        output: list[dict[str, float | int | str | bool]] = []

        for index in candidate_indices:
            if index + 1 >= len(frame):
                next_open = float("nan")
            else:
                next_open = float(frame.iloc[index + 1]["open"])

            row = frame.loc[index]
            swing = (
                float(row["swing_low"])
                if side == "LONG"
                else float(row["swing_high"])
            )
            stop = float(row["stop_price"])

            if side == "LONG":
                entry = next_open * (1.0 + slippage_rate)
                is_valid = bool(pd.notna(entry) and pd.notna(stop) and stop < entry)
                reason = (
                    "valid"
                    if is_valid
                    else "stop_wrong_side"
                    if pd.notna(stop) and pd.notna(entry)
                    else "missing_value"
                )
                reference_price = float(row["low"])
                stop_distance = entry - stop if pd.notna(entry) and pd.notna(stop) else float("nan")
            else:
                entry = next_open * (1.0 - slippage_rate)
                is_valid = bool(pd.notna(entry) and pd.notna(stop) and stop > entry)
                reason = (
                    "valid"
                    if is_valid
                    else "stop_wrong_side"
                    if pd.notna(stop) and pd.notna(entry)
                    else "missing_value"
                )
                reference_price = float(row["high"])
                stop_distance = stop - entry if pd.notna(entry) and pd.notna(stop) else float("nan")

            output.append(
                {
                    "timestamp": row["timestamp"],
                    "side": side,
                    "next_open_raw": next_open,
                    "entry_after_slippage": entry,
                    "signal_open": float(row["open"]),
                    "signal_high": float(row["high"]),
                    "signal_low": float(row["low"]),
                    "signal_close": float(row["close"]),
                    "swing_price": swing,
                    "signal_reference_price": reference_price,
                    "atr": float(row["atr"]),
                    "atr_buffer": float(row["atr"]) * atr_buffer_ratio,
                    "stop_price": stop,
                    "stop_distance": stop_distance,
                    "is_valid": is_valid,
                    "reason": reason,
                    "swing_vs_entry": swing - entry if pd.notna(entry) else float("nan"),
                    "reference_vs_entry": reference_price - entry if pd.notna(entry) else float("nan"),
                }
            )

        return output

    @staticmethod
    def _validate_frame(frame: pd.DataFrame) -> None:
        required = {
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "atr",
            "swing_low",
            "swing_high",
            "stop_price",
            "long_setup",
            "short_setup",
        }
        missing = sorted(required.difference(frame.columns))
        if missing:
            raise ValueError(
                "Stop debug report is missing columns: "
                + ", ".join(missing)
            )
