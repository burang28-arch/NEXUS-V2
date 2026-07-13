# NEXUS V2 — v2.0.1-dev1

첫 번째 코어 엔진 리팩터링 묶음입니다.

## 새로 분리된 파일

```text
nexus/core/
├── __init__.py
├── position.py
├── trade.py
└── broker.py
```

현재 기존 `nexus/backtest.py`는 그대로 유지되므로 기존 백테스트 명령은 계속 실행됩니다.

```powershell
.\.venv\Scripts\python.exe nexus.py backtest .\data\BTCUSDT_15M.csv
```

## 새 구조

- `Position`: 포지션 상태, 잔여 비율, PnL 계산
- `TradeRecord`: 완결된 거래 기록
- `BacktestBroker`: 수수료와 슬리피지 체결 계산
- `Fill`: 체결 가격, 명목가치, 수수료 기록

## 테스트

의존성을 업데이트한 뒤:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
```

이 커밋에서는 기존 엔진 동작을 바꾸지 않습니다. 다음 묶음에서 기존 `backtest.py`가 새 `Position`, `TradeRecord`, `BacktestBroker`를 실제로 사용하도록 연결합니다.

## Git 커밋

```powershell
git add .
git commit -m "refactor: add core position trade and broker"
git push
```
