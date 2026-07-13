# NEXUS V2 — v2.0.1-dev12

DEV12은 거래 수가 줄어드는 구간을 분석합니다.

## 출력 파일

```text
reports/trade_frequency.csv
reports/reject_reasons.csv
```

## Trade Frequency 단계

- total_candles
- indicator_ready
- rsi_pass
- adx_pass
- bollinger_touch
- valid_stop_and_targets
- executed_trades

각 단계에서 롱, 숏, 합계, 이전 단계 대비 통과율을 기록합니다.

## Reject Reasons

- indicator_not_ready
- rsi_filter
- adx_filter_after_rsi
- bollinger_not_touched
- invalid_stop_or_targets
- position_open_or_margin_limit

마지막 항목은 같은 방향 포지션 보유 또는 총 증거금 제한 때문에
실제 체결되지 않은 후보를 합산한 값입니다.

## 검증

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe nexus.py backtest .\data\BTCUSDT_15M.csv
```

기존 백테스트 수치는 동일해야 합니다.

## 커밋

```powershell
git add .
git commit -m "feat: add trade frequency analysis"
git push
```
