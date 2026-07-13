# NEXUS V2 — v2.0.1-dev13

DEV13은 setup 후보가 손절 및 목표가 검증에서 탈락하는 이유를 분석합니다.

## 출력

```text
reports/stop_analysis.csv
```

## 사유

- valid
- no_next_open
- stop_missing
- stop_wrong_side
- tp1_wrong_side
- tp2_wrong_side

전략과 손절 계산 방식은 변경하지 않습니다.

## 검증

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe nexus.py backtest .\data\BTCUSDT_15M.csv
```

## 커밋

```powershell
git add .
git commit -m "feat: add stop and target validation analysis"
git push
```
