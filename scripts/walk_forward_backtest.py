import os
import sys
import pandas as pd
from loguru import logger
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.features.feature_pipeline import FeaturePipeline
from app.ml.labeling import RegimeLabeler
from app.ml.trainer import ModelTrainer
from app.backtest.engine import BacktestEngine
from app.backtest.metrics import Metrics

def run_real_walk_forward():
    data_path = "data/real_nifty_30d.csv"
    if not os.path.exists(data_path):
        logger.error(f"{data_path} not found. Run fetch_real_data.py first.")
        return
        
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp').sort_index()
    
    logger.info(f"Loaded {len(df)} rows of real NIFTY Spot data.")
    
    # Generate features
    features_df = FeaturePipeline.generate_features(df)
    
    # Find cutoff for 20-day train / 10-day test split
    unique_days = features_df.index.normalize().unique()
    if len(unique_days) < 10:
        logger.error("Not enough days of data for a split. Please fetch more data.")
        return
        
    split_idx = int(len(unique_days) * (2/3)) # Roughly 20 days if 30 days total
    split_date = unique_days[split_idx]
    
    logger.info(f"Total Days: {len(unique_days)} | Splitting at {split_date.date()}")
    
    train_df = features_df[features_df.index < split_date].copy()
    test_df = features_df[features_df.index >= split_date].copy()
    
    logger.info(f"Train size: {len(train_df)} rows | Test size: {len(test_df)} rows")
    
    # 1. Label Train Data
    logger.info("Labeling Train Data...")
    train_df = RegimeLabeler.apply_advanced_regime_labeling(train_df)
    
    # 2. Train Model
    trainer = ModelTrainer(n_splits=3)
    X_train, y_train = trainer.prepare_data(train_df)
    
    logger.info("Training Model on Real Data...")
    trainer.train_with_cv(X_train, y_train)
    trainer.save_model("data/models/real_walk_forward_model.pkl")
    
    # 3. Predict on Test Data
    drop_cols = ['label', 'timestamp', 'symbol', 'token', 'exchange']
    X_test = test_df.drop(columns=[c for c in drop_cols if c in test_df.columns])
    
    probs = trainer.model.predict_proba(X_test)
    pred_classes = probs.argmax(axis=1) + 1 # 0-6 to 1-7
    signals = pd.Series(pred_classes, index=test_df.index)
    
    logger.info(f"Test Signal Distribution: {signals.value_counts().to_dict()}")
    
    # 4. Run Backtest Engine on Test Data
    logger.info("Running Execution Engine on Test Data...")
    raw_test_prices = df.loc[test_df.index]
    
    engine = BacktestEngine(initial_capital=300000.0, slippage_pct=0.005)
    orders = engine.run(raw_test_prices, signals)
    
    # 5. Metrics
    metrics = Metrics.from_pnl_series(engine.risk_engine.trade_pnls, engine.risk_engine.starting_capital)
    
    logger.info("--- REAL OUT-OF-SAMPLE TEST METRICS ---")
    for k, v in metrics.items():
        if isinstance(v, float):
            logger.info(f"{k}: {v:.2f}")
        else:
            logger.info(f"{k}: {v}")
            
    logger.success("Walk-forward backtest complete! Check your Streamlit dashboard for visual results.")

if __name__ == "__main__":
    import pandas as pd
    import numpy as np
    pd.np = np
    run_real_walk_forward()
