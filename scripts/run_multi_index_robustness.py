import pandas as pd
import numpy as np
import joblib
import json
import os
from loguru import logger
from app.features.feature_pipeline import FeaturePipeline

# Major indices to test for robustness
TARGET_INDICES = [
    "NIFTY BANK_minute.csv",
    "NIFTY IT_minute.csv",
    "NIFTY NEXT 50_minute.csv",
    "NIFTY MIDCAP 100_minute.csv",
    "NIFTY FIN SERVICE_minute.csv",
    "NIFTY AUTO_minute.csv"
]

def load_and_prep_raw_data(filepath, start_date="2026-01-01", end_date="2026-04-23"):
    try:
        df = pd.read_csv(filepath)
        # raw data has 'date' col formatted as '2015-01-09 09:15:00'
        df['timestamp'] = pd.to_datetime(df['date'])
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        
        # filter to test window
        df = df.loc[start_date:end_date].copy()
        if len(df) < 1000:
            return None
            
        # Clean column names to match what pipeline expects
        df.columns = [c.strip().lower() for c in df.columns]
        for c in ('open', 'high', 'low', 'close', 'volume'):
            df[c] = pd.to_numeric(df[c], errors='coerce')
        
        df.dropna(inplace=True)
        return df.reset_index()
    except Exception as e:
        logger.error(f"Failed to load {filepath}: {e}")
        return None

def simulate_trades(df, y_pred_class, confidences, entry_thresh=0.45):
    """Simple vectorized backtest engine matching our existing logic"""
    trades = []
    in_position = False
    entry_price = 0
    entry_time = None
    direction = 0 # 1=long, -1=short
    capital = 100000
    
    for i in range(len(df)-1):
        row = df.iloc[i]
        pred = y_pred_class[i]
        conf = confidences[i]
        
        # Exit logic
        if in_position:
            # Time exit (intraday only)
            if row['timestamp'].hour >= 15 and row['timestamp'].minute >= 15:
                exit_price = row['close']
                pnl = (exit_price - entry_price) * direction * (capital / entry_price)
                capital += pnl
                trades.append({
                    "entry_time": entry_time.strftime("%Y-%m-%d %H:%M"),
                    "exit_time": row['timestamp'].strftime("%Y-%m-%d %H:%M"),
                    "direction": "LONG" if direction == 1 else "SHORT",
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "pnl_rs": pnl,
                    "pnl_pct": (exit_price - entry_price) / entry_price * direction * 100,
                    "capital_after": capital,
                    "exit_reason": "End of Day"
                })
                in_position = False
            
            # Regime shift exit
            elif (direction == 1 and pred == 2 and conf > 0.40) or (direction == -1 and pred == 0 and conf > 0.40):
                exit_price = df.iloc[i+1]['open']
                pnl = (exit_price - entry_price) * direction * (capital / entry_price)
                capital += pnl
                trades.append({
                    "entry_time": entry_time.strftime("%Y-%m-%d %H:%M"),
                    "exit_time": df.iloc[i+1]['timestamp'].strftime("%Y-%m-%d %H:%M"),
                    "direction": "LONG" if direction == 1 else "SHORT",
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "pnl_rs": pnl,
                    "pnl_pct": (exit_price - entry_price) / entry_price * direction * 100,
                    "capital_after": capital,
                    "exit_reason": "Signal Reversal"
                })
                in_position = False
                
        # Entry logic
        if not in_position and row['timestamp'].hour < 15:
            if conf >= entry_thresh:
                if pred == 0: # BULLISH
                    direction = 1
                    in_position = True
                    entry_price = df.iloc[i+1]['open']
                    entry_time = df.iloc[i+1]['timestamp']
                elif pred == 2: # BEARISH
                    direction = -1
                    in_position = True
                    entry_price = df.iloc[i+1]['open']
                    entry_time = df.iloc[i+1]['timestamp']
                    
    return trades, capital

