import os
import json
import uuid
from datetime import datetime
from loguru import logger
from typing import Dict, Any

JOBS_FILE = "data/jobs.json"

def _load_jobs() -> Dict[str, Any]:
    if os.path.exists(JOBS_FILE):
        try:
            with open(JOBS_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def _save_jobs(jobs: Dict[str, Any]):
    os.makedirs(os.path.dirname(JOBS_FILE), exist_ok=True)
    with open(JOBS_FILE, "w") as f:
        json.dump(jobs, f, indent=2)

def create_job(job_type: str, model_name: str) -> str:
    job_id = str(uuid.uuid4())
    jobs = _load_jobs()
    
    jobs[job_id] = {
        "job_id": job_id,
        "job_type": job_type,
        "status": "PENDING",
        "model_name": model_name,
        "start_time": datetime.now().isoformat(),
        "end_time": None,
        "error": None,
        "result_file": None
    }
    
    _save_jobs(jobs)
    return job_id

def update_job_status(job_id: str, status: str, error: str = None, result_file: str = None):
    jobs = _load_jobs()
    if job_id in jobs:
        jobs[job_id]["status"] = status
        if status in ["COMPLETED", "FAILED"]:
            jobs[job_id]["end_time"] = datetime.now().isoformat()
        if error:
            jobs[job_id]["error"] = error
        if result_file:
            jobs[job_id]["result_file"] = result_file
        _save_jobs(jobs)
        logger.info(f"Job {job_id} updated: {status}")

def get_job(job_id: str) -> Dict[str, Any]:
    jobs = _load_jobs()
    return jobs.get(job_id)

def get_all_jobs() -> Dict[str, Any]:
    return _load_jobs()
