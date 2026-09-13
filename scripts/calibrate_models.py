"""
Probability Calibration Script
==============================
Fits Isotonic Regression calibrators on each walk-forward model (V1-V4).

For each model:
  1. Loads the training data (pre-April 2026)
  2. Splits into train (80%) and calibration holdout (20%) — time-ordered
  3. Trains the model on the train portion
  4. Collects raw predict_proba() on the calibration holdout
  5. Fits IsotonicRegression mapping raw_max_prob → actual_hit_rate
  6. Saves the calibrator as `calibrator.joblib` next to the model

Usage:
    cd /Users/vishal/Desktop/tradingggg
    source venv/bin/activate
    python scripts/calibrate_models.py
"""

import os
import sys
import joblib
import numpy as np
import pandas as pd
from loguru import logger
from sklearn.isotonic import IsotonicRegression

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.features.feature_pipeline import FeaturePipeline
from app.ml.labeling import RegimeLabeler


def main():
    logger.info("=== Probability Calibration Pipeline ===")

    # ── 1. Load & prepare data (same data used for training, pre-April 2026) ──
    logger.info("Loading training data...")
    df_raw = pd.read_csv("data/raw/NIFTY50_1min_3years.csv")
    df_raw["timestamp"] = pd.to_datetime(df_raw["timestamp"], utc=False)
    if df_raw["timestamp"].dt.tz is not None:
        df_raw["timestamp"] = df_raw["timestamp"].dt.tz_localize(None)

    # Use only training period (before April 24, 2026)
    df_train_period = df_raw[df_raw["timestamp"].dt.date < pd.to_datetime("2026-04-24").date()].copy()
    logger.info(f"Training period: {len(df_train_period)} rows | "
                f"{df_train_period['timestamp'].min()} to {df_train_period['timestamp'].max()}")

    # ── 2. Build features ──
    logger.info("Building features...")
    df_feat = FeaturePipeline.generate_features(df_train_period)
    df_train_period = df_train_period.iloc[-len(df_feat):].reset_index(drop=True)
    df_feat = df_feat.reset_index(drop=True)
    df_feat["timestamp"] = df_train_period["timestamp"]

    # ── 3. For each model, fit a calibrator ──
    models = [
        ("V1", "models/walk_forward/best_model.joblib"),
        ("V2", "models/walk_forward_v2/best_model.joblib"),
        ("V3", "models/walk_forward_v3/best_model.joblib"),
        ("V4", "models/walk_forward_v4/best_model.joblib"),
    ]

    for name, model_path in models:
        if not os.path.exists(model_path):
            logger.warning(f"Model {model_path} not found, skipping {name}")
            continue

        logger.info(f"\n{'='*60}")
        logger.info(f"Calibrating {name} ({model_path})...")

        model = joblib.load(model_path)
        expected_cols = model.feature_names_in_

        X_all = df_feat.reindex(columns=expected_cols, fill_value=0.0)

        # Use the last 20% as the calibration holdout (time-ordered, no leakage)
        n = len(X_all)
        split_idx = int(n * 0.80)

        X_cal = X_all.iloc[split_idx:]

        # Get raw probabilities on the calibration set
        raw_probs = model.predict_proba(X_cal)
        raw_preds = np.argmax(raw_probs, axis=1)
        raw_max_probs = np.max(raw_probs, axis=1)

        # We need to know if the model's top prediction was actually correct.
        # To do this, we need labels for the calibration set.
        # Re-label the calibration slice using the same labeling pipeline.
        cal_slice = df_train_period.iloc[split_idx:split_idx + len(X_cal)].copy()
        cal_slice = cal_slice.set_index("timestamp")
        
        try:
            labeled = RegimeLabeler.apply_3class_regime_labeling(
                cal_slice, horizon=60, threshold_pct=0.1
            )
        except Exception:
            # Fallback: try the advanced labeling
            labeled = RegimeLabeler.apply_advanced_regime_labeling(cal_slice)

        labeled = labeled.dropna(subset=["label"])
        true_labels = (labeled["label"].astype(int) - 1).values  # shift 1-3 → 0-2

        # Align lengths (labeling may drop rows due to horizon)
        min_len = min(len(true_labels), len(raw_preds))
        raw_max_probs = raw_max_probs[:min_len]
        raw_preds = raw_preds[:min_len]
        true_labels = true_labels[:min_len]

        # Binary target: 1 if the model's top prediction matched the true label
        correct = (raw_preds == true_labels).astype(float)

        logger.info(f"  Calibration set size: {min_len}")
        logger.info(f"  Raw accuracy on cal set: {correct.mean():.4f}")
        logger.info(f"  Raw mean confidence: {raw_max_probs.mean():.4f}")

        # ── 4. Fit Isotonic Regression ──
        calibrator = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
        calibrator.fit(raw_max_probs, correct)

        # Show the calibration effect
        calibrated_probs = calibrator.predict(raw_max_probs)
        logger.info(f"  Calibrated mean confidence: {calibrated_probs.mean():.4f}")

        # Show before/after for key thresholds
        for threshold in [0.50, 0.65, 0.80, 0.90, 0.95]:
            raw_mask = raw_max_probs >= threshold
            cal_mask = calibrated_probs >= threshold
            raw_count = raw_mask.sum()
            cal_count = cal_mask.sum()
            raw_acc = correct[raw_mask].mean() if raw_count > 0 else 0
            cal_acc = correct[cal_mask].mean() if cal_count > 0 else 0
            logger.info(f"  Threshold {threshold:.2f}: "
                        f"Raw: {raw_count} trades (acc={raw_acc:.3f}) → "
                        f"Calibrated: {cal_count} trades (acc={cal_acc:.3f})")

        # ── 5. Save calibrator ──
        model_dir = os.path.dirname(model_path)
        cal_path = os.path.join(model_dir, "calibrator.joblib")
        joblib.dump(calibrator, cal_path)
        logger.success(f"  Saved calibrator → {cal_path}")

    logger.success("\n✅ All calibrators fitted and saved!")


if __name__ == "__main__":
    main()
