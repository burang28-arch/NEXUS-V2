from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Rectangle


class TradeChartGenerator:
    """
    Generate Gate-style review charts.

    Three groups are exported:
    - successful: latest profitable trades
    - failed: latest losing trades
    - recent: latest completed trades regardless of result
    """

    BACKGROUND = "#0b0e11"
    PANEL = "#161a1e"
    GRID = "#2b3139"
    TEXT = "#eaecef"
    MUTED = "#848e9c"
    UP = "#0ecb81"
    DOWN = "#f6465d"
    ENTRY = "#f0b90b"
    STOP = "#f6465d"
    TP1 = "#2ebd85"
    TP2 = "#1e80ff"
    EXIT = "#ffffff"

    def __init__(
        self,
        candles_before: int = 30,
        candles_after: int = 12,
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
        self._reset_output(output_dir)

        data = market.copy()
        data["timestamp"] = pd.to_datetime(
            data["timestamp"],
            utc=True,
            errors="coerce",
        )
        data = data.dropna(subset=["timestamp"]).reset_index(drop=True)

        review = trades.copy()
        review["entry_time"] = pd.to_datetime(
            review["entry_time"],
            utc=True,
            errors="coerce",
        )
        review["exit_time"] = pd.to_datetime(
            review["exit_time"],
            utc=True,
            errors="coerce",
        )
        review = review.dropna(subset=["entry_time", "exit_time"])

        selections = {
            "successful": (
                review.loc[review["net_pnl"] > 0]
                .sort_values("exit_time", ascending=False)
                .head(self.max_charts)
            ),
            "failed": (
                review.loc[review["net_pnl"] < 0]
                .sort_values("exit_time", ascending=False)
                .head(self.max_charts)
            ),
            "recent": (
                review.sort_values("exit_time", ascending=False)
                .head(self.max_charts)
            ),
        }

        generated: list[Path] = []
        manifest_rows: list[dict[str, Any]] = []

        for category, selected in selections.items():
            category_dir = output_dir / category
            category_dir.mkdir(parents=True, exist_ok=True)

            # Generate oldest-to-newest inside each selected group.
            selected = selected.sort_values("exit_time")
            for _, trade in selected.iterrows():
                path = self._generate_one(
                    data,
                    trade,
                    category_dir,
                    category,
                )
                if path is None:
                    continue

                generated.append(path)
                manifest_rows.append(
                    {
                        "category": category,
                        "trade_id": int(trade["trade_id"]),
                        "result": str(trade.get("result", "")),
                        "side": str(trade["side"]),
                        "entry_time": trade["entry_time"],
                        "exit_time": trade["exit_time"],
                        "net_pnl": float(trade["net_pnl"]),
                        "file": str(path),
                    }
                )

        pd.DataFrame(manifest_rows).to_csv(
            output_dir / "chart_index.csv",
            index=False,
        )
        return generated


    def _generate_one(
        self,
        market: pd.DataFrame,
        trade: pd.Series,
        output_dir: Path,
        category: str,
    ) -> Path | None:
        signal_time = pd.to_datetime(
            trade.get("signal_time", trade["entry_time"]),
            utc=True,
        )
        entry_time = pd.to_datetime(trade["entry_time"], utc=True)
        exit_time = pd.to_datetime(trade["exit_time"], utc=True)

        signal_index = self._first_index_at_or_after(market, signal_time)
        entry_index = self._first_index_at_or_after(market, entry_time)
        exit_index = self._first_index_at_or_after(market, exit_time)
        if entry_index is None or exit_index is None:
            return None
        if signal_index is None:
            signal_index = entry_index

        signal_row = market.iloc[signal_index]
        l1_index = self._optional_int(signal_row, "divergence_l1_index")
        l2_index = self._optional_int(signal_row, "divergence_l2_index")

        if l2_index is None:
            l2_index = max(0, signal_index - 1)

        l1_price = self._optional_float(signal_row, "divergence_l1_price")
        l2_price = self._optional_float(signal_row, "divergence_l2_price")
        l1_rsi = self._optional_float(signal_row, "divergence_l1_rsi")
        l2_rsi = self._optional_float(signal_row, "divergence_l2_rsi")

        if l1_index is None and l1_price is not None:
            l1_index = self._nearest_price_index(
                market,
                end_index=l2_index,
                price=l1_price,
                side=str(trade["side"]),
                lookback=160,
            )

        relevant_indices = [
            value
            for value in (
                signal_index,
                entry_index,
                exit_index,
                l1_index,
                l2_index,
            )
            if value is not None
        ]
        window_start = max(
            0,
            min(relevant_indices) - self.candles_before,
        )
        window_end = min(
            len(market),
            max(exit_index, signal_index) + self.candles_after + 1,
        )
        window = market.iloc[window_start:window_end].copy().reset_index(drop=True)
        if window.empty:
            return None

        local_signal = signal_index - window_start
        local_entry = entry_index - window_start
        local_exit = exit_index - window_start
        local_l1 = l1_index - window_start if l1_index is not None else None
        local_l2 = l2_index - window_start if l2_index is not None else None

        figure = plt.figure(figsize=(16, 11), facecolor=self.BACKGROUND)
        price_axis = figure.add_axes([0.07, 0.40, 0.89, 0.53])
        rsi_axis = figure.add_axes(
            [0.07, 0.22, 0.89, 0.15],
            sharex=price_axis,
        )
        adx_axis = figure.add_axes(
            [0.07, 0.07, 0.89, 0.12],
            sharex=price_axis,
        )

        for axis in (price_axis, rsi_axis, adx_axis):
            axis.set_facecolor(self.BACKGROUND)
            axis.grid(color=self.GRID, alpha=0.45, linewidth=0.7)
            axis.tick_params(colors=self.MUTED)
            for spine in axis.spines.values():
                spine.set_color(self.GRID)

        self._draw_candles(price_axis, window)

        self._draw_vertical_marker(
            price_axis,
            local_signal,
            self.MUTED,
            "Signal confirmed",
        )
        self._draw_vertical_marker(
            price_axis,
            local_entry,
            self.ENTRY,
            "Entry candle",
        )
        self._draw_vertical_marker(
            price_axis,
            local_exit,
            self.EXIT,
            "Exit candle",
        )

        self._draw_price_line(
            price_axis,
            float(trade["entry_price"]),
            self.ENTRY,
            "ENTRY",
            "-",
        )
        self._draw_price_line(
            price_axis,
            float(trade["stop_price"]),
            self.STOP,
            "SL",
            ":",
        )
        self._draw_price_line(
            price_axis,
            float(trade["tp1_price"]),
            self.TP1,
            "TP1",
            "-.",
        )
        self._draw_price_line(
            price_axis,
            float(trade["tp2_price"]),
            self.TP2,
            "TP2",
            "-.",
        )

        exit_price = float(trade["exit_price"])
        price_axis.scatter(
            [local_exit],
            [exit_price],
            marker="X",
            s=130,
            color=self.EXIT,
            edgecolors=self.BACKGROUND,
            linewidths=1.0,
            label="EXIT",
            zorder=9,
        )

        if (
            local_l1 is not None
            and local_l2 is not None
            and l1_price is not None
            and l2_price is not None
            and 0 <= local_l1 < len(window)
            and 0 <= local_l2 < len(window)
        ):
            price_axis.plot(
                [local_l1, local_l2],
                [l1_price, l2_price],
                color=self.ENTRY,
                linewidth=2.0,
                linestyle="--",
                alpha=0.95,
                label="Price divergence L1→L2",
                zorder=7,
            )
            self._draw_pivot_label(
                price_axis,
                local_l1,
                l1_price,
                "L1",
                self.TP2,
            )
            self._draw_pivot_label(
                price_axis,
                local_l2,
                l2_price,
                "L2",
                self.ENTRY,
            )
        elif l2_price is not None and local_l2 is not None:
            self._draw_pivot_label(
                price_axis,
                local_l2,
                l2_price,
                "L2",
                self.ENTRY,
            )

        rsi_values = pd.to_numeric(window["rsi"], errors="coerce")
        rsi_axis.plot(
            range(len(window)),
            rsi_values,
            color="#b388ff",
            linewidth=1.4,
            label="RSI",
        )
        rsi_axis.axhline(
            30,
            color=self.UP,
            linestyle="--",
            linewidth=0.9,
            alpha=0.8,
            label="RSI 30",
        )
        rsi_axis.axhline(
            70,
            color=self.DOWN,
            linestyle="--",
            linewidth=0.9,
            alpha=0.8,
            label="RSI 70",
        )
        rsi_axis.set_ylim(0, 100)
        rsi_axis.set_ylabel("RSI", color=self.MUTED)

        if (
            local_l1 is not None
            and local_l2 is not None
            and l1_rsi is not None
            and l2_rsi is not None
            and 0 <= local_l1 < len(window)
            and 0 <= local_l2 < len(window)
        ):
            rsi_axis.plot(
                [local_l1, local_l2],
                [l1_rsi, l2_rsi],
                color=self.ENTRY,
                linewidth=2.0,
                linestyle="--",
                label="RSI divergence L1→L2",
                zorder=7,
            )
            self._draw_indicator_label(
                rsi_axis,
                local_l1,
                l1_rsi,
                f"L1 RSI {l1_rsi:.1f}",
                self.TP2,
            )
            self._draw_indicator_label(
                rsi_axis,
                local_l2,
                l2_rsi,
                f"L2 RSI {l2_rsi:.1f}",
                self.ENTRY,
            )

        adx_values = pd.to_numeric(window["adx"], errors="coerce")
        adx_axis.plot(
            range(len(window)),
            adx_values,
            color="#00b8d9",
            linewidth=1.4,
            label="ADX",
        )
        adx_min = 20.0
        adx_max = 30.0
        adx_axis.axhspan(
            adx_min,
            adx_max,
            color="#2ebd85",
            alpha=0.13,
            label=f"Allowed ADX {adx_min:.0f}-{adx_max:.0f}",
        )
        adx_axis.axhline(
            adx_min,
            color=self.UP,
            linestyle="--",
            linewidth=0.8,
            alpha=0.7,
        )
        adx_axis.axhline(
            adx_max,
            color=self.ENTRY,
            linestyle="--",
            linewidth=0.8,
            alpha=0.7,
        )
        adx_axis.set_ylabel("ADX", color=self.MUTED)
        adx_axis.set_xlabel("UTC time", color=self.MUTED)

        if 0 <= local_signal < len(window):
            signal_adx = self._optional_float(signal_row, "divergence_adx")
            if signal_adx is None and "adx" in signal_row.index:
                signal_adx = float(signal_row["adx"])
            if signal_adx is not None:
                adx_axis.scatter(
                    [local_signal],
                    [signal_adx],
                    s=70,
                    color=self.ENTRY,
                    edgecolors=self.BACKGROUND,
                    linewidths=0.8,
                    zorder=8,
                )
                self._draw_indicator_label(
                    adx_axis,
                    local_signal,
                    signal_adx,
                    f"Signal ADX {signal_adx:.1f}",
                    self.ENTRY,
                )

        trade_id = int(trade["trade_id"])
        result = str(trade.get("result", ""))
        side = str(trade["side"])
        pnl = float(trade["net_pnl"])
        title = (
            f"BTCUSDT 15m | Trade {trade_id:04d} | "
            f"{side} | {result} | Net PnL {pnl:+.2f} USDT"
        )
        price_axis.set_title(
            title,
            color=self.TEXT,
            fontsize=15,
            loc="left",
            pad=14,
        )
        price_axis.set_ylabel("Price", color=self.MUTED)

        tick_step = max(1, len(window) // 10)
        tick_positions = list(range(0, len(window), tick_step))
        tick_labels = [
            window.loc[index, "timestamp"].strftime("%m-%d\n%H:%M")
            for index in tick_positions
        ]
        adx_axis.set_xticks(tick_positions)
        adx_axis.set_xticklabels(tick_labels)
        price_axis.tick_params(labelbottom=False)
        rsi_axis.tick_params(labelbottom=False)

        reason_text = self._build_reason_text(
            trade,
            signal_row,
            l1_price,
            l2_price,
        )
        price_axis.text(
            0.012,
            0.985,
            reason_text,
            transform=price_axis.transAxes,
            va="top",
            ha="left",
            color=self.TEXT,
            fontsize=9.3,
            linespacing=1.33,
            bbox={
                "boxstyle": "round,pad=0.55",
                "facecolor": self.PANEL,
                "edgecolor": self.GRID,
                "alpha": 0.93,
            },
            zorder=10,
        )

        for axis, columns in (
            (price_axis, 2),
            (rsi_axis, 4),
            (adx_axis, 2),
        ):
            legend = axis.legend(
                loc="upper right",
                facecolor=self.PANEL,
                edgecolor=self.GRID,
                labelcolor=self.TEXT,
                fontsize=7.8,
                ncol=columns,
            )
            legend.get_frame().set_alpha(0.9)

        for axis in (price_axis, rsi_axis, adx_axis):
            axis.set_xlim(-1, len(window))

        output_path = output_dir / (
            f"{category}_trade_{trade_id:04d}_{side.lower()}_"
            f"{result.lower()}.png"
        )
        figure.savefig(
            output_path,
            dpi=150,
            facecolor=figure.get_facecolor(),
        )
        plt.close(figure)
        return output_path
    def _build_reason_text(
        self,
        trade: pd.Series,
        signal_row: pd.Series,
        l1_price: float | None,
        l2_price: float | None,
    ) -> str:
        reason = str(
            signal_row.get(
                "signal_reason",
                "RSI divergence + ADX range",
            )
        )
        l1_rsi = self._optional_float(signal_row, "divergence_l1_rsi")
        l2_rsi = self._optional_float(signal_row, "divergence_l2_rsi")
        rsi_diff = self._optional_float(
            signal_row,
            "divergence_rsi_difference",
        )
        divergence_adx = self._optional_float(
            signal_row,
            "divergence_adx",
        )

        lines = [
            f"Category: {str(trade.get('result', ''))}",
            f"Entry reason: {reason}",
            (
                f"Signal: RSI {float(trade.get('rsi', 0.0)):.2f} | "
                f"ADX {float(trade.get('adx', 0.0)):.2f} | "
                f"Score {int(trade.get('score', 0))}"
            ),
        ]

        if l1_price is not None and l2_price is not None:
            lines.append(
                f"Divergence price: L1 {l1_price:.2f} -> L2 {l2_price:.2f}"
            )
        if l1_rsi is not None and l2_rsi is not None:
            diff_text = (
                f" | diff {rsi_diff:.2f}"
                if rsi_diff is not None
                else ""
            )
            lines.append(
                f"Divergence RSI: L1 {l1_rsi:.2f} -> L2 {l2_rsi:.2f}"
                f"{diff_text}"
            )
        if divergence_adx is not None:
            lines.append(f"Divergence ADX: {divergence_adx:.2f}")

        lines.extend(
            [
                (
                    f"Entry {float(trade['entry_price']):.2f} | "
                    f"SL {float(trade['stop_price']):.2f}"
                ),
                (
                    f"TP1 {float(trade['tp1_price']):.2f} | "
                    f"TP2 {float(trade['tp2_price']):.2f}"
                ),
                (
                    f"Exit {float(trade['exit_price']):.2f} | "
                    f"{str(trade['exit_reason'])}"
                ),
                (
                    f"Holding {int(trade.get('holding_bars', 0))} bars | "
                    f"PnL {float(trade['net_pnl']):+.2f} USDT"
                ),
            ]
        )
        return "\n".join(lines)


    @classmethod
    def _draw_pivot_label(
        cls,
        axis,
        x: int,
        price: float,
        label: str,
        color: str,
    ) -> None:
        axis.scatter(
            [x],
            [price],
            s=125,
            color=color,
            edgecolors=cls.BACKGROUND,
            linewidths=1.2,
            zorder=9,
        )
        axis.annotate(
            f"{label}\n{price:.2f}",
            xy=(x, price),
            xytext=(0, 22),
            textcoords="offset points",
            ha="center",
            va="bottom",
            color=cls.TEXT,
            fontsize=10,
            fontweight="bold",
            bbox={
                "boxstyle": "round,pad=0.32",
                "facecolor": cls.PANEL,
                "edgecolor": color,
                "alpha": 0.96,
            },
            arrowprops={
                "arrowstyle": "-|>",
                "color": color,
                "linewidth": 1.2,
            },
            zorder=10,
        )

    @classmethod
    def _draw_indicator_label(
        cls,
        axis,
        x: int,
        value: float,
        label: str,
        color: str,
    ) -> None:
        axis.annotate(
            label,
            xy=(x, value),
            xytext=(7, 8),
            textcoords="offset points",
            color=cls.TEXT,
            fontsize=8.5,
            fontweight="bold",
            bbox={
                "boxstyle": "round,pad=0.22",
                "facecolor": cls.PANEL,
                "edgecolor": color,
                "alpha": 0.94,
            },
            zorder=10,
        )

    @staticmethod
    def _optional_int(row: pd.Series, column: str) -> int | None:
        if column not in row.index or pd.isna(row[column]):
            return None
        return int(row[column])

    @staticmethod
    def _nearest_price_index(
        market: pd.DataFrame,
        end_index: int,
        price: float,
        side: str,
        lookback: int,
    ) -> int | None:
        start = max(0, end_index - lookback)
        history = market.iloc[start:end_index + 1]
        if history.empty:
            return None

        column = "low" if side == "LONG" else "high"
        distance = (
            pd.to_numeric(history[column], errors="coerce") - price
        ).abs()
        if distance.dropna().empty:
            return None
        return int(distance.idxmin())

    def _draw_candles(self, axis, window: pd.DataFrame) -> None:
        width = 0.68
        for index, row in window.iterrows():
            open_price = float(row["open"])
            high_price = float(row["high"])
            low_price = float(row["low"])
            close_price = float(row["close"])
            candle_color = self.UP if close_price >= open_price else self.DOWN

            axis.vlines(
                index,
                low_price,
                high_price,
                color=candle_color,
                linewidth=1.0,
                zorder=2,
            )

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
                facecolor=candle_color,
                edgecolor=candle_color,
                linewidth=0.8,
                zorder=3,
            )
            axis.add_patch(rectangle)

    @staticmethod
    def _first_index_at_or_after(
        market: pd.DataFrame,
        timestamp: pd.Timestamp,
    ) -> int | None:
        matches = market.index[market["timestamp"] >= timestamp]
        return int(matches[0]) if len(matches) else None

    @staticmethod
    def _optional_float(row: pd.Series, column: str) -> float | None:
        if column not in row.index or pd.isna(row[column]):
            return None
        return float(row[column])

    @staticmethod
    def _draw_vertical_marker(axis, x: int, color: str, label: str) -> None:
        axis.axvline(
            x,
            color=color,
            linestyle="--",
            linewidth=1.05,
            alpha=0.9,
            label=label,
            zorder=1,
        )

    @staticmethod
    def _draw_price_line(
        axis,
        price: float,
        color: str,
        label: str,
        linestyle: str,
    ) -> None:
        axis.axhline(
            price,
            color=color,
            linestyle=linestyle,
            linewidth=1.05,
            alpha=0.9,
            label=label,
            zorder=1,
        )

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

    @staticmethod
    def _reset_output(output_dir: Path) -> None:
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
