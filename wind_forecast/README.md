# BARAM 2026 풍력발전량 예측 - 다양성 앙상블 베이스라인

제3회 풍력발전량 예측 AI 경진대회(Dacon 236727)용 예측 파이프라인입니다.

## 실행 방법 (로컬 PC)

데이터 폴더가 `C:\Users\evoll\Downloads\open` 라면:

```bat
pip install pandas numpy scikit-learn lightgbm
python predict_wind.py --data-dir "C:\Users\evoll\Downloads\open" --out submission.csv
```

실행이 끝나면 현재 폴더에 `submission.csv`가 생성됩니다.

## 특징

- **NMAE 최적화**: 대회 평가지표(1-NMAE)에 맞춰 모든 모델이 MAE(L1) 목적함수로 학습
- **다양성 앙상블** (7개 모델 평균):
  - 모델 계열: LightGBM gbdt ×3, LightGBM dart ×1, HistGradientBoosting ×2, ExtraTrees ×1
  - 시드 다양성: 계열별 서로 다른 random seed
  - 피처 다양성: 모델별 colsample/max_features 0.6~0.9 차등
- **그룹별 학습**: 풍력단지 그룹 컬럼이 감지되면 3개 그룹 각각 개별 모델 학습
- **물리 기반 피처**: 풍속 2·3제곱(P ∝ v³), 풍향 벡터 분해(u/v), 시간 주기성(sin/cos)
- **자동 컬럼 탐지**: 한글/영문 컬럼명(발전량, 일시, 풍속, 그룹 등) 자동 인식
- **안전장치**: 음수 예측 클리핑, cp949/utf-8 인코딩 자동 처리

## 컬럼이 자동 인식되지 않을 때

스크립트 상단의 `TARGET_PATTERNS`, `DATETIME_PATTERNS`, `GROUP_PATTERNS`에
실제 컬럼명 패턴을 추가하면 됩니다.
