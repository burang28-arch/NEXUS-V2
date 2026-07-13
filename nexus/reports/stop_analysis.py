from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


class StopAnalysis:
    """Validate entry-based fixed percentage stop and target levels."""

    REASONS = ("valid", "no_next_open", "invalid_config")

    @classmethod
    def prepare(cls, frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
        cls._validate_frame(frame)
        stop_pct = float(config["risk"]["stop_loss_pct"])
        tp1_pct = float(config["exit"]["tp1_pct"])
        tp2_pct = float(config["exit"]["tp2_pct"])
        config_valid = stop_pct > 0 and tp1_pct > 0 and tp2_pct > tp1_pct

        rows = []
        all_results = []
        for side, setup_col in (("LONG", "long_setup"), ("SHORT", "short_setup")):
            setup = frame[setup_col].fillna(False)
            next_open = frame["open"].shift(-1).loc[setup]
            results = pd.Series("valid", index=next_open.index, dtype="object")
            results = results.mask(next_open.isna(), "no_next_open")
            if not config_valid:
                results.loc[next_open.notna()] = "invalid_config"
            all_results.append(results.reset_index(drop=True))
            rows.extend(cls._summary_rows(side, results))
        combined = pd.concat(all_results, ignore_index=True) if all_results else pd.Series(dtype="object")
        rows.extend(cls._summary_rows("ALL", combined))
        return pd.DataFrame(rows)

    @classmethod
    def export(cls, frame, config, output_path: Path):
        report = cls.prepare(frame, config)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report.to_csv(output_path, index=False)
        return report

    @classmethod
    def _summary_rows(cls, side, results):
        total = len(results)
        return [{
            "side": side,
            "reason": reason,
            "count": int((results == reason).sum()),
            "share_of_side_setups_pct": (int((results == reason).sum()) / total * 100.0 if total else 0.0),
        } for reason in cls.REASONS]

    @staticmethod
    def _validate_frame(frame):
        required = {"open", "long_setup", "short_setup"}
        missing = sorted(required.difference(frame.columns))
        if missing:
            raise ValueError("Stop analysis is missing columns: " + ", ".join(missing))
