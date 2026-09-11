import sys
import os
import glob
import pandas as pd
from loguru import logger
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ml.trainer import ModelTrainer

def main():
    logger.info("Looking for processed training data...")
    # Find the most recent training data file
    data_files = glob.glob("data/processed/training_data_*.csv")
    
    if not data_files:
        logger.error("No training data found in data/processed/. Please run scripts/generate_training_data.py first.")
        return
        
    latest_file = max(data_files, key=os.path.getctime)
    logger.info(f"Loading data from {latest_file}...")
    
    df = pd.read_csv(latest_file, index_col=0)
    logger.info(f"Loaded dataset with shape: {df.shape}")
    
    trainer = ModelTrainer(n_splits=5)
    
    logger.info("Preparing data for XGBoost...")
    X, y = trainer.prepare_data(df)
    
    if len(X) < 50:
        logger.warning(f"Dataset is extremely small ({len(X)} rows). Model evaluation will not be reliable.")
        
    # Check class distribution
    counts = y.value_counts().to_dict()
    logger.info(f"Target Label Distribution: {counts}")
    
    # Train and evaluate
    trainer.train_with_cv(X, y)
    
    # Save the model
    model_filename = f"data/models/xgboost_regime_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
    trainer.save_model(model_filename)
    
    logger.info("Phase 7 Model Training Pipeline Complete.")

if __name__ == "__main__":
    main()
