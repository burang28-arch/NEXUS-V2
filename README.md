# NEXUS V2 — v2.0.1-dev16

DEV16은 부분 익절을 제거하고 단일 목표가에서 전량 청산합니다.

## 설정

```yaml
risk:
  stop_loss_pct: 1.0

exit:
  take_profit_pct: 2.2
```

모든 수치는 설정 파일에서 관리하며 코드에 하드코딩하지 않습니다.

## 동작

### LONG

- 손절: 진입가 대비 -1.0%
- 익절: 진입가 대비 +2.2%
- 목표가 도달 시 100% 종료

### SHORT

- 손절: 진입가 대비 +1.0%
- 익절: 진입가 대비 -2.2%
- 목표가 도달 시 100% 종료

동일 봉에서 손절과 익절이 모두 닿으면 기존과 동일하게 손절을 먼저 처리합니다.

## 호환성

기존 CSV와 차트 코드 호환을 위해 `tp1_price`, `tp2_price` 열은 유지되며,
두 열 모두 동일한 단일 목표가를 기록합니다.

## 검증

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe nexus.py backtest .\data\BTCUSDT_15M.csv
```

## 커밋

```powershell
git add .
git commit -m "feat: close full position at configurable 2.2 percent target"
git push
```
