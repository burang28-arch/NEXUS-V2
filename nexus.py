from __future__ import annotations

import argparse
import sys
from time import perf_counter
from pathlib import Path

from nexus.backtest import calculate_statistics, run_backtest
from nexus.config import load_config
from nexus.data import load_ohlcv_csv
from nexus.indicators import add_indicators
from nexus.optimizer import (
    SequentialOptimizer,
    load_optimizer_config,
    recommended_workers,
)
from nexus.signals import add_signal_columns, extract_signals
from nexus.runtime import (
    estimate_backtest_seconds,
    estimate_optimizer_seconds,
    format_duration,
    optimizer_plan,
    record_runtime,
)
from nexus.reports.monthly_report import MonthlyReport
from nexus.reports.signal_analysis import SignalAnalyzer
from nexus.reports.stop_analysis import StopAnalysis
from nexus.reports.stop_debug import StopDebugReport
from nexus.reports.trade_charts import TradeChartGenerator
from nexus.reports.trade_frequency import TradeFrequencyAnalyzer
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
        "--signal-analysis-output",
        type=Path,
        default=Path("reports/signal_analysis.csv"),
    )
    backtest_parser.add_argument(
        "--trade-frequency-output",
        type=Path,
        default=Path("reports/trade_frequency.csv"),
    )
    backtest_parser.add_argument(
        "--reject-reasons-output",
        type=Path,
        default=Path("reports/reject_reasons.csv"),
    )
    backtest_parser.add_argument(
        "--stop-analysis-output",
        type=Path,
        default=Path("reports/stop_analysis.csv"),
    )
    backtest_parser.add_argument(
        "--stop-debug-output",
        type=Path,
        default=Path("reports/stop_debug.csv"),
    )
    backtest_parser.add_argument(
        "--stop-debug-rows",
        type=int,
        default=200,
    )
    backtest_parser.add_argument(
        "--charts",
        action="store_true",
        help=(
            "Generate Gate-style charts for the latest successful, "
            "failed, and recent trades. Disabled by default."
        ),
    )
    backtest_parser.add_argument(
        "--max-charts",
        type=int,
        default=10,
        help="Number of charts per group. Default: 10",
    )


    optimize_parser = subparsers.add_parser(
        "optimize",
        help="Run a small sequential parameter optimizer.",
    )
    optimize_parser.add_argument("csv_path", type=Path)
    optimize_parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/strategy.yaml"),
    )
    optimize_parser.add_argument(
        "--optimizer-config",
        type=Path,
        default=Path("config/optimizer.yaml"),
    )
    optimize_parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/optimizer_results.csv"),
    )
    optimize_parser.add_argument(
        "--best-config-output",
        type=Path,
        default=Path("reports/best_strategy.yaml"),
    )
    optimize_parser.add_argument(
        "--yearly-output",
        type=Path,
        default=Path("reports/optimizer_yearly_results.csv"),
    )
    optimize_parser.add_argument(
        "--workers",
        type=int,
        default=recommended_workers(),
        help=(
            "Parallel optimizer processes. Default is hardware-aware; "
            "use 1 to disable multiprocessing."
        ),
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
    print("NEXUS V2 v2.0.1-dev26")
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
    print("NEXUS V2 v2.0.1-dev26")
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
    signal_analysis_output: Path,
    trade_frequency_output: Path,
    reject_reasons_output: Path,
    stop_analysis_output: Path,
    stop_debug_output: Path,
    stop_debug_rows: int,
    charts: bool,
    max_charts: int,
) -> int:
    command_started = perf_counter()
    raw_rows = len(load_ohlcv_csv(csv_path))
    estimate = estimate_backtest_seconds(raw_rows)

    print("NEXUS V2 v2.0.1-dev26")
    print(f"- Data rows:        {raw_rows:,}")
    print(f"- Estimated time:   {format_duration(estimate)}")

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
    SignalAnalyzer.export(trade_log, signal_analysis_output)
    TradeFrequencyAnalyzer.export(
        frame,
        trade_log,
        config,
        trade_frequency_output,
        reject_reasons_output,
    )
    StopAnalysis.export(frame, config, stop_analysis_output)
    StopDebugReport.export(
        frame,
        config,
        stop_debug_output,
        max_rows=stop_debug_rows,
    )

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

    print("NEXUS V2 v2.0.1-dev26")
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
    print(f"- Signal analysis: {signal_analysis_output.resolve()}")
    print(f"- Trade frequency: {trade_frequency_output.resolve()}")
    print(f"- Reject reasons:  {reject_reasons_output.resolve()}")
    print(f"- Stop analysis:   {stop_analysis_output.resolve()}")
    print(f"- Stop debug:      {stop_debug_output.resolve()}")
    if charts:
        print(
            f"- Trade charts:    {len(chart_paths)} generated "
            f"(successful/failed/recent)"
        )
        print(
            "- Chart folder:    "
            f"{Path('reports/trade_charts').resolve()}"
        )

    elapsed = perf_counter() - command_started
    record_runtime("backtest", elapsed, raw_rows)
    print(f"- Elapsed time:     {format_duration(elapsed)}")
    print(f"- Next estimate:    {format_duration(elapsed)}")
    return 0



