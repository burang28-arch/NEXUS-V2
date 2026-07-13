from __future__ import annotations

import argparse
import sys
from pathlib import Path

from nexus.backtest import calculate_statistics, run_backtest
from nexus.config import load_config
from nexus.data import load_ohlcv_csv
from nexus.indicators import add_indicators
from nexus.signals import add_signal_columns, extract_signals
from nexus.reports.monthly_report import MonthlyReport
from nexus.reports.trade_charts import TradeChartGenerator
from nexus.reports.trade_logger import TradeLogger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nexus",
        description="NEXUS V2 BTCUSDT 15-minute mean-reversion framework.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("csv_path", type=Path)
    inspect_parser.add_argument("--config", type=Path, default=Path("config/strategy.yaml"))
    inspect_parser.add_argument("--tail", type=int, default=5)

    signals_parser = subparsers.add_parser("signals")
    signals_parser.add_argument("csv_path", type=Path)
    signals_parser.add_argument("--config", type=Path, default=Path("config/strategy.yaml"))
    signals_parser.add_argument("--output", type=Path, default=Path("reports/signals.csv"))

    backtest_parser = subparsers.add_parser("backtest")
    backtest_parser.add_argument("csv_path", type=Path)
    backtest_parser.add_argument("--config", type=Path, default=Path("config/strategy.yaml"))
    backtest_parser.add_argument("--trades-output", type=Path, default=Path("reports/trades.csv"))
    backtest_parser.add_argument("--equity-output", type=Path, default=Path("reports/equity.csv"))
    backtest_parser.add_argument(
        "--monthly-output",
        type=Path,
        default=Path("reports/monthly_report.csv"),
    )
    backtest_parser.add_argument(
        "--charts",
        action="store_true",
        help="Generate charts for the first completed trades.",
    )
    backtest_parser.add_argument(
        "--max-charts",
        type=int,
        default=10,
        help="Maximum number of trade charts. Default: 10",
    )

    return parser


def _load_enriched(csv_path: Path, config_path: Path):
    config = load_config(config_path)
    frame = add_indicators(load_ohlcv_csv(csv_path), config)
    frame = add_signal_columns(frame, config)
    return config, frame


def run_inspect(csv_path: Path, config_path: Path, tail: int) -> int:
    _, frame = _load_enriched(csv_path, config_path)
    cols = [
        "timestamp", "open", "high", "low", "close", "volume",
        "rsi", "atr", "adx", "bb_lower", "bb_middle", "bb_upper",
        "volume_ma", "swing_low", "swing_high", "signal", "score",
        "size_multiplier", "stop_price",
    ]
    print("NEXUS V2 v2.0.0-c")
    print(frame[cols].tail(max(1, tail)).to_string(index=False))
    return 0


def run_signals(csv_path: Path, config_path: Path, output_path: Path) -> int:
    _, frame = _load_enriched(csv_path, config_path)
    signals = extract_signals(frame)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    signals.to_csv(output_path, index=False)

    monthly = (
        signals.assign(month=signals["timestamp"].dt.to_period("M").astype(str))
        .groupby("month")
        .size()
    )
    print("NEXUS V2 v2.0.0-c")
    print(f"- Total signals: {len(signals):,}")
    print(f"- Long signals:  {(signals['signal'] == 'LONG').sum():,}")
    print(f"- Short signals: {(signals['signal'] == 'SHORT').sum():,}")
    if not monthly.empty:
        print(f"- Avg signals/month: {monthly.mean():.2f}")
        print(f"- Median/month:      {monthly.median():.2f}")
        print(f"- Min/month:         {monthly.min():.0f}")
        print(f"- Max/month:         {monthly.max():.0f}")
    print(f"- Saved: {output_path.resolve()}")
    return 0


def run_backtest_command(
    csv_path: Path,
    config_path: Path,
    trades_output: Path,
    equity_output: Path,
    monthly_output: Path,
    charts: bool,
    max_charts: int,
) -> int:
    config, frame = _load_enriched(csv_path, config_path)
    trades, curve = run_backtest(frame, config)
    stats = calculate_statistics(
        trades,
        curve,
        float(config["risk"]["initial_equity"]),
    )

    trades_output.parent.mkdir(parents=True, exist_ok=True)
    equity_output.parent.mkdir(parents=True, exist_ok=True)
    trade_log = TradeLogger.export(trades, trades_output)
    curve.to_csv(equity_output, index=False)
    MonthlyReport.export(trade_log, monthly_output)

    chart_paths = []
    if charts and not trade_log.empty:
        generator = TradeChartGenerator(max_charts=max_charts)
        chart_paths = generator.generate(
            frame,
            trade_log,
            Path("reports/trade_charts"),
        )

    if not trades.empty:
        monthly = (
            trade_log.assign(month=trade_log["entry_time"].dt.to_period("M").astype(str))
            .groupby("month")
            .size()
        )
        avg_month = float(monthly.mean())
        min_month = int(monthly.min())
        max_month = int(monthly.max())
    else:
        avg_month = 0.0
        min_month = 0
        max_month = 0

    print("NEXUS V2 v2.0.0-c")
    print(f"- Trades:          {stats['trades']:,}")
    print(f"- Wins:            {stats['wins']:,}")
    print(f"- Losses:          {stats['losses']:,}")
    print(f"- Win rate:        {stats['win_rate_pct']:.2f}%")
    print(f"- Profit factor:   {stats['profit_factor']:.4f}")
    print(f"- Net profit:      {stats['net_profit']:.2f}")
    print(f"- Return:          {stats['return_pct']:.2f}%")
    print(f"- Max drawdown:    {stats['max_drawdown_pct']:.2f}%")
    print(f"- Avg trade:       {stats['avg_trade']:.4f}")
    print(f"- Avg trades/month:{avg_month:.2f}")
    print(f"- Min/Max month:   {min_month}/{max_month}")
    print(f"- Trades saved:    {trades_output.resolve()}")
    print(f"- Equity saved:    {equity_output.resolve()}")
    print(f"- Monthly report:  {monthly_output.resolve()}")
    if charts:
        print(f"- Trade charts:    {len(chart_paths)} generated")
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "inspect":
            return run_inspect(args.csv_path, args.config, args.tail)
        if args.command == "signals":
            return run_signals(args.csv_path, args.config, args.output)
        if args.command == "backtest":
            return run_backtest_command(
                args.csv_path,
                args.config,
                args.trades_output,
                args.equity_output,
                args.monthly_output,
                args.charts,
                args.max_charts,
            )
    except (FileNotFoundError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
