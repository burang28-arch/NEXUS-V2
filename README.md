# NEXUS V2 — v2.0.1-dev6

DEV6은 Execution 인터페이스만 추가합니다.

## 추가 파일

```text
nexus/core/execution.py
tests/test_core_execution.py
```

기존 `backtest.py`는 수정하지 않았습니다.

## 검증

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe nexus.py backtest .\data\BTCUSDT_15M.csv
```

기대 백테스트 기준:

```text
Trades: 277
Win rate: 24.91%
Profit factor: 0.5231
Net profit: -5.21
```

## 커밋

```powershell
git add .
git commit -m "feat: add execution engine interface"
git push
```
