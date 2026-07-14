# -*- coding: utf-8 -*-
"""
BARAM 2026 (제3회 풍력발전량 예측 AI 경진대회) - 다양성 앙상블 베이스라인

사용법 (데이터 폴더가 C:\\Users\\evoll\\Downloads\\open 인 경우):
    python predict_wind.py --data-dir "C:\\Users\\evoll\\Downloads\\open" --out submission.csv

필요 패키지:
    pip install pandas numpy scikit-learn lightgbm

설계 원칙
- 평가지표가 NMAE(평균 예측오차율) 기반이므로 MAE(L1) 목적함수로 학습.
- "다양성"을 세 축으로 확보:
    1) 모델 계열 다양성: LightGBM(gbdt/dart), HistGradientBoosting, ExtraTrees
    2) 시드 다양성: 계열별 복수 시드
    3) 피처 서브샘플링 다양성: 모델별 colsample/max_features 차등
- 풍력단지 그룹 컬럼이 있으면 그룹별로 개별 모델 학습.
- 예측값은 [0, 학습 최대치*1.05]로 클리핑 (음수 발전량 방지).
"""

import argparse
import glob
import os
import re
import sys

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# 컬럼 자동 탐지
# ---------------------------------------------------------------------------

TARGET_PATTERNS = [
    r"발전량", r"^target$", r"power", r"generation", r"amount", r"energy", r"^y$",
]
DATETIME_PATTERNS = [
    r"일시", r"날짜", r"시간", r"datetime", r"date", r"^time$", r"timestamp", r"^dt$",
]
ID_PATTERNS = [r"^id$", r"^ID$", r"^index$"]
GROUP_PATTERNS = [r"그룹", r"단지", r"group", r"farm", r"plant", r"site", r"turbine"]


def find_col(cols, patterns):
    for pat in patterns:
        for c in cols:
            if re.search(pat, str(c), re.IGNORECASE):
                return c
    return None


def load_csv(path):
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# 피처 엔지니어링
# ---------------------------------------------------------------------------

def add_time_features(df, dt_col):
    dt = pd.to_datetime(df[dt_col], errors="coerce")
    df["_month"] = dt.dt.month
    df["_day"] = dt.dt.day
    df["_hour"] = dt.dt.hour
    df["_dayofweek"] = dt.dt.dayofweek
    df["_dayofyear"] = dt.dt.dayofyear
    # 주기성 인코딩
    df["_hour_sin"] = np.sin(2 * np.pi * df["_hour"] / 24)
    df["_hour_cos"] = np.cos(2 * np.pi * df["_hour"] / 24)
    df["_doy_sin"] = np.sin(2 * np.pi * df["_dayofyear"] / 365)
    df["_doy_cos"] = np.cos(2 * np.pi * df["_dayofyear"] / 365)
    df["_month_sin"] = np.sin(2 * np.pi * df["_month"] / 12)
    df["_month_cos"] = np.cos(2 * np.pi * df["_month"] / 12)
    return df


def add_wind_features(df):
    """풍속/풍향 컬럼이 있으면 물리 기반 파생 피처 추가."""
    cols = list(df.columns)
    ws_col = find_col(cols, [r"풍속", r"wind.?speed", r"^ws"])
    wd_col = find_col(cols, [r"풍향", r"wind.?dir", r"^wd"])
    if ws_col is not None:
        ws = pd.to_numeric(df[ws_col], errors="coerce")
        # 발전량은 풍속의 3제곱에 비례 (P ∝ v^3)
        df["_ws_sq"] = ws ** 2
        df["_ws_cube"] = ws ** 3
        if wd_col is not None:
            wd = pd.to_numeric(df[wd_col], errors="coerce")
            rad = np.deg2rad(wd)
            df["_wind_u"] = ws * np.cos(rad)
            df["_wind_v"] = ws * np.sin(rad)
    if wd_col is not None:
        wd = pd.to_numeric(df[wd_col], errors="coerce")
        rad = np.deg2rad(wd)
        df["_wd_sin"] = np.sin(rad)
        df["_wd_cos"] = np.cos(rad)
    return df


def build_features(train, test, target_col, dt_col, id_col):
    drop_cols = {target_col}
    if id_col:
        drop_cols.add(id_col)

    for df in (train, test):
        if dt_col and dt_col in df.columns:
            add_time_features(df, dt_col)
        add_wind_features(df)
    if dt_col:
        drop_cols.add(dt_col)

    feat_cols = [c for c in test.columns if c not in drop_cols and c in train.columns]

    # 범주형은 코드로 변환 (train/test 합쳐서 일관되게)
    for c in feat_cols:
        if train[c].dtype == object:
            both = pd.concat([train[c], test[c]], axis=0).astype("category")
            train[c] = pd.Categorical(train[c], categories=both.cat.categories).codes
            test[c] = pd.Categorical(test[c], categories=both.cat.categories).codes
        else:
            train[c] = pd.to_numeric(train[c], errors="coerce")
            test[c] = pd.to_numeric(test[c], errors="coerce")

    return feat_cols


# ---------------------------------------------------------------------------
# 다양성 앙상블
# ---------------------------------------------------------------------------

