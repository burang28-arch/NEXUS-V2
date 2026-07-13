# NEXUS V2 — v2.0.1-dev19

## 진입 전략

### LONG
- L1 가격 Pivot Low: 왼쪽 3봉 / 오른쪽 3봉
- L1 RSI ≤ 30
- L2 가격 Pivot Low: 왼쪽 3봉 / 오른쪽 1봉으로 빠르게 확인
- L2 가격 < L1 가격
- L2 RSI ≥ L1 RSI + 8
- L2 봉이 Bollinger Lower Band를 터치해야 함
- L2 우측 1봉 확인 후 다음 봉 시가 시장가 진입

### SHORT
위 조건을 완전히 반대로 적용합니다.
- L1 RSI ≥ 70
- L2 가격 > L1 가격
- L2 RSI ≤ L1 RSI - 8
- L2 봉이 Bollinger Upper Band 터치

ADX는 더 이상 진입 조건이 아닙니다. 거래량과 캔들패턴은 기존처럼 포지션 크기 점수에만 사용됩니다.

## 리스크
```yaml
risk:
  initial_equity: 1000.0
  base_margin_pct: 3.0
  leverage: 30.0
  stop_loss_pct: 1.0
exit:
  tp1_pct: 2.0
  tp2_pct: 4.0
  tp1_fraction: 0.70
  tp2_fraction: 0.30
```

## 실행
```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe nexus.py inspect .\data\BTCUSDT_15M.csv
.\.venv\Scripts\python.exe nexus.py backtest .\data\BTCUSDT_15M.csv
.\.venv\Scripts\python.exe nexus.py optimize .\data\BTCUSDT_15M.csv
```

## 우선 최적화 추천
1. `min_rsi_difference`: 6 / 8 / 10 / 12
2. L1 RSI: 롱 25~35, 숏 65~75
3. `pivot_left_bars`: 2 / 3 / 4
4. `l1_right_bars`: 2 / 3 / 4
5. `l2_right_bars`: 1 / 2
6. Bollinger length/stddev
7. 마지막으로 SL, TP1, TP2

피벗과 RSI 조건부터 먼저 찾고, 청산 수치는 마지막에 조정하는 것을 권장합니다.

## 커밋
```powershell
git add .
git commit -m "feat: use RSI divergence entries with Bollinger confirmation"
git push
```
