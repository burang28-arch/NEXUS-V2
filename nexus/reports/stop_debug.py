from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


class StopDebugReport:
    """Export entry-based fixed stop and take-profit calculations."""

    @classmethod
    def prepare(cls, frame: pd.DataFrame, config: dict[str, Any], max_rows: int = 200) -> pd.DataFrame:
        cls._validate_frame(frame)
        slip = float(config["risk"]["slippage_rate_pct"]) / 100.0
        stop_pct = float(config["risk"]["stop_loss_pct"]) / 100.0
        tp1_pct = float(config["exit"]["tp1_pct"]) / 100.0
        tp2_pct = float(config["exit"]["tp2_pct"]) / 100.0
        rows = []
        for side, setup_col in (("LONG", "long_setup"), ("SHORT", "short_setup")):
            for index in frame.index[frame[setup_col].fillna(False)]:
                if index + 1 >= len(frame):
                    continue
                raw = float(frame.iloc[index + 1]["open"])
                entry = raw * (1 + slip if side == "LONG" else 1 - slip)
                if side == "LONG":
                    stop, tp1, tp2 = entry*(1-stop_pct), entry*(1+tp1_pct), entry*(1+tp2_pct)
                else:
                    stop, tp1, tp2 = entry*(1+stop_pct), entry*(1-tp1_pct), entry*(1-tp2_pct)
                rows.append({
                    "timestamp": frame.loc[index, "timestamp"], "side": side,
                    "next_open_raw": raw, "entry_after_slippage": entry,
                    "stop_loss_pct": stop_pct*100, "tp1_pct": tp1_pct*100, "tp2_pct": tp2_pct*100,
                    "stop_price": stop, "tp1_price": tp1, "tp2_price": tp2,
                    "stop_distance": abs(entry-stop), "tp1_distance": abs(tp1-entry), "tp2_distance": abs(tp2-entry),
                    "is_valid": (stop < entry < tp1 < tp2) if side == "LONG" else (stop > entry > tp1 > tp2),
                })
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
            raise ValueError("Stop debug report is missing columns: " + ", ".join(missing))
