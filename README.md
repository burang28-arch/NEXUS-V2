# NEXUS V2 — v2.0.1-dev2

DEV2는 Broker 연결만 수행합니다.

## 변경 사항

- `nexus/backtest.py`의 수수료 및 슬리피지 계산을 `nexus/core/broker.py`의 `BacktestBroker`로 연결
- 전략, Position 구조, Portfolio, 청산 규칙은 변경하지 않음
- 목표: 기존 백테스트 결과와 완전히 동일

## 테스트

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe nexus.py backtest .\data\BTCUSDT_15M.csv
```

기준 결과:

```text
Trades: 277
Win rate: 24.91%
Profit factor: 0.5231
Net profit: -5.21
```

## 커밋

```powershell
git add .
git commit -m "refactor: route backtest fills through broker"
git push
```
