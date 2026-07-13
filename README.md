# NEXUS V2 — v2.0.1-dev3

DEV3는 기존 백테스트가 `nexus/core/position.py`의 `Position`을 실제로 사용하도록 연결한 작은 리팩터링입니다.

## 변경 범위

- `nexus/backtest.py` 내부의 중복 `Position` 클래스 제거
- `nexus.core.position.Position` import
- 부분 청산 시 `Position.reduce()` 사용
- TP1 완료 시 `Position.mark_tp1_done()` 사용

Broker, TradeRecord, Portfolio, 전략 조건은 건드리지 않았습니다.

## 검증

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe nexus.py backtest .\data\BTCUSDT_15M.csv
```

통과 기준:

```text
Trades: 277
Win rate: 24.91%
Profit factor: 0.5231
Net profit: -5.21
```

## 커밋

```powershell
git add .
git commit -m "refactor: use core Position in backtest"
git push
```
