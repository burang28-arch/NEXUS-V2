from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


class SignalAnalyzer:
    """Summarize trade performance by side, score, ADX bucket, and RSI bucket."""

    ADX_BINS = [-np.inf, 15.0, 20.0, 25.0, 30.0, np.inf]
    ADX_LABELS = ["<15", "15-20", "20-25", "25-30", "30+"]

    RSI_BINS = [-np.inf, 20.0, 25.0, 30.0, 35.0, 40.0, 60.0, 65.0, 70.0, 75.0, 80.0, np.inf]
    RSI_LABELS = [
        "<20",
        "20-25",
        "25-30",
        "30-35",
        "35-40",
        "40-60",
        "60-65",
        "65-70",
        "70-75",
        "75-80",
        "80+",
    ]

    @classmethod
    def prepare(cls, trades: pd.DataFrame) -> pd.DataFrame:
        columns = [
            "category",
            "value",
            "trades",
            "wins",
            "losses",
            "win_rate_pct",
            "profit_factor",
            "gross_profit",
            "gross_loss",
            "net_profit",
            "average_trade",
        ]

        if trades.empty:
            return pd.DataFrame(columns=columns)

        required = {"side", "score", "adx", "rsi", "net_pnl"}
        missing = sorted(required.difference(trades.columns))
        if missing:
            raise ValueError(
                "Signal analysis is missing required columns: "
                + ", ".join(missing)
            )

        data = trades.copy()
        for column in ("score", "adx", "rsi", "net_pnl"):
            data[column] = pd.to_numeric(data[column], errors="coerce")

        data = data.dropna(subset=["side", "score", "adx", "rsi", "net_pnl"])

        rows: list[dict[str, float | int | str]] = []

        for side, group in data.groupby("side", sort=True):
            rows.append(cls._summarize("side", str(side), group))

        for score, group in data.groupby("score", sort=True):
            rows.append(cls._summarize("score", str(int(score)), group))

        adx_bucket = pd.cut(
            data["adx"],
            bins=cls.ADX_BINS,
            labels=cls.ADX_LABELS,
            right=False,
        )
        for value, group in data.groupby(adx_bucket, observed=True, sort=False):
            rows.append(cls._summarize("adx", str(value), group))

        rsi_bucket = pd.cut(
            data["rsi"],
            bins=cls.RSI_BINS,
            labels=cls.RSI_LABELS,
            right=False,
        )
        for value, group in data.groupby(rsi_bucket, observed=True, sort=False):
            rows.append(cls._summarize("rsi", str(value), group))

        return pd.DataFrame(rows, columns=columns)

    @staticmethod
    def _summarize(
        category: str,
        value: str,
        group: pd.DataFrame,
    ) -> dict[str, float | int | str]:
        wins = group.loc[group["net_pnl"] > 0, "net_pnl"]
        losses = group.loc[group["net_pnl"] < 0, "net_pnl"]

        gross_profit = float(wins.sum())
        gross_loss = abs(float(losses.sum()))

        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        elif gross_profit > 0:
            profit_factor = float("inf")
        else:
            profit_factor = 0.0

        return {
            "category": category,
            "value": value,
            "trades": int(len(group)),
            "wins": int((group["net_pnl"] > 0).sum()),
            "losses": int((group["net_pnl"] < 0).sum()),
            "win_rate_pct": float((group["net_pnl"] > 0).mean() * 100.0),
            "profit_factor": float(profit_factor),
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "net_profit": float(group["net_pnl"].sum()),
            "average_trade": float(group["net_pnl"].mean()),
        }

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
