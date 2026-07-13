from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


class MonthlyReport:
    """Generate a monthly performance summary from completed trades."""

    @staticmethod
    def prepare(trades: pd.DataFrame) -> pd.DataFrame:
        columns = [
            "month",
            "trades",
            "long_trades",
            "short_trades",
            "wins",
            "losses",
            "win_rate_pct",
            "profit_factor",
            "gross_profit",
            "gross_loss",
            "net_profit",
            "average_trade",
            "best_trade",
            "worst_trade",
            "average_holding_bars",
        ]

        if trades.empty:
            return pd.DataFrame(columns=columns)

        required = {
            "entry_time",
            "side",
            "net_pnl",
            "holding_bars",
        }
        missing = sorted(required.difference(trades.columns))
        if missing:
            raise ValueError(
                "Monthly report is missing required columns: "
                + ", ".join(missing)
            )

        data = trades.copy()
        data["entry_time"] = pd.to_datetime(
            data["entry_time"],
            utc=True,
            errors="coerce",
        )
        data = data.dropna(subset=["entry_time"])
        data["month"] = data["entry_time"].dt.strftime("%Y-%m")

        rows: list[dict[str, float | int | str]] = []

        for month, group in data.groupby("month", sort=True):
            wins = group.loc[group["net_pnl"] > 0, "net_pnl"]
            losses = group.loc[group["net_pnl"] < 0, "net_pnl"]

            gross_profit = float(wins.sum())
            gross_loss = abs(float(losses.sum()))
            profit_factor = (
                gross_profit / gross_loss
                if gross_loss > 0
                else np.inf if gross_profit > 0 else 0.0
            )

            rows.append(
                {
                    "month": month,
                    "trades": int(len(group)),
                    "long_trades": int((group["side"] == "LONG").sum()),
                    "short_trades": int((group["side"] == "SHORT").sum()),
                    "wins": int((group["net_pnl"] > 0).sum()),
                    "losses": int((group["net_pnl"] < 0).sum()),
                    "win_rate_pct": float(
                        (group["net_pnl"] > 0).mean() * 100.0
                    ),
                    "profit_factor": float(profit_factor),
                    "gross_profit": gross_profit,
                    "gross_loss": gross_loss,
                    "net_profit": float(group["net_pnl"].sum()),
                    "average_trade": float(group["net_pnl"].mean()),
                    "best_trade": float(group["net_pnl"].max()),
                    "worst_trade": float(group["net_pnl"].min()),
                    "average_holding_bars": float(
                        group["holding_bars"].mean()
                    ),
                }
            )

        return pd.DataFrame(rows, columns=columns)

    @classmethod
    def export(
        cls,
        trades: pd.DataFrame,
        output_path: Path,
    ) -> pd.DataFrame:
        report = cls.prepare(trades)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report.to_csv(output_path, index=False)
        return report
