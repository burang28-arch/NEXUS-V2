# NEXUS V2 — v2.0.1-dev15

DEV15 changes risk and profit targets to configurable entry-based percentages.

## Current levels

- Stop Loss: 1.0%
- TP1: 2.0%, close 70%
- TP2: 4.0%, close remaining 30%

LONG: entry -1%, +2%, +4%.
SHORT: entry +1%, -2%, -4%.

No value is hardcoded in the execution logic. Settings are in `config/strategy.yaml`:

```yaml
risk:
  stop_loss_pct: 1.0
exit:
  tp1_pct: 2.0
  tp2_pct: 4.0
  tp1_fraction: 0.70
  tp2_fraction: 0.30
```

## Verify

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe nexus.py backtest .\data\BTCUSDT_15M.csv
```

## Commit

```powershell
git add .
git commit -m "feat: use configurable fixed stop and profit targets"
git push
```
