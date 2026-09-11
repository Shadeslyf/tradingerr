"""
Walk-Forward Training Pipeline for Nifty50 Market Regime Classification
========================================================================
Strategy: 2-month TRAIN → 1-month TEST → slide forward by 1 month → repeat

This script:
  1. Loads the raw Nifty50 2-year 1-min CSV
  2. Runs the full feature + labeling pipeline on each window
  3. Trains an XGBoost model on 2 months, evaluates on the next 1 month
  4. Saves per-fold metrics and the best model

Usage:
    cd /Users/vishal/Desktop/tradingggg
    source venv/bin/activate
    python scripts/walk_forward_train.py
"""

import os
import sys
import joblib
import warnings
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta

import numpy as np
import pandas as pd
import xgboost as xgb
from loguru import logger
from sklearn.metrics import (
    f1_score,
    precision_score,
    recall_score,
    accuracy_score,
    confusion_matrix,
)

warnings.filterwarnings("ignore")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.features.feature_pipeline import FeaturePipeline
from app.ml.labeling import RegimeLabeler

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
RAW_CSV      = "data/Nifty50_2Years_1Min.csv"
RESULTS_DIR  = "data/walk_forward_results"
MODELS_DIR   = "models/walk_forward"
TRAIN_MONTHS = 3   # months to train on  ← expanded from 2
TEST_MONTHS  = 1   # months to test on
STEP_MONTHS  = 1   # slide forward by this many months each fold

# Labeling params — 3-class mode
LABEL_HORIZON     = 60    # 60-bar (1-min) forward window
THRESHOLD_PCT     = 0.1   # % move to call BULLISH or BEARISH (symmetric)
NUM_CLASSES       = 3

# XGBoost params
XGB_PARAMS = {
    "objective":        "multi:softprob",
    "num_class":        3,
    "eval_metric":      "mlogloss",
    "max_depth":        6,
    "learning_rate":    0.04,
    "n_estimators":     300,
    "subsample":        0.8,
    "colsample_bytree": 0.7,
    "min_child_weight": 5,
    "reg_alpha":        0.1,    # L1 regularisation — prunes noisy features
    "reg_lambda":       1.5,    # L2 regularisation
    "use_label_encoder": False,
    "random_state":     42,
    "verbosity":        0,
}