def main():
    model_path_v1 = "models/walk_forward/best_model.joblib"
    model_path_v2 = "models/walk_forward_v2/best_model.joblib"
    model_path_v3 = "models/walk_forward_v3/best_model.joblib"
    
    logger.info(f"Loading V1 model from {model_path_v1}")
    model_v1 = joblib.load(model_path_v1)
    
    logger.info(f"Loading V2 model from {model_path_v2}")
    model_v2 = joblib.load(model_path_v2)
    
    logger.info(f"Loading V3 model from {model_path_v3}")
    model_v3 = joblib.load(model_path_v3)
    
    results_v1 = {}
    results_v2 = {}
    results_v3 = {}
    
    for filename in TARGET_INDICES:
        name = filename.replace("_minute.csv", "")
        filepath = os.path.join("data/raw", filename)
        logger.info(f"Testing on {name}...")
        
        df = load_and_prep_raw_data(filepath)
        if df is None:
            continue
            
        logger.info(f"Generating features for {name} ({len(df)} bars)...")
        features_df = FeaturePipeline.generate_features(df)
        features_df.reset_index(inplace=True)
        
        # --- V1 Model Prediction ---
        expected_cols_v1 = model_v1.feature_names_in_
        # For V1, some features might not exist (like the 4 cross-asset features), fill with 0
        X_v1 = features_df.reindex(columns=expected_cols_v1, fill_value=0.0)
        
        probs_v1 = model_v1.predict_proba(X_v1)
        preds_v1 = np.argmax(probs_v1, axis=1)
        confs_v1 = np.max(probs_v1, axis=1)
        
        trades_v1, final_cap_v1 = simulate_trades(features_df, preds_v1, confs_v1)
        net_pnl_v1 = final_cap_v1 - 100000
        win_rate_v1 = sum(1 for t in trades_v1 if t['pnl_rs'] > 0) / len(trades_v1) if trades_v1 else 0
        
        logger.info(f"{name} (V1) P&L: ₹{net_pnl_v1:,.2f} | Trades: {len(trades_v1)} | WinRate: {win_rate_v1:.1%}")
        results_v1[name] = {
            "net_pnl_rs": net_pnl_v1,
            "return_pct": (net_pnl_v1 / 100000) * 100,
            "total_trades": len(trades_v1),
            "win_rate": win_rate_v1
        }

        # --- V2 Model Prediction ---
        expected_cols_v2 = model_v2.feature_names_in_
        X_v2 = features_df.reindex(columns=expected_cols_v2, fill_value=0.0)
        
        probs_v2 = model_v2.predict_proba(X_v2)
        preds_v2 = np.argmax(probs_v2, axis=1)
        confs_v2 = np.max(probs_v2, axis=1)
        
        trades_v2, final_cap_v2 = simulate_trades(features_df, preds_v2, confs_v2)
        net_pnl_v2 = final_cap_v2 - 100000
        win_rate_v2 = sum(1 for t in trades_v2 if t['pnl_rs'] > 0) / len(trades_v2) if trades_v2 else 0
        
        logger.info(f"{name} (V2) P&L: ₹{net_pnl_v2:,.2f} | Trades: {len(trades_v2)} | WinRate: {win_rate_v2:.1%}")
        results_v2[name] = {
            "net_pnl_rs": net_pnl_v2,
            "return_pct": (net_pnl_v2 / 100000) * 100,
            "total_trades": len(trades_v2),
            "win_rate": win_rate_v2
        }

        # --- V3 Model Prediction ---
        expected_cols_v3 = model_v3.feature_names_in_
        X_v3 = features_df.reindex(columns=expected_cols_v3, fill_value=0.0)
        
        probs_v3 = model_v3.predict_proba(X_v3)
        preds_v3 = np.argmax(probs_v3, axis=1)
        confs_v3 = np.max(probs_v3, axis=1)
        
        trades_v3, final_cap_v3 = simulate_trades(features_df, preds_v3, confs_v3)
        net_pnl_v3 = final_cap_v3 - 100000
        win_rate_v3 = sum(1 for t in trades_v3 if t['pnl_rs'] > 0) / len(trades_v3) if trades_v3 else 0
        
        logger.info(f"{name} (V3) P&L: ₹{net_pnl_v3:,.2f} | Trades: {len(trades_v3)} | WinRate: {win_rate_v3:.1%}")
        results_v3[name] = {
            "net_pnl_rs": net_pnl_v3,
            "return_pct": (net_pnl_v3 / 100000) * 100,
            "total_trades": len(trades_v3),
            "win_rate": win_rate_v3
        }
        
    # Save results
    os.makedirs("data/backtest_results", exist_ok=True)
    with open("data/backtest_results/multi_index_robustness.json", "w") as f:
        json.dump({"V1": results_v1, "V2": results_v2, "V3": results_v3}, f, indent=2)
    logger.info("Saved robustness results to data/backtest_results/multi_index_robustness.json")

if __name__ == "__main__":
    main()
