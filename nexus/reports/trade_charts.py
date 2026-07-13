from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Rectangle


class TradeChartGenerator:
    """Generate simple candlestick charts for completed trades."""

    def __init__(
        self,
        candles_before: int = 20,
        candles_after: int = 10,
        max_charts: int = 10,
    ) -> None:
        if candles_before < 1:
            raise ValueError("candles_before must be at least 1.")
        if candles_after < 1:
            raise ValueError("candles_after must be at least 1.")
        if max_charts < 1:
            raise ValueError("max_charts must be at least 1.")

        self.candles_before = candles_before
        self.candles_after = candles_after
        self.max_charts = max_charts

    def generate(
        self,
        market: pd.DataFrame,
        trades: pd.DataFrame,
        output_dir: Path,
    ) -> list[Path]:
        if trades.empty:
            return []

        self._validate_market(market)
        output_dir.mkdir(parents=True, exist_ok=True)

        data = market.copy()
        data["timestamp"] = pd.to_datetime(
            data["timestamp"],
            utc=True,
            errors="coerce",
        )
        data = data.dropna(subset=["timestamp"]).reset_index(drop=True)

        generated: list[Path] = []
        for _, trade in trades.head(self.max_charts).iterrows():
            path = self._generate_one(data, trade, output_dir)
            if path is not None:
                generated.append(path)

        return generated

    def _generate_one(
        self,
        market: pd.DataFrame,
        trade: pd.Series,
        output_dir: Path,
    ) -> Path | None:
        entry_time = pd.to_datetime(trade["entry_time"], utc=True)
        exit_time = pd.to_datetime(trade["exit_time"], utc=True)

        entry_matches = market.index[market["timestamp"] >= entry_time]
        exit_matches = market.index[market["timestamp"] >= exit_time]
        if len(entry_matches) == 0 or len(exit_matches) == 0:
            return None

        entry_index = int(entry_matches[0])
        exit_index = int(exit_matches[0])

        start = max(0, entry_index - self.candles_before)
        end = min(
            len(market),
            exit_index + self.candles_after + 1,
        )
        window = market.iloc[start:end].copy().reset_index(drop=True)
        if window.empty:
            return None

        local_entry = entry_index - start
        local_exit = exit_index - start

        figure, axis = plt.subplots(figsize=(14, 7))
        self._draw_candles(axis, window)

        axis.axvline(
            local_entry,
            linestyle="--",
            linewidth=1.2,
            label="Entry candle",
        )
        axis.axvline(
            local_exit,
            linestyle="--",
            linewidth=1.2,
            label="Exit candle",
        )
        axis.axhline(
            float(trade["entry_price"]),
            linestyle="-",
            linewidth=1.0,
            label="Entry",
        )
        axis.axhline(
            float(trade["stop_price"]),
            linestyle=":",
            linewidth=1.0,
            label="Stop",
        )
        axis.axhline(
            float(trade["tp1_price"]),
            linestyle="-.",
            linewidth=1.0,
            label="TP1",
        )
        axis.axhline(
            float(trade["tp2_price"]),
            linestyle="-.",
            linewidth=1.0,
            label="TP2",
        )
        axis.scatter(
            [local_exit],
            [float(trade["exit_price"])],
            marker="x",
            s=80,
            label="Exit",
            zorder=5,
        )

        trade_id = int(trade["trade_id"])
        title = (
            f"Trade {trade_id:04d} | {trade['side']} | "
            f"{trade['result']} | PnL {float(trade['net_pnl']):.4f}"
        )
        axis.set_title(title)
        axis.set_ylabel("Price")
        axis.set_xlabel("15-minute candles")
        axis.grid(alpha=0.2)
        axis.legend(loc="best")

        tick_step = max(1, len(window) // 8)
        tick_positions = list(range(0, len(window), tick_step))
        tick_labels = [
            window.loc[index, "timestamp"].strftime("%m-%d\n%H:%M")
            for index in tick_positions
        ]
        axis.set_xticks(tick_positions)
        axis.set_xticklabels(tick_labels)

        figure.tight_layout()

        output_path = output_dir / f"trade_{trade_id:04d}.png"
        figure.savefig(output_path, dpi=140)
        plt.close(figure)
        return output_path

    @staticmethod
    def _draw_candles(axis, window: pd.DataFrame) -> None:
        width = 0.65
        for index, row in window.iterrows():
            open_price = float(row["open"])
            high_price = float(row["high"])
            low_price = float(row["low"])
            close_price = float(row["close"])

            axis.vlines(index, low_price, high_price, linewidth=1.0)

            body_bottom = min(open_price, close_price)
            body_height = abs(close_price - open_price)
            if body_height == 0:
                body_height = max(
                    (high_price - low_price) * 0.01,
                    1e-8,
                )

            rectangle = Rectangle(
                (index - width / 2, body_bottom),
                width,
                body_height,
                fill=close_price >= open_price,
                linewidth=1.0,
                alpha=0.8,
            )
            axis.add_patch(rectangle)

        axis.set_xlim(-1, len(window))

    @staticmethod
    def _validate_market(market: pd.DataFrame) -> None:
        required = {
            "timestamp",
            "open",
            "high",
            "low",
            "close",
        }
        missing = sorted(required.difference(market.columns))
        if missing:
            raise ValueError(
                "Market data is missing required columns: "
                + ", ".join(missing)
            )
