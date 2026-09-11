import sys
import os
import pandas as pd
from loguru import logger
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.models import SessionLocal, OHLCV
from app.features.feature_pipeline import FeaturePipeline
from app.ml.labeling import RegimeLabeler

def generate_dataset():
    logger.info("Starting Training Dataset Generation...")
    
    session = SessionLocal()
    
    # In a real scenario, we'd query Options OHLCV as well. 
    # For now, let's just grab Spot OHLCV to demonstrate the pipeline integration.
    logger.info("Fetching OHLCV data from database...")
    query = session.query(OHLCV).order_by(OHLCV.timestamp.asc())
    df = pd.read_sql(query.statement, session.bind)
    
    if df.empty:
        logger.warning("No OHLCV data found in DB. Generating 30 days of dummy data for training pipeline testing...")
        import numpy as np
        dates = pd.date_range(end=datetime.now(), periods=30*375, freq='min')
        np_random = pd.Series(1 + (pd.Series(range(len(dates))).apply(lambda x: 0.0001 * (np.random.random() - 0.5))))
        close = 24000 * np_random.cumprod()
        df = pd.DataFrame({
            'timestamp': dates,
            'open': close,
            'high': close + 10,
            'low': close - 10,
            'close': close,
            'volume': 1000000
        })
        # Filter trading hours
        df = df[(df.timestamp.dt.hour >= 9) & (df.timestamp.dt.hour <= 15)]
        df = df[~((df.timestamp.dt.hour == 9) & (df.timestamp.dt.minute < 15))]
        df = df[~((df.timestamp.dt.hour == 15) & (df.timestamp.dt.minute > 30))]
        df = df.reset_index(drop=True)

    logger.info(f"Loaded {len(df)} OHLCV candles.")
    
    # 1. Feature Generation
    # We pass None for options_df for this basic generation script if we don't have it structured yet in DB.
    # The pipeline gracefully skips options features if missing.
    features_df = FeaturePipeline.generate_features(df, options_ohlcv=None)
    
    if features_df.empty:
        logger.error("Feature pipeline returned empty DataFrame (likely not enough rows to overcome warm-up).")
        return

    # 2. Labeling
    logger.info("Applying Advanced Regime Labeling (7 Classes)...")
    labeled_df = RegimeLabeler.apply_advanced_regime_labeling(
        features_df, 
        horizon=60, 
        r_strong_pct=0.3, 
        r_weak_pct=0.15,
        v_high_pct=0.6,
        v_mid_pct=0.3
    )
    
    # Drop rows at the end where label is NaN (due to horizon cut-off)
    final_df = labeled_df.dropna(subset=['label'])
    
    if final_df.empty:
        logger.error("Final DataFrame is empty after dropping NaN labels.")
        return

    # 3. Save to disk
    os.makedirs('data/processed', exist_ok=True)
    filename = f"data/processed/training_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    final_df.to_csv(filename, index=True)
    logger.info(f"Successfully generated dataset with {len(final_df)} rows and {len(final_df.columns)} columns.")
    logger.info(f"Dataset saved to: {filename}")

if __name__ == "__main__":
    generate_dataset()
