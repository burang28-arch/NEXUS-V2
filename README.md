# NEXUS V2 — v2.0.1-dev9

DEV9은 월별 백테스트 요약 CSV를 생성합니다.

## 추가 파일

```text
nexus/reports/monthly_report.py
tests/test_monthly_report.py
```

## 출력 파일

```text
reports/monthly_report.csv
```

## 포함 항목

- month
- trades
- long_trades
- short_trades
- wins
- losses
- win_rate_pct
- profit_factor
- gross_profit
- gross_loss
- net_profit
- average_trade
- best_trade
- worst_trade
- average_holding_bars

## 검증

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe nexus.py backtest .\data\BTCUSDT_15M.csv
```

기존 백테스트 수치는 동일해야 합니다.

```text
Trades: 277
Win rate: 24.91%
Profit factor: 0.5231
Net profit: -5.21
```

## 커밋

```powershell
git add .
git commit -m "feat: add monthly performance report"
git push
```
