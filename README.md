# NEXUS V2 — v2.0.1-dev4

DEV4는 계좌 상태와 포트폴리오 클래스만 추가합니다.

## 추가된 파일

```text
nexus/core/account.py
nexus/core/portfolio.py
tests/test_core_account.py
tests/test_core_portfolio.py
```

## 구현 범위

- 초기 잔고와 현재 잔고
- 실현·미실현 손익
- Equity
- 사용 증거금
- 가용 증거금
- 롱 1개와 숏 1개의 독립 보유
- 같은 방향 중복 포지션 방지

기존 `nexus/backtest.py`는 수정하지 않았습니다. 따라서 기존 백테스트 결과는 바뀌면 안 됩니다.

## 검증 명령

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
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
git commit -m "feat: add account and portfolio core models"
git push
```
