# NEXUS V2 — v2.0.1-dev20

DEV20은 RSI 다이버전스 진입에서 볼린저 밴드 터치 조건을 제거하고,
ADX 필터를 적용합니다.

## 진입 조건

### LONG

- L1 가격 저점 피벗: 좌 3 / 우 3
- L1 RSI ≤ 30
- L2 가격 저점 피벗: 좌 3 / 우 1
- L2 가격 < L1 가격
- L2 RSI ≥ L1 RSI + 8
- 신호 확정 봉 ADX ≤ 22
- 다음 봉 시가 시장가 진입

### SHORT

반대 조건:

- L1 RSI ≥ 70
- L2 가격 > L1 가격
- L2 RSI ≤ L1 RSI - 8
- 신호 확정 봉 ADX ≤ 22
- 다음 봉 시가 시장가 진입

볼린저 밴드는 진입 조건에 사용하지 않습니다.

## 청산

```yaml
risk:
  stop_loss_pct: 1.0

exit:
  tp1_pct: 2.0
  tp2_pct: 4.0
  tp1_fraction: 0.7
  tp2_fraction: 0.3
```

## 옵티마이저

볼린저 관련 항목은 제거했고 ADX를 추가했습니다.

```yaml
entry.adx_max:
  - 14
  - 16
  - 18
  - 20
  - 22
  - 25
  - 30
```

실행:

```powershell
.\.venv\Scripts\python.exe nexus.py optimize .\data\BTCUSDT_15M.csv
```

결과:

```text
reports\optimizer_results.csv
reports\best_strategy.yaml
```

## 검증

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe nexus.py backtest .\data\BTCUSDT_15M.csv
```

## 커밋

```powershell
git add .
git commit -m "feat: replace Bollinger confirmation with ADX filter"
git push
```
