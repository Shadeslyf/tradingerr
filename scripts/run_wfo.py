import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
from loguru import logger
import joblib

from app.features.feature_pipeline import FeaturePipeline
from app.ml.trainer import ModelTrainer
from app.trading.simulator import run_backtest

# Configure Logger for clean terminal output
logger.remove()
import sys
logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{message}</level>", level="INFO")

def run_wfo_2025():
    logger.info("Starting Walk-Forward Optimization for 2025...")
    
    # 1. Load Global Data
    logger.info("Loading 3-year raw NIFTY50 data...")
    df_raw = pd.read_csv("data/raw/NIFTY50_1min_3years.csv")
    df_raw["timestamp"] = pd.to_datetime(df_raw["timestamp"])
    if df_raw["timestamp"].dt.tz is not None:
        df_raw["timestamp"] = df_raw["timestamp"].dt.tz_localize(None)
    
    logger.info("Generating global features (This will take a moment)...")
    # Buffer slice from mid 2024 to late 2026 to save compute
    start_buffer = pd.to_datetime("2024-06-01")
    end_buffer = pd.to_datetime("2026-10-01")
    df_raw = df_raw[(df_raw["timestamp"] >= start_buffer) & (df_raw["timestamp"] <= end_buffer)].copy().reset_index(drop=True)
    
    df_feat = FeaturePipeline.generate_features(df_raw)
    df_raw = df_raw.iloc[-len(df_feat):].reset_index(drop=True)
    df_feat = df_feat.reset_index(drop=True)
    df_feat["timestamp"] = df_raw["timestamp"]
    
    # 2. Iterate through months of 2025 and 2026 (Up to Aug 2026)
    start_date = pd.to_datetime("2025-01-01")
    total_months = 20 # 12 months in 2025 + 8 months in 2026
    
    wfo_results_2025 = []
    wfo_results_2026 = []
    total_net_pnl_2025 = 0.0
    total_net_pnl_2026 = 0.0
    current_capital = 100000.0
    
    os.makedirs("models/wfo", exist_ok=True)
    
    for i in range(total_months):
        test_start = start_date + relativedelta(months=i)
        test_end = test_start + relativedelta(months=1) - relativedelta(days=1)
        
        train_end = test_start - relativedelta(days=1)
        train_start = train_end - relativedelta(months=6)
        
        month_name = test_start.strftime("%B %Y")
        year = test_start.year
        logger.info(f"--- WFO Iteration: {month_name} ---")
        logger.info(f"Train Window: {train_start.date()} to {train_end.date()}")
        logger.info(f"Test Window:  {test_start.date()} to {test_end.date()}")
        
        # --- TRAINING PHASE ---
        df_train_feat = df_feat[(df_feat["timestamp"].dt.date >= train_start.date()) & (df_feat["timestamp"].dt.date <= train_end.date())].copy()
        
        if len(df_train_feat) < 1000:
            logger.warning(f"Not enough training data for {month_name}. Skipping...")
            continue
            
        from app.ml.labeling import RegimeLabeler
        df_train_raw = df_raw[(df_raw["timestamp"].dt.date >= train_start.date()) & (df_raw["timestamp"].dt.date <= train_end.date())].copy()
        labeled_df = RegimeLabeler.apply_3class_regime_labeling(df_train_raw.set_index("timestamp"))
        labeled_df = labeled_df.dropna(subset=["label"])
        
        common_idx = df_train_feat.set_index("timestamp").index.intersection(labeled_df.index)
        X_train_labeled = df_train_feat.set_index("timestamp").loc[common_idx].copy()
        X_train_labeled["label"] = labeled_df.loc[common_idx, "label"].astype(int)
        
        n = len(X_train_labeled)
        split_idx = int(n * 0.8)
        
        train_slice = X_train_labeled.iloc[:split_idx].copy()
        cal_slice = X_train_labeled.iloc[split_idx:].copy()
        
        trainer = ModelTrainer()
        X_tr, y_tr = trainer.prepare_data(train_slice, target_col='label')
        
        model_name = f"wfo/V2_WFO_{month_name.replace(' ', '_')}"
        model_dir = f"models/{model_name}"
        os.makedirs(model_dir, exist_ok=True)
        
        logger.info("Training XGBoost Model...")
        model = trainer.train_with_cv(X_tr, y_tr)
        
        logger.info("Fitting Isotonic Calibrator...")
        from sklearn.isotonic import IsotonicRegression
        X_cal, y_cal = trainer.prepare_data(cal_slice, target_col='label')
        
        expected_cols = model.feature_names_in_
        X_cal_reindexed = X_cal.reindex(columns=expected_cols, fill_value=0.0)
        
        raw_probs = model.predict_proba(X_cal_reindexed)
        raw_preds = np.argmax(raw_probs, axis=1)
        raw_max_probs = np.max(raw_probs, axis=1)
        correct = (raw_preds == y_cal.values).astype(float)
        
        calibrator = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
        calibrator.fit(raw_max_probs, correct)
        
        joblib.dump(model, f"{model_dir}/best_model.joblib")
        joblib.dump(calibrator, f"{model_dir}/calibrator.joblib")
        
        # --- TESTING PHASE ---
        df_test_raw = df_raw[(df_raw["timestamp"].dt.date >= test_start.date()) & (df_raw["timestamp"].dt.date <= test_end.date())].copy()
        df_test_feat = df_feat[(df_feat["timestamp"].dt.date >= test_start.date()) & (df_feat["timestamp"].dt.date <= test_end.date())].copy()
        
        if len(df_test_feat) < 100:
            logger.warning(f"Not enough testing data for {month_name}. Skipping...")
            continue
            
        logger.info(f"Running V2 Simulator for {month_name}...")
        
        results = run_backtest(
            df_raw=df_test_raw,
            df_feat=df_test_feat,
            model_path=f"{model_dir}/best_model.joblib",
            initial_capital=current_capital,
            label=f"WFO {month_name}",
            is_v3=False,
            is_v4=False,
            house_money_mode=False
        )
        
        if not results:
            logger.warning(f"Simulator returned empty results for {month_name}.")
            continue
            
        net_pnl = results.get("net_pnl", 0.0)
        win_rate = results.get("win_rate_pct", 0.0)
        trades_count = results.get("total_trades", 0)
        
        logger.info(f"Result for {month_name} -> P&L: ₹{net_pnl} | Win Rate: {win_rate}% | Trades: {trades_count}")
        
        current_capital += net_pnl
        
        res_dict = {
            "month": month_name,
            "net_pnl": net_pnl,
            "win_rate": win_rate,
            "trades": trades_count,
            "capital_after": current_capital
        }
        
        if year == 2025:
            wfo_results_2025.append(res_dict)
            total_net_pnl_2025 += net_pnl
        else:
            wfo_results_2026.append(res_dict)
            total_net_pnl_2026 += net_pnl
            
    logger.info("="*40)
    logger.info("🎯 WALK-FORWARD OPTIMIZATION COMPLETE (2025 vs 2026) 🎯")
    logger.info("="*40)
    
    logger.info("--- 2025 RESULTS ---")
    for res in wfo_results_2025:
        logger.info(f"{res['month']:<15} | P&L: ₹{res['net_pnl']:<10} | Win Rate: {res['win_rate']:>5}% | Trades: {res['trades']}")
    logger.info(f"2025 Total Net P&L: ₹{total_net_pnl_2025}")
    
    logger.info("\n--- 2026 RESULTS (Jan - Aug) ---")
    for res in wfo_results_2026:
        logger.info(f"{res['month']:<15} | P&L: ₹{res['net_pnl']:<10} | Win Rate: {res['win_rate']:>5}% | Trades: {res['trades']}")
    logger.info(f"2026 Total Net P&L: ₹{total_net_pnl_2026}")
    
    logger.info("="*40)
    logger.info(f"💰 Combined 20-Month Net P&L: ₹{total_net_pnl_2025 + total_net_pnl_2026}")
    logger.info(f"🏦 Final Capital: ₹{current_capital}")

if __name__ == "__main__":
    run_wfo_2025()
