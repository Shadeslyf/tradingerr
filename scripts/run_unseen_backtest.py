import pandas as pd
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from app.features.feature_pipeline import FeaturePipeline
from app.trading.simulator import run_backtest

def main():
    logger.info("Loading Unseen Data...")
    df_raw = pd.read_csv("data/raw/NIFTY50_1min_3years.csv")
    df_raw["timestamp"] = pd.to_datetime(df_raw["timestamp"], utc=False)
    if df_raw["timestamp"].dt.tz is not None:
        df_raw["timestamp"] = df_raw["timestamp"].dt.tz_localize(None)

    # We want POST-TRAINING data (after April 24, 2026)
    df_slice = df_raw[(df_raw["timestamp"].dt.date >= pd.to_datetime("2026-04-24").date())].copy()
    
    logger.info(f"Loaded {len(df_slice)} rows from {df_slice['timestamp'].min()} to {df_slice['timestamp'].max()}")
    
    logger.info("Building Features...")
    df_feat = FeaturePipeline.generate_features(df_slice)
    
    # Align rows
    df_slice = df_slice.iloc[-len(df_feat):].reset_index(drop=True)
    df_feat = df_feat.reset_index(drop=True)
    df_feat["timestamp"] = df_slice["timestamp"]

    models = [
        ("v1", "models/walk_forward/best_model.joblib", False, False),
        ("v2", "models/walk_forward_v2/best_model.joblib", False, False),
        ("v3", "models/walk_forward_v3/best_model.joblib", True, False),
        ("v4", "models/walk_forward_v4/best_model.joblib", False, True),
    ]

    for name, path, is_v3, is_v4 in models:
        logger.info(f"Running Post-Training House Money Backtest for {name.upper()}...")
        res = run_backtest(df_slice, df_feat, path, initial_capital=100000.0, label=f"{name.upper()} (Post-Train)", is_v3=is_v3, is_v4=is_v4, house_money_mode=True)
        
        out_path = f"data/backtest_results/backtest_posttrain_{name}_hm.json"
        with open(out_path, "w") as f:
            json.dump(res, f, indent=2)
        logger.info(f"  -> Saved {out_path} | Trading Capital: ₹{res.get('trading_capital', 0):,.2f} | Total Withdrawn: ₹{res.get('total_withdrawn', 0):,.2f} | P&L: ₹{res.get('net_pnl', 0):,.2f}")

if __name__ == "__main__":
    main()
