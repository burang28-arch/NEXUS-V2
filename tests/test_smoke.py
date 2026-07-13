from pathlib import Path

import pandas as pd

from nexus.config import load_config
from nexus.data import load_ohlcv_csv
from nexus.indicators import add_indicators


def test_load_and_calculate(tmp_path: Path) -> None:
    csv_path = tmp_path / "sample.csv"
    rows = []
    start = 1_700_000_000_000

    for index in range(80):
        price = 30_000 + index * 5
        rows.append(
            {
                "open_time": start + index * 900_000,
                "open": price,
                "high": price + 20,
                "low": price - 20,
                "close": price + 5,
                "volume": 100 + index,
            }
        )

    pd.DataFrame(rows).to_csv(csv_path, index=False)
    config = load_config(Path("config/strategy.yaml"))
    frame = add_indicators(load_ohlcv_csv(csv_path), config)

    assert len(frame) == 80
    assert {"rsi", "atr", "adx", "bb_lower", "bb_upper"}.issubset(frame.columns)
    assert frame["atr"].notna().sum() > 0
