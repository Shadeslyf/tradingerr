import os
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger
from fastapi import APIRouter, BackgroundTasks, HTTPException
from sklearn.isotonic import IsotonicRegression

from app.api.schemas import TrainRequest, JobResponse
from app.api.jobs import create_job, update_job_status
from app.features.feature_pipeline import FeaturePipeline
from app.ml.labeling import RegimeLabeler
from app.ml.trainer import ModelTrainer

router = APIRouter()

def run_training_pipeline(job_id: str, request: TrainRequest):
    try:
        update_job_status(job_id, "RUNNING")
        logger.info(f"Job {job_id}: Starting training for {request.model_name}")

        # 1. Load Data
        df_raw = pd.read_csv("data/raw/NIFTY50_1min_3years.csv")
        df_raw["timestamp"] = pd.to_datetime(df_raw["timestamp"], utc=False)
        if df_raw["timestamp"].dt.tz is not None:
            df_raw["timestamp"] = df_raw["timestamp"].dt.tz_localize(None)

        start_dt = pd.to_datetime(request.start_date)
        end_dt = pd.to_datetime(request.end_date)
        
        # Buffer for features (2 days)
        buffer_start = start_dt - timedelta(days=2)
        
        df_slice = df_raw[(df_raw["timestamp"].dt.date >= buffer_start.date()) & 
                          (df_raw["timestamp"].dt.date <= end_dt.date())].copy()
        
        if len(df_slice) < 500:
            raise ValueError("Not enough data in the selected date range.")

        # 2. Build Features
        logger.info(f"Job {job_id}: Building features...")
        df_feat = FeaturePipeline.generate_features(df_slice)
        
        # Align rows and drop buffer
        df_slice = df_slice.iloc[-len(df_feat):].reset_index(drop=True)
        df_feat = df_feat.reset_index(drop=True)
        df_feat["timestamp"] = df_slice["timestamp"]
        
        # Filter to exact requested start_date
        mask = df_feat["timestamp"].dt.date >= start_dt.date()
        df_feat = df_feat[mask].copy()
        df_slice = df_slice[mask].copy()

        # 3. Labeling (use advanced 3-class by default)
        logger.info(f"Job {job_id}: Labeling data...")
        labeled_df = RegimeLabeler.apply_3class_regime_labeling(df_slice.set_index("timestamp"))
        labeled_df = labeled_df.dropna(subset=["label"])

        # Align features with labels
        common_idx = df_feat.set_index("timestamp").index.intersection(labeled_df.index)
        X = df_feat.set_index("timestamp").loc[common_idx]
        y = labeled_df.loc[common_idx, "label"].astype(int) - 1 # 1-3 to 0-2
        
        # 4. Training
        # We'll split the data: 80% train, 20% calibration
        n = len(X)
        split_idx = int(n * 0.8)
        
        X_train, y_train = X.iloc[:split_idx].copy(), y.iloc[:split_idx].copy()
        X_cal, y_cal = X.iloc[split_idx:].copy(), y.iloc[split_idx:].copy()
        
        # Add label column back temporarily for trainer
        X_train_labeled = X_train.copy()
        X_train_labeled["label"] = y_train + 1
        
        logger.info(f"Job {job_id}: Training XGBoost model...")
        trainer = ModelTrainer(n_splits=3)
        X_tr, y_tr = trainer.prepare_data(X_train_labeled, target_col="label")
        model = trainer.train_with_cv(X_tr, y_tr)
        
        # 5. Calibration
        logger.info(f"Job {job_id}: Fitting calibrator...")
        expected_cols = model.feature_names_in_
        X_cal_reindexed = X_cal.reindex(columns=expected_cols, fill_value=0.0)
        
        raw_probs = model.predict_proba(X_cal_reindexed)
        raw_preds = np.argmax(raw_probs, axis=1)
        raw_max_probs = np.max(raw_probs, axis=1)
        
        correct = (raw_preds == y_cal.values).astype(float)
        
        calibrator = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
        calibrator.fit(raw_max_probs, correct)
        
        # 6. Saving
        model_dir = f"models/{request.model_name}"
        os.makedirs(model_dir, exist_ok=True)
        
        joblib.dump(model, f"{model_dir}/best_model.joblib")
        joblib.dump(calibrator, f"{model_dir}/calibrator.joblib")
        
        logger.info(f"Job {job_id}: Successfully saved model and calibrator to {model_dir}")
        update_job_status(job_id, "COMPLETED")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}")
        update_job_status(job_id, "FAILED", error=str(e))

@router.post("/train", response_model=JobResponse)
def train_model(request: TrainRequest, background_tasks: BackgroundTasks):
    # Check if model exists, if yes append timestamp to name to avoid overwrite
    model_name = request.model_name
    if os.path.exists(f"models/{model_name}/best_model.joblib"):
        suffix = datetime.now().strftime("%Y%m%d%H%M%S")
        model_name = f"{model_name}_{suffix}"
        request.model_name = model_name
        
    job_id = create_job("TRAIN", request.model_name)
    background_tasks.add_task(run_training_pipeline, job_id, request)
    
    return {
        "job_id": job_id,
        "job_type": "TRAIN",
        "status": "PENDING",
        "model_name": request.model_name,
        "start_time": datetime.now().isoformat()
    }
