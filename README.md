# NEXUS V2 — v2.0.1-dev11

DEV11은 거래 성과를 방향, 점수, ADX 구간, RSI 구간별로 요약합니다.

## 추가 파일

```text
nexus/reports/signal_analysis.py
tests/test_signal_analysis.py
```

## 출력 파일

```text
reports/signal_analysis.csv
```

## 분석 항목

- LONG / SHORT
- Score 0 / 1 / 2
- ADX 구간
- RSI 구간

각 그룹마다 다음 값을 출력합니다.

- trades
- wins
- losses
- win_rate_pct
- profit_factor
- gross_profit
- gross_loss
- net_profit
- average_trade

전략과 파라미터는 변경하지 않습니다.

## 검증

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe nexus.py backtest .\data\BTCUSDT_15M.csv
```

생성 파일:

```text
reports\signal_analysis.csv
```

기존 백테스트 결과는 동일해야 합니다.

## 커밋

```powershell
git add .
git commit -m "feat: add signal performance analyzer"
git push
```
