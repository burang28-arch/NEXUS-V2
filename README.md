# NEXUS V2 — v2.0.1-dev23

DEV23은 전략을 변경하지 않고 옵티마이저 실행 속도만 개선합니다.

## 추가된 속도 개선

### 1. 멀티프로세싱

같은 최적화 단계 안의 후보값을 여러 CPU 프로세스에서 동시에 실행합니다.

```powershell
.\.venv\Scripts\python.exe nexus.py optimize .\data\BTCUSDT_15M.csv --workers 10
```

`--workers 1`을 사용하면 기존처럼 단일 프로세스로 실행됩니다.

Core Ultra 7 155H + RAM 16GB 환경에서는 먼저 `8~10` 워커를 권장합니다.
12개 이상은 메모리 압박으로 오히려 느려질 수 있습니다.

### 2. Indicator Cache

RSI, ADX, ATR, 볼린저, 거래량 평균 등 지표 설정이 같으면 다시 계산하지 않습니다.

### 3. Signal Cache

SL, TP처럼 진입 조건과 관계없는 값만 바뀌면 RSI 다이버전스 신호를 다시 계산하지 않습니다.

## 단계형 최적화와 병렬 처리

최적화 단계 자체는 순서대로 진행됩니다.

```text
ADX 구간 선택
→ RSI 기준 선택
→ 피벗 선택
→ SL 선택
→ TP1 선택
→ TP2 선택
```

하지만 각 단계 안의 후보는 동시에 실행됩니다.

예:

```text
SL 단계
0.8 / 1.0 / 1.2 / 1.5 / 2.0
```

5개 후보를 최대 5개 프로세스가 병렬 백테스트합니다.

## 실행

자동 권장 워커:

```powershell
.\.venv\Scripts\python.exe nexus.py optimize .\data\BTCUSDT_15M.csv
```

Trevor-OMEN 권장 시작값:

```powershell
.\.venv\Scripts\python.exe nexus.py optimize .\data\BTCUSDT_15M.csv --workers 10
```

노트북이 버벅거리거나 메모리가 90% 이상이면:

```powershell
.\.venv\Scripts\python.exe nexus.py optimize .\data\BTCUSDT_15M.csv --workers 6
```

## 결과

기존과 동일합니다.

```text
reports/optimizer_results.csv
reports/optimizer_yearly_results.csv
reports/best_strategy.yaml
```

`optimizer_results.csv`에는 캐시 적중 여부도 기록됩니다.

```text
indicator_cache_hit
signal_cache_hit
```

## 검증

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## 커밋

```powershell
git add .
git commit -m "perf: parallelize optimizer and cache indicators and signals"
git push
```