def run_optimize_command(
    csv_path: Path,
    config_path: Path,
    optimizer_config_path: Path,
    output_path: Path,
    best_config_output: Path,
    yearly_output: Path,
    workers: int,
) -> int:
    command_started = perf_counter()
    strategy_config = load_config(config_path)
    optimizer_config = load_optimizer_config(optimizer_config_path)
    market = load_ohlcv_csv(csv_path)

    planned_runs, stage_sizes = optimizer_plan(optimizer_config)
    estimate = estimate_optimizer_seconds(
        rows=len(market),
        workers=workers,
        runs=planned_runs,
        stage_sizes=stage_sizes,
    )

    print("NEXUS V2 v2.0.1-dev26")
    print(f"- Workers:         {workers}")
    print(f"- Planned runs:    {planned_runs}")
    print(f"- Estimated time:  {format_duration(estimate)}")

    def show_progress(stage: int, total: int, parameter: str) -> None:
        elapsed = perf_counter() - command_started
        if stage > 0:
            projected_total = elapsed / stage * total
            remaining = max(0.0, projected_total - elapsed)
        else:
            remaining = None
        print(
            f"- Progress:        {stage}/{total} stages | "
            f"elapsed {format_duration(elapsed)} | "
            f"remaining {format_duration(remaining)} | "
            f"{parameter}"
        )

    optimizer = SequentialOptimizer(
        strategy_config,
        optimizer_config,
        workers=workers,
        progress_callback=show_progress,
    )
    results, best_config = optimizer.run(market)
    optimizer.export_results(results, output_path)
    optimizer.export_yearly_results(yearly_output)
    optimizer.export_best_config(best_config, best_config_output)

    print("NEXUS V2 v2.0.1-dev26")
    print(f"- Optimizer runs:  {len(results):,}")
    if not results.empty:
        valid = results.loc[results["objective"].map(lambda x: x != float("-inf"))]
        if not valid.empty:
            best = valid.iloc[0]
            print(f"- Best score:      {best['objective']:.4f}")
            print(f"- Best PF:         {best['profit_factor']:.4f}")
            print(f"- Best trades:     {int(best['trades']):,}")
            print(
                f"- Best ADX range:  "
                f"{best['adx_min']:.0f}-{best['adx_max']:.0f}"
            )
            print("- Top 10:")
            top = valid.head(10)
            for rank, (_, row) in enumerate(top.iterrows(), start=1):
                print(
                    f"  {rank:>2}. score={row['objective']:.4f} "
                    f"PF={row['profit_factor']:.4f} "
                    f"trades={int(row['trades'])} "
                    f"MDD={row['max_drawdown_pct']:.2f}% "
                    f"years={int(row['profitable_years'])}/"
                    f"{int(row['evaluated_years'])}"
                )
    print(
        f"- Cache hits:      indicators={optimizer.indicator_cache_hits}, "
        f"signals={optimizer.signal_cache_hits}"
    )
    print(f"- Results saved:   {output_path.resolve()}")
    print(f"- Yearly results:  {yearly_output.resolve()}")
    print(f"- Best config:     {best_config_output.resolve()}")

    elapsed = perf_counter() - command_started
    record_runtime(
        "optimize",
        elapsed,
        rows=len(market),
        workers=workers,
        runs=len(results),
    )
    print(f"- Elapsed time:     {format_duration(elapsed)}")
    print(f"- Next estimate:    {format_duration(elapsed)}")
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
                args.signal_analysis_output,
                args.trade_frequency_output,
                args.reject_reasons_output,
                args.stop_analysis_output,
                args.stop_debug_output,
                args.stop_debug_rows,
                args.charts,
                args.max_charts,
            )
        if args.command == "optimize":
            return run_optimize_command(
                args.csv_path,
                args.config,
                args.optimizer_config,
                args.output,
                args.best_config_output,
                args.yearly_output,
                args.workers,
            )
    except (FileNotFoundError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
