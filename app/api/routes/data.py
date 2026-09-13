import os
import json
import shutil
import time
import subprocess
from datetime import datetime
from loguru import logger
import pandas as pd
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional

from app.api.jobs import get_job, get_all_jobs

router = APIRouter()

paper_trading_process: Optional[subprocess.Popen] = None

@router.post("/paper-trading/start")
def start_paper_trading():
    global paper_trading_process
    if paper_trading_process is not None and paper_trading_process.poll() is None:
        return {"status": "already running"}
    
    # Run the script using the current virtual environment's python
    python_exec = "python" 
    if os.path.exists("venv/bin/python"):
        python_exec = "venv/bin/python"
        
    paper_trading_process = subprocess.Popen([python_exec, "scripts/run_paper_trading.py"])
    logger.info("Paper trading script started via API")
    return {"status": "started"}

@router.post("/paper-trading/stop")
def stop_paper_trading():
    global paper_trading_process
    if paper_trading_process is not None and paper_trading_process.poll() is None:
        paper_trading_process.terminate()
        paper_trading_process.wait()
        paper_trading_process = None
        logger.info("Paper trading script stopped via API")
        return {"status": "stopped"}
    return {"status": "not running"}

@router.get("/health")
def get_health():
    state_path = "data/live_paper_trading.json"
    is_live = False
    
    global paper_trading_process
    is_running = paper_trading_process is not None and paper_trading_process.poll() is None
    
    if os.path.exists(state_path):
        mtime = os.path.getmtime(state_path)
        # Consider live if updated in the last 2 minutes and the process is actually running
        if time.time() - mtime < 120 and is_running:
            is_live = True
            
    return {
        "status": "healthy",
        "live_feed_status": "active" if is_live else "inactive",
        "is_running": is_running,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/jobs")
def list_jobs():
    return get_all_jobs()

@router.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.get("/models")
def list_models():
    models_dir = "models"
    if not os.path.exists(models_dir):
        return []
        
    models = []
    for d in os.listdir(models_dir):
        path = os.path.join(models_dir, d)
        if os.path.isdir(path):
            has_model = os.path.exists(os.path.join(path, "best_model.joblib"))
            has_calibrator = os.path.exists(os.path.join(path, "calibrator.joblib"))
            if has_model:
                models.append({
                    "name": d,
                    "has_calibrator": has_calibrator
                })
    return models

@router.get("/backtests")
def list_backtests():
    results_dir = "data/backtest_results"
    if not os.path.exists(results_dir):
        return []
        
    backtests = []
    for f in os.listdir(results_dir):
        if f.endswith(".json") and f != "loss_analysis.json":
            path = os.path.join(results_dir, f)
            try:
                # Just read basic stats to avoid massive payload
                with open(path, "r") as file:
                    data = json.load(file)
                    
                if isinstance(data, dict) and "net_pnl" in data:
                    backtests.append({
                        "id": f.replace(".json", ""),
                        "filename": f,
                        "label": data.get("label", f),
                        "net_pnl": data.get("net_pnl", 0),
                        "win_rate_pct": data.get("win_rate_pct", 0),
                        "total_trades": data.get("total_trades", 0),
                        "max_drawdown_pct": data.get("max_drawdown_pct", 0)
                    })
            except Exception:
                pass
                
    return backtests

@router.get("/backtests/{result_id}")
def get_backtest_result(result_id: str):
    path = f"data/backtest_results/{result_id}.json"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Result not found")
        
    with open(path, "r") as f:
        data = json.load(f)
        data["id"] = result_id
        return data

@router.get("/paper-trading/state")
def get_paper_trading_state():
    path = "data/live_paper_trading.json"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Live paper trading state not found")
        
    with open(path, "r") as f:
        return json.load(f)

@router.get("/dataset/info")
def get_dataset_info():
    path = "data/raw/NIFTY50_1min_3years.csv"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    # Read just the timestamp column to find min/max dates
    df = pd.read_csv(path, usecols=["timestamp"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    return {
        "min_date": df["timestamp"].min().isoformat(),
        "max_date": df["timestamp"].max().isoformat(),
        "total_rows": len(df)
    }

@router.get("/loss-analysis")
def get_loss_analysis():
    path = "data/backtest_results/loss_analysis.json"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Loss analysis not found")
        
    with open(path, "r") as f:
        return json.load(f)

@router.delete("/models/{model_name}")
def delete_model(model_name: str):
    path = f"models/{model_name}"
    if not os.path.exists(path) or not os.path.isdir(path):
        raise HTTPException(status_code=404, detail="Model not found")
        
    shutil.rmtree(path)
    return {"status": "deleted", "model_name": model_name}

@router.delete("/backtests/{result_id}")
def delete_backtest(result_id: str):
    path = f"data/backtest_results/{result_id}.json"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Result not found")
        
    os.remove(path)
    return {"status": "deleted", "result_id": result_id}

