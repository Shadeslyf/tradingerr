import os
import json
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger
from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.api.schemas import BacktestRequest, JobResponse
from app.api.jobs import create_job, update_job_status
from app.features.feature_pipeline import FeaturePipeline
from app.trading.simulator import run_backtest

router = APIRouter()

def run_backtest_pipeline(job_id: str, request: BacktestRequest):
    try:
        update_job_status(job_id, "RUNNING")
        logger.info(f"Job {job_id}: Starting backtest for {request.model_name}")

        model_path = f"models/{request.model_name}/best_model.joblib"
        if not os.path.exists(model_path):
            raise ValueError(f"Model {request.model_name} not found at {model_path}")

        # 1. Load Data
        df_raw = pd.read_csv("data/raw/NIFTY50_1min_3years.csv")
        df_raw["timestamp"] = pd.to_datetime(df_raw["timestamp"], utc=False)
        if df_raw["timestamp"].dt.tz is not None:
            df_raw["timestamp"] = df_raw["timestamp"].dt.tz_localize(None)
            
        # Blend today's live data if available so users can backtest today
        live_state_path = "data/live_paper_trading.json"
        if os.path.exists(live_state_path):
            try:
                with open(live_state_path, "r") as f:
                    live_state = json.load(f)
                live_md = live_state.get("market_data", {})
                if live_md and live_md.get("timestamp"):
                    df_live = pd.DataFrame(live_md)
                    if "volume" not in df_live.columns:
                        df_live["volume"] = 1000  # Dummy volume for live ticks
                    df_live["timestamp"] = pd.to_datetime(df_live["timestamp"], utc=False)
                    if df_live["timestamp"].dt.tz is not None:
                        df_live["timestamp"] = df_live["timestamp"].dt.tz_localize(None)
                    df_raw = pd.concat([df_raw, df_live]).drop_duplicates(subset=["timestamp"], keep="last").sort_values("timestamp").reset_index(drop=True)
                    df_raw["volume"] = df_raw["volume"].fillna(1000)
                    logger.info("Blended live paper trading data into backtest dataset.")
            except Exception as e:
                logger.warning(f"Failed to blend live data: {e}")

        start_dt = pd.to_datetime(request.start_date)
        end_dt = pd.to_datetime(request.end_date)
        
        # Buffer for features: Take the 400 rows immediately preceding the start date
        idx_start = df_raw[df_raw["timestamp"].dt.date >= start_dt.date()].index.min()
        if pd.isna(idx_start):
            # If start date is beyond the dataset, just take the end of the dataset
            idx_start = len(df_raw)
            
        buffer_start_idx = max(0, idx_start - 400)
        idx_end = df_raw[df_raw["timestamp"].dt.date <= end_dt.date()].index.max()
        if pd.isna(idx_end):
            idx_end = len(df_raw) - 1
            
        df_slice = df_raw.iloc[buffer_start_idx : int(idx_end) + 1].copy()
        
        if len(df_slice) < 100:
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
        
        # 3. Run Simulation
        logger.info(f"Job {job_id}: Running simulation...")
        
        is_v3 = "v3" in request.model_name.lower()
        is_v4 = "v4" in request.model_name.lower() or not is_v3 # default custom models to v4 advanced exit logic
        
        results = run_backtest(
            df_raw=df_slice,
            df_feat=df_feat,
            model_path=model_path,
            initial_capital=request.initial_capital,
            label=f"{request.model_name} ({request.start_date} to {request.end_date})",
            is_v3=is_v3,
            is_v4=is_v4,
            house_money_mode=False
        )
        
        # 4. Save Results
        result_file = f"data/backtest_results/job_{job_id}.json"
        os.makedirs(os.path.dirname(result_file), exist_ok=True)
        
        with open(result_file, "w") as f:
            json.dump(results, f, indent=2)
            
        logger.info(f"Job {job_id}: Successfully saved results to {result_file}")
        update_job_status(job_id, "COMPLETED", result_file=result_file)
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}")
        update_job_status(job_id, "FAILED", error=str(e))

@router.post("/backtest", response_model=JobResponse)
def run_backtest_job(request: BacktestRequest, background_tasks: BackgroundTasks):
    job_id = create_job("BACKTEST", request.model_name)
    background_tasks.add_task(run_backtest_pipeline, job_id, request)
    
    return {
        "job_id": job_id,
        "job_type": "BACKTEST",
        "status": "PENDING",
        "model_name": request.model_name,
        "start_time": datetime.now().isoformat()
    }
