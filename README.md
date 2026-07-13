# NEXUS V2 — v2.0.1-dev10

DEV10은 소형 순차 옵티마이저를 추가합니다.

## 최적화 대상

- ADX 최대값
- RSI 롱 기준
- RSI 숏 기준
- ATR 손절 버퍼

모든 조합을 한꺼번에 돌리지 않고, 각 변수를 순서대로 테스트합니다.
기본 설정에서는 총 16회 백테스트합니다.

## 실행

```powershell
.\.venv\Scripts\python.exe nexus.py optimize .\data\BTCUSDT_15M.csv
```

출력:

```text
reports\optimizer_results.csv
reports\best_strategy.yaml
```

## 검증

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

옵티마이저는 전체 데이터에서 시간이 걸릴 수 있습니다.

## 커밋

```powershell
git add .
git commit -m "feat: add sequential strategy optimizer"
git push
```
