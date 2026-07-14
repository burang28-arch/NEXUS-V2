# NEXUS V2 — v2.0.1-dev26

DEV25는 현재 옵티마이저 1위 설정을 기본 전략에 적용하고,
선택형 거래 검토 차트를 개선합니다.

## 적용된 기본 설정

```yaml
entry:
  l1_rsi_long_max: 30.0
  l1_rsi_short_min: 75.0
  min_rsi_difference: 10.0
  pivot_left_bars: 3
  l1_right_bars: 3
  l2_right_bars: 1
  adx_min: 20.0
  adx_max: 30.0

risk:
  stop_loss_pct: 0.8

exit:
  tp1_pct: 2.0
  tp2_pct: 3.0
  tp1_fraction: 0.7
  tp2_fraction: 0.3
```

## 차트 출력은 기본 OFF

일반 백테스트:

```powershell
.\.venv\Scripts\python.exe nexus.py backtest .\data\BTCUSDT_15M.csv
```

차트를 포함한 백테스트:

```powershell
.\.venv\Scripts\python.exe nexus.py backtest .\data\BTCUSDT_15M.csv --charts
```

그룹당 출력 수 변경:

```powershell
.\.venv\Scripts\python.exe nexus.py backtest .\data\BTCUSDT_15M.csv --charts --max-charts 20
```

`--max-charts 10`은 다음을 각각 10개씩 출력합니다.

- 최근 성공 거래 10개
- 최근 실패 거래 10개
- 전체 최근 거래 10개

총 최대 30장입니다.

## 저장 위치

```text
reports/trade_charts/
├── successful/
├── failed/
├── recent/
└── chart_index.csv
```

기존 폴더는 새 차트 실행 때 자동으로 비워져 오래된 사진이 섞이지 않습니다.

## 차트 표시 내용

- Gate 스타일의 어두운 거래소 화면
- 상승봉 녹색 / 하락봉 빨간색
- 신호 확정 봉
- 실제 진입 봉과 진입 가격
- SL / TP1 / TP2
- 실제 청산 위치와 청산 이유
- RSI 다이버전스 L1/L2 가격
- L1/L2 RSI 및 차이
- ADX
- 점수
- 보유 봉 수
- 순손익
- 진입 이유

## 검증

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe nexus.py backtest .\data\BTCUSDT_15M.csv --charts
```

## 커밋

```powershell
git add .
git commit -m "feat: apply best settings and add opt-in Gate-style trade charts"
git push
```


## DEV26 차트 개선

각 거래 이미지가 세 개의 패널로 구성됩니다.

```text
가격 차트: L1/L2, 가격 다이버전스, 진입/SL/TP/청산
RSI 차트: RSI 흐름, 30/70 기준선, L1/L2 RSI 연결선
ADX 차트: ADX 흐름, 허용 구간 20~30, 신호 시점 ADX
```

L1과 L2는 큰 라벨과 화살표로 표시되어 바로 구분할 수 있습니다.
