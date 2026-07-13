# NEXUS V2 — v2.0.1-dev17

DEV17은 포지션 규모와 고정 손절·익절 설정만 변경합니다.

## 설정

```yaml
risk:
  initial_equity: 1000.0
  base_margin_pct: 3.0
  leverage: 30.0
  stop_loss_pct: 0.9

exit:
  take_profit_pct: 1.5
```

## 의미

- 총 자산: $1,000
- 1회 증거금: 자산의 3% = $30
- 레버리지: 30배
- 명목 포지션 규모: 약 $900
- 손절: 가격 기준 -0.9%
- 익절: 가격 기준 +1.5%
- 목표가 도달 시 100% 종료

롱과 숏에 대칭 적용됩니다.

## 검증

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe nexus.py backtest .\data\BTCUSDT_15M.csv
```

## 커밋

```powershell
git add .
git commit -m "tune: set 30x leverage with 0.9 stop and 1.5 target"
git push
```
