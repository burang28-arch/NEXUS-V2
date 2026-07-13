from pathlib import Path

import pandas as pd
import pytest

from nexus.reports.trade_logger import TradeLogger


def sample_trades() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "side": "LONG",
                "signal_time": "2026-01-01T00:00:00Z",
                "entry_time": "2026-01-01T00:15:00Z",
                "exit_time": "2026-01-01T01:15:00Z",
                "entry_price": 100.0,
                "stop_price": 95.0,
                "tp1_price": 105.0,
                "tp2_price": 110.0,
                "exit_price": 110.0,
                "exit_reason": "TP2",
                "score": 2,
                "size_multiplier": 1.5,
                "margin_used": 30.0,
                "notional": 100.0,
                "quantity": 1.0,
                "gross_pnl": 10.0,
                "fees": 0.1,
                "net_pnl": 9.9,
                "return_on_margin_pct": 33.0,
                "holding_bars": 4,
                "adx": 18.0,
                "rsi": 30.0,
                "atr": 2.0,
                "volume_score": 1,
                "candle_score": 1,
            }
        ]
    )


def test_prepare_adds_analysis_columns() -> None:
    log = TradeLogger.prepare(sample_trades())

    assert log.loc[0, "trade_id"] == 1
    assert log.loc[0, "result"] == "WIN"
    assert log.loc[0, "entry_month"] == "2026-01"
    assert log.loc[0, "entry_hour_utc"] == 0
    assert log.loc[0, "duration_minutes"] == pytest.approx(60.0)
    assert log.loc[0, "confirmation"] == "VOLUME+CANDLE"
    assert log.loc[0, "pnl_on_notional_pct"] == pytest.approx(9.9)


def test_export_creates_csv(tmp_path: Path) -> None:
    output = tmp_path / "trades.csv"
    TradeLogger.export(sample_trades(), output)

    assert output.exists()
    saved = pd.read_csv(output)
    assert "trade_id" in saved.columns
    assert saved.loc[0, "result"] == "WIN"
