# NEXUS V2 — v2.0.1-dev7

DEV7은 백테스트 거래 로그를 분석하기 쉬운 CSV로 확장합니다.

## 추가 파일

```text
nexus/reports/trade_logger.py
tests/test_trade_logger.py
```

## 거래 로그 추가 열

- `trade_id`
- `result`
- `entry_month`
- `entry_date`
- `entry_hour_utc`
- `entry_weekday_utc`
- `duration_minutes`
- `pnl_on_notional_pct`
- `confirmation`
- `setup_summary`
- `exit_summary`

기존 진입, 청산, 손절, 수수료 및 손익 계산은 변경하지 않습니다.

## 검증

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe nexus.py backtest .\data\BTCUSDT_15M.csv
```

결과 파일:

```text
reports\trades.csv
reports\equity.csv
```

백테스트 기준값은 기존과 동일해야 합니다.

```text
Trades: 277
Win rate: 24.91%
Profit factor: 0.5231
Net profit: -5.21
```

## 커밋

```powershell
git add .
git commit -m "feat: add detailed trade logger"
git push
```