REGIME_NAMES = {
    0: "BULLISH",
    1: "RANGE",
    2: "BEARISH",
}


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def load_raw_data(csv_path: str) -> pd.DataFrame:
    logger.info(f"Loading raw data from: {csv_path}")
    df = pd.read_csv(csv_path)
    df.columns = [c.strip().lower() for c in df.columns]

    # Detect timestamp column
    ts_col = next(
        (c for c in df.columns if c in ("time", "date", "datetime", "timestamp")),
        df.columns[0],
    )
    df.rename(columns={ts_col: "timestamp"}, inplace=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=False)

    # Strip timezone for consistent slicing
    if df["timestamp"].dt.tz is not None:
        df["timestamp"] = df["timestamp"].dt.tz_localize(None)

    df.sort_values("timestamp", inplace=True)
    df.reset_index(drop=True, inplace=True)

    for col in ("open", "high", "low", "close"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if "volume" not in df.columns:
        df["volume"] = 0

    # Filter to market hours 09:15 – 15:30
    h, m = df["timestamp"].dt.hour, df["timestamp"].dt.minute
    market_open  = (h > 9)  | ((h == 9)  & (m >= 15))
    market_close = (h < 15) | ((h == 15) & (m <= 30))
    df = df[market_open & market_close].reset_index(drop=True)

    logger.info(
        f"Loaded {len(df):,} 1-min bars  |  "
        f"{df['timestamp'].min().date()} to {df['timestamp'].max().date()}"
    )
    return df


def build_features_and_labels(df: pd.DataFrame):
    if len(df) < 200:
        return None
    try:
        feats = FeaturePipeline.generate_features(df.copy(), options_ohlcv=None)
        if feats.empty:
            return None
        labeled = RegimeLabeler.apply_3class_regime_labeling(
            feats,
            horizon=LABEL_HORIZON,
            threshold_pct=THRESHOLD_PCT,
        )
        labeled = labeled.dropna(subset=["label"])
        labeled["label"] = labeled["label"].astype(int)
        return labeled if not labeled.empty else None
    except Exception as e:
        logger.warning(f"Feature/label pipeline failed: {e}")
        return None


def prepare_xy(df: pd.DataFrame):
    drop_cols = [c for c in ("label", "timestamp", "symbol", "token", "exchange") if c in df.columns]
    X = df.drop(columns=drop_cols, errors="ignore")
    y = df["label"].astype(int) - 1   # shift 1-3 → 0-2
    return X, y


def train_model(X_train, y_train):
    # Ensure all 3 classes are present (inject mean-row dummies for missing classes)
    present = set(y_train.unique())
    missing = set(range(NUM_CLASSES)) - present
    if missing:
        dummy_X = pd.DataFrame([X_train.mean()] * len(missing), columns=X_train.columns)
        dummy_y = pd.Series(list(missing))
        X_train = pd.concat([X_train, dummy_X], ignore_index=True)
        y_train = pd.concat([y_train, dummy_y], ignore_index=True)

    model = xgb.XGBClassifier(**XGB_PARAMS)
    model.fit(X_train, y_train, verbose=False)
    return model


def evaluate(model, X_test, y_test, fold_id: str) -> dict:
    y_pred = model.predict(X_test)
    acc  = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, average="macro", zero_division=0)
    rec  = recall_score(y_test, y_pred, average="macro", zero_division=0)
    f1   = f1_score(y_test, y_pred, average="macro", zero_division=0)
    cm   = confusion_matrix(y_test, y_pred, labels=list(range(NUM_CLASSES)))
    per_class_f1 = f1_score(y_test, y_pred, average=None, zero_division=0, labels=list(range(NUM_CLASSES)))
    per_class = {REGIME_NAMES[i]: round(float(per_class_f1[i]), 4) for i in range(NUM_CLASSES)}

    logger.info(
        f"[{fold_id}]  Acc={acc:.4f}  Prec={prec:.4f}  Rec={rec:.4f}  F1={f1:.4f}  "
        f"| BULL={per_class['BULLISH']:.3f} RANGE={per_class['RANGE']:.3f} BEAR={per_class['BEARISH']:.3f}"
    )
    return {
        "fold":             fold_id,
        "accuracy":         round(acc, 4),
        "precision":        round(prec, 4),
        "recall":           round(rec, 4),
        "f1_macro":         round(f1, 4),
        "per_class_f1":     per_class,
        "confusion_matrix": cm.tolist(),
    }


# ─────────────────────────────────────────────────────────────
# MAIN WALK-FORWARD LOOP
# ─────────────────────────────────────────────────────────────