def make_models():
    """모델 계열 x 시드 x 피처서브샘플 다양성을 가진 앙상블 구성."""
    models = []

    try:
        import lightgbm as lgb

        for seed, colsample, boosting in [
            (42, 0.8, "gbdt"),
            (202, 0.6, "gbdt"),
            (777, 0.9, "gbdt"),
            (1234, 0.7, "dart"),
        ]:
            models.append((
                f"lgbm_{boosting}_s{seed}",
                lgb.LGBMRegressor(
                    objective="l1",  # NMAE에 맞춘 MAE 목적함수
                    boosting_type=boosting,
                    n_estimators=1200,
                    learning_rate=0.03,
                    num_leaves=63,
                    colsample_bytree=colsample,
                    subsample=0.8,
                    subsample_freq=1,
                    min_child_samples=30,
                    random_state=seed,
                    n_jobs=-1,
                    verbose=-1,
                ),
            ))
    except ImportError:
        print("[warn] lightgbm 미설치 - sklearn 모델만 사용합니다.", file=sys.stderr)

    from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor

    for seed, max_feat in [(7, 0.8), (99, 0.6)]:
        models.append((
            f"hgb_s{seed}",
            HistGradientBoostingRegressor(
                loss="absolute_error",
                max_iter=800,
                learning_rate=0.05,
                max_leaf_nodes=63,
                max_features=max_feat,
                random_state=seed,
            ),
        ))

    models.append((
        "extratrees_s3",
        ExtraTreesRegressor(
            n_estimators=500,
            max_features=0.7,
            min_samples_leaf=5,
            random_state=3,
            n_jobs=-1,
        ),
    ))

    return models


def fit_predict_group(X_tr, y_tr, X_te):
    """한 그룹(또는 전체)에 대해 앙상블 학습 후 평균 예측 반환."""
    med = X_tr.median(numeric_only=True)
    X_tr = X_tr.fillna(med)
    X_te = X_te.fillna(med)

    preds = []
    for name, model in make_models():
        model.fit(X_tr, y_tr)
        p = model.predict(X_te)
        preds.append(p)
        print(f"    - {name}: mean={p.mean():.2f}")

    ens = np.mean(preds, axis=0)
    cap = float(y_tr.max()) * 1.05
    return np.clip(ens, 0.0, cap)


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="open", help="train/test/sample_submission CSV가 있는 폴더")
    ap.add_argument("--out", default="submission.csv")
    args = ap.parse_args()

    d = args.data_dir

    def locate(keyword):
        hits = sorted(glob.glob(os.path.join(d, f"*{keyword}*.csv")))
        return hits[0] if hits else None

    train_path = locate("train")
    test_path = locate("test")
    sub_path = locate("sample_submission") or locate("submission")

    if not (train_path and test_path and sub_path):
        print(f"[error] {d} 에서 train/test/sample_submission CSV를 찾지 못했습니다.", file=sys.stderr)
        print(f"  발견된 파일: {os.listdir(d) if os.path.isdir(d) else '(폴더 없음)'}", file=sys.stderr)
        sys.exit(1)

    print(f"train: {train_path}\ntest: {test_path}\nsample_submission: {sub_path}")

    train = load_csv(train_path)
    test = load_csv(test_path)
    sub = load_csv(sub_path)

    cols = list(train.columns)
    # 타깃: train에만 있는 컬럼 우선, 없으면 패턴 매칭
    only_in_train = [c for c in cols if c not in test.columns]
    target_col = find_col(only_in_train, TARGET_PATTERNS) or (
        only_in_train[-1] if only_in_train else find_col(cols, TARGET_PATTERNS)
    )
    dt_col = find_col(cols, DATETIME_PATTERNS)
    id_col = find_col(cols, ID_PATTERNS)
    group_col = find_col([c for c in cols if c != target_col], GROUP_PATTERNS)

    print(f"target={target_col}, datetime={dt_col}, id={id_col}, group={group_col}")
    if target_col is None:
        print("[error] 타깃 컬럼을 찾지 못했습니다. 스크립트 상단 TARGET_PATTERNS를 수정하세요.", file=sys.stderr)
        sys.exit(1)

    train = train.dropna(subset=[target_col]).reset_index(drop=True)
    feat_cols = build_features(train, test, target_col, dt_col, id_col)
    print(f"피처 {len(feat_cols)}개: {feat_cols}")

    y = pd.to_numeric(train[target_col], errors="coerce")
    test_pred = np.zeros(len(test))

    if group_col and group_col in feat_cols and test[group_col].nunique() > 1:
        # 풍력단지 그룹별 개별 모델 (그룹 간 설비용량/특성 차이 반영)
        for g in sorted(test[group_col].dropna().unique()):
            tr_mask = train[group_col] == g
            te_mask = test[group_col] == g
            if tr_mask.sum() == 0:
                tr_mask = train[group_col].notna()
            print(f"[group {g}] train={tr_mask.sum()}, test={te_mask.sum()}")
            test_pred[te_mask.values] = fit_predict_group(
                train.loc[tr_mask, feat_cols], y[tr_mask], test.loc[te_mask, feat_cols]
            )
    else:
        print("[전체 데이터 단일 학습]")
        test_pred = fit_predict_group(train[feat_cols], y, test[feat_cols])

    # sample_submission의 마지막(또는 타깃 이름과 매칭되는) 컬럼에 예측값 기록
    pred_col = find_col(sub.columns, TARGET_PATTERNS) or sub.columns[-1]
    sub[pred_col] = test_pred
    sub.to_csv(args.out, index=False, encoding="utf-8-sig")
    print(f"\n완료: {args.out} ({len(sub)} rows, 예측 컬럼='{pred_col}')")
    print(sub.head())


if __name__ == "__main__":
    main()
