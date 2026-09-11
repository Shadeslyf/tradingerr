import sys
import os
import pandas as pd
from loguru import logger
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.models import SessionLocal, OHLCV
from app.features.feature_pipeline import FeaturePipeline
from app.ml.labeling import TripleBarrierLabeler

def generate_dataset():
    logger.info("Starting Training Dataset Generation...")
    
    session = SessionLocal()
    
    # In a real scenario, we'd query Options OHLCV as well. 
    # For now, let's just grab Spot OHLCV to demonstrate the pipeline integration.
    logger.info("Fetching OHLCV data from database...")
    query = session.query(OHLCV).order_by(OHLCV.timestamp.asc())
    df = pd.read_sql(query.statement, session.bind)
    
    if df.empty:
        logger.error("No OHLCV data found in the database. Run the collector and normalizer first.")
        return

    logger.info(f"Loaded {len(df)} OHLCV candles.")
    
    # 1. Feature Generation
    # We pass None for options_df for this basic generation script if we don't have it structured yet in DB.
    # The pipeline gracefully skips options features if missing.
    features_df = FeaturePipeline.generate_features(df, options_ohlcv=None)
    
    if features_df.empty:
        logger.error("Feature pipeline returned empty DataFrame (likely not enough rows to overcome warm-up).")
        return

    # 2. Labeling
    logger.info("Applying Triple Barrier Labeling...")
    # Using 60 min horizon, 0.2% up/down barriers
    labeled_df = TripleBarrierLabeler.apply_triple_barrier(
        features_df, 
        horizon=60, 
        upper_barrier_pct=0.2, 
        lower_barrier_pct=0.2
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
