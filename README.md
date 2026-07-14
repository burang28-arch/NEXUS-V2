# NEXUS V2 — v2.0.1-dev21

DEV21은 기존 옵티마이저가 선택한 최적값을 기본 전략 설정에 적용합니다.

## 적용값

```yaml
entry:
  strategy: rsi_divergence
  l1_rsi_long_max: 30.0
  l1_rsi_short_min: 75.0
  min_rsi_difference: 10.0
  pivot_left_bars: 3
  l1_right_bars: 2
  l2_right_bars: 1
  adx_max: 25.0
```

## 유지되는 리스크 및 청산 설정

```yaml
risk:
  initial_equity: 1000.0
  base_margin_pct: 3.0
  leverage: 30.0
  stop_loss_pct: 1.0

exit:
  tp1_pct: 2.0
  tp2_pct: 4.0
  tp1_fraction: 0.7
  tp2_fraction: 0.3
```

DEV21에서는 옵티마이저 구조를 변경하지 않습니다.
ADX 구간형 최적화는 DEV22에서 별도로 구현합니다.

## 검증

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe nexus.py backtest .\data\BTCUSDT_15M.csv
```

## 커밋

```powershell
git add .
git commit -m "tune: apply optimized divergence strategy parameters"
git push
```