def run_walk_forward():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)

    raw_df   = load_raw_data(RAW_CSV)
    min_date = raw_df["timestamp"].min().normalize()
    max_date = raw_df["timestamp"].max().normalize()

    logger.info(
        f"Walk-Forward Config: TRAIN={TRAIN_MONTHS}mo  TEST={TEST_MONTHS}mo  "
        f"STEP={STEP_MONTHS}mo  |  Data: {min_date.date()} to {max_date.date()}"
    )

    # Build fold windows
    folds = []
    train_start = min_date
    while True:
        train_end  = train_start + relativedelta(months=TRAIN_MONTHS)
        test_start = train_end
        test_end   = test_start + relativedelta(months=TEST_MONTHS)
        if test_end > max_date + relativedelta(days=1):
            break
        folds.append((train_start, train_end, test_start, test_end))
        train_start += relativedelta(months=STEP_MONTHS)

    logger.info(f"Total folds planned: {len(folds)}")

    all_metrics  = []
    best_f1      = -1.0
    best_model   = None
    best_fold_id = None

    for fold_idx, (tr_s, tr_e, te_s, te_e) in enumerate(folds):
        fold_id = (
            f"Fold_{fold_idx+1:02d}__"
            f"Train_{tr_s.date()}_{tr_e.date()}__"
            f"Test_{te_s.date()}_{te_e.date()}"
        )
        logger.info(f"\n{'='*72}")
        logger.info(f"  {fold_id}")
        logger.info(f"{'='*72}")

        train_raw = raw_df[(raw_df["timestamp"] >= tr_s) & (raw_df["timestamp"] < tr_e)].copy()
        test_raw  = raw_df[(raw_df["timestamp"] >= te_s) & (raw_df["timestamp"] < te_e)].copy()

        logger.info(f"  Train bars: {len(train_raw):,}  |  Test bars: {len(test_raw):,}")

        if len(train_raw) < 500 or len(test_raw) < 100:
            logger.warning("  Not enough data — skipping fold.")
            continue

        logger.info("  Building TRAIN features & labels...")
        train_df = build_features_and_labels(train_raw)
        if train_df is None or len(train_df) < 50:
            logger.warning("  TRAIN features empty — skipping.")
            continue

        logger.info("  Building TEST features & labels...")
        test_df = build_features_and_labels(test_raw)
        if test_df is None or len(test_df) < 20:
            logger.warning("  TEST features empty — skipping.")
            continue

        X_train, y_train = prepare_xy(train_df)
        X_test,  y_test  = prepare_xy(test_df)

        common = list(set(X_train.columns) & set(X_test.columns))
        if len(common) < 5:
            logger.warning("  Too few common feature columns — skipping.")
            continue
        X_train, X_test = X_train[common], X_test[common]

        logger.info(f"  TRAIN labels (0-6): {y_train.value_counts().sort_index().to_dict()}")
        logger.info(f"  TEST  labels (0-6): {y_test.value_counts().sort_index().to_dict()}")

        logger.info("  Training XGBoost...")
        model = train_model(X_train, y_train)

        metrics = evaluate(model, X_test, y_test, fold_id)
        metrics.update({
            "train_start": str(tr_s.date()),
            "train_end":   str(tr_e.date()),
            "test_start":  str(te_s.date()),
            "test_end":    str(te_e.date()),
            "train_rows":  len(X_train),
            "test_rows":   len(X_test),
        })
        all_metrics.append(metrics)

        fold_model_path = os.path.join(MODELS_DIR, f"{fold_id}.joblib")
        joblib.dump(model, fold_model_path)
        logger.info(f"  Model saved: {fold_model_path}")

        if metrics["f1_macro"] > best_f1:
            best_f1, best_model, best_fold_id = metrics["f1_macro"], model, fold_id

    # ─── Summary ────────────────────────────────────────────────────
    logger.info(f"\n{'='*72}")
    logger.info("  WALK-FORWARD COMPLETE")
    logger.info(f"{'='*72}")

    if not all_metrics:
        logger.error("No folds completed. Check your data file path and format.")
        return

    f1_vals  = [m["f1_macro"]  for m in all_metrics]
    acc_vals = [m["accuracy"]  for m in all_metrics]

    print("\n" + "="*80)
    print("  Walk-Forward Results Summary")
    print("="*80)
    header = f"{'Fold':>5}  {'Train Window':^26}  {'Test Window':^26}  {'Acc':>7}  {'F1':>7}"
    print(header)
    print("-"*80)
    for m in all_metrics:
        num = m["fold"].split("_")[1]
        tw  = f"{m['train_start']} → {m['train_end']}"
        ew  = f"{m['test_start']} → {m['test_end']}"
        print(f"  {num:>3}  {tw:^26}  {ew:^26}  {m['accuracy']:>7.4f}  {m['f1_macro']:>7.4f}")
    print("-"*80)
    print(f"  AVG Accuracy: {np.mean(acc_vals):.4f}   AVG F1 Macro: {np.mean(f1_vals):.4f}")
    print(f"  Best Fold:    {best_fold_id}  F1={best_f1:.4f}")
    print("="*80 + "\n")

    if best_model:
        best_path = os.path.join(MODELS_DIR, "best_model.joblib")
        joblib.dump(best_model, best_path)
        logger.info(f"Best model saved: {best_path}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(RESULTS_DIR, f"walk_forward_metrics_{ts}.json")
    with open(json_path, "w") as f:
        json.dump(all_metrics, f, indent=2)
    logger.info(f"Metrics JSON saved: {json_path}")

    summary_df = pd.DataFrame([
        {k: v for k, v in m.items() if k not in ("confusion_matrix", "per_class_f1", "fold")}
        for m in all_metrics
    ])
    csv_path = os.path.join(RESULTS_DIR, f"walk_forward_summary_{ts}.csv")
    summary_df.to_csv(csv_path, index=False)
    logger.info(f"Summary CSV saved: {csv_path}")


if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    logger.add(
        f"logs/walk_forward_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        level="DEBUG",
        rotation="50 MB",
    )
    run_walk_forward()
