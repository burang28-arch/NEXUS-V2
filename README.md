# NEXUS V2 — v2.0.1-dev14

DEV14는 손절 계산값을 실제 숫자로 확인하는 디버그 CSV를 생성합니다.

## 출력 파일

```text
reports/stop_debug.csv
```

## 주요 열

- side
- next_open_raw
- entry_after_slippage
- signal_high
- signal_low
- swing_price
- atr
- atr_buffer
- stop_price
- stop_distance
- is_valid
- reason
- swing_vs_entry
- reference_vs_entry

기본적으로 잘못된 후보부터 최대 200개를 저장합니다.

## 실행

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe nexus.py backtest .\data\BTCUSDT_15M.csv
```

더 많이 출력:

```powershell
.\.venv\Scripts\python.exe nexus.py backtest .\data\BTCUSDT_15M.csv --stop-debug-rows 1000
```

전략과 손절 계산 로직은 변경하지 않습니다.

## 커밋

```powershell
git add .
git commit -m "feat: add stop calculation debug report"
git push
```
