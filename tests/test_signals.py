from pathlib import Path

import pandas as pd

from nexus.config import load_config
from nexus.data import load_ohlcv_csv
from nexus.indicators import add_indicators
from nexus.signals import add_signal_columns


def test_signal_columns_exist(tmp_path: Path) -> None:
    csv_path = tmp_path / "sample.csv"
    rows = []
    start = 1_700_000_000_000

    for index in range(120):
        base = 30_000 + (index % 20 - 10) * 20
        rows.append(
            {
                "open_time": start + index * 900_000,
                "open": base,
                "high": base + 60,
                "low": base - 60,
                "close": base + (20 if index % 2 == 0 else -20),
                "volume": 100 + index,
            }
        )

    pd.DataFrame(rows).to_csv(csv_path, index=False)

    config = load_config(Path("config/strategy.yaml"))
    frame = load_ohlcv_csv(csv_path)
    frame = add_indicators(frame, config)
    frame = add_signal_columns(frame, config)

    required = {
        "long_setup",
        "short_setup",
        "volume_score",
        "long_candle_score",
        "short_candle_score",
        "long_stop",
        "short_stop",
        "signal",
        "score",
        "size_multiplier",
        "stop_price",
    }
    assert required.issubset(frame.columns)
