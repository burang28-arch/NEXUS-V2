# NEXUS V2 — v2.0.1-dev18

DEV18은 더 유리한 가격을 기다리는 지정가 진입과 고정 손절·익절을 적용합니다.

## 설정

```yaml
entry:
  order_type: limit
  limit_offset_pct: 0.3
  limit_expiry_bars: 2

risk:
  initial_equity: 1000.0
  base_margin_pct: 3.0
  leverage: 30.0
  stop_loss_pct: 1.0

exit:
  take_profit_pct: 1.5
```

## 진입 규칙

신호 봉이 마감된 후 다음 봉 시가를 기준 가격으로 사용합니다.

### LONG

```text
지정가 = 다음 봉 시가 × (1 - 0.3%)
```

### SHORT

```text
지정가 = 다음 봉 시가 × (1 + 0.3%)
```

다음 2개 봉 안에 지정가가 체결되지 않으면 주문을 취소합니다.

봉이 지정가를 갭으로 통과해 더 유리한 가격에서 시작하면 해당 시가로 체결합니다.
지정가 진입에는 추가적인 불리한 슬리피지를 적용하지 않으며, 청산 슬리피지는 기존대로 적용합니다.

## 청산

- 손절: 진입가 기준 1.0%
- 익절: 진입가 기준 1.5%
- 익절 시 전량 청산
- 같은 봉에서 손절과 익절이 모두 닿으면 손절 우선

지정가가 봉 중간에 체결된 경우, 그 봉에서는 손절만 보수적으로 인정하고
익절은 다음 봉부터 인정합니다. 봉 안의 가격 이동 순서를 알 수 없기 때문입니다.

## 분석 리포트

`trade_frequency.csv`에 다음 단계가 추가됩니다.

```text
limit_filled_within_expiry
```

`reject_reasons.csv`에는 다음 항목이 추가됩니다.

```text
limit_not_filled_within_expiry
```

## 검증

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe nexus.py backtest .\data\BTCUSDT_15M.csv
```

## 커밋

```powershell
git add .
git commit -m "feat: add configurable 0.3 percent limit entries"
git push
```
