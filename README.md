# NEXUS V2 — v2.0.1-dev5

DEV5는 기존 백테스트의 계좌 및 증거금 관리를 `Account`와 `Portfolio`에 연결합니다.

## 변경 범위

- `nexus/backtest.py`
  - 독립 `equity` 변수 대신 `portfolio.account.equity` 사용
  - 롱·숏 상태를 `Portfolio`에서 관리
  - 진입 시 `Portfolio.open_position()`
  - 종료 시 `Portfolio.close_position()`
- `nexus/core/portfolio.py`
  - 한쪽 포지션 종료 시 반대쪽 증거금이 정확히 유지되도록 수정
- `tests/test_core_portfolio.py`
  - 헤지 상태에서 한쪽 포지션 종료 테스트 추가

전략 조건, TP, 손절, 수수료, 슬리피지 계산은 변경하지 않습니다.

## 검증

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe nexus.py backtest .\data\BTCUSDT_15M.csv
```

기대 기준:

```text
Trades: 277
Win rate: 24.91%
Profit factor: 0.5231
Net profit: -5.21
```

## 커밋

```powershell
git add .
git commit -m "refactor: manage backtest positions through Portfolio"
git push
```
