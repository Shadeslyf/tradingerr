from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class TrainRequest(BaseModel):
    model_name: str
    start_date: str
    end_date: str

class BacktestRequest(BaseModel):
    model_name: str
    start_date: str
    end_date: str
    initial_capital: float = 100000.0

class JobResponse(BaseModel):
    job_id: str
    job_type: str
    status: str
    model_name: str
    start_time: str
    end_time: Optional[str] = None
    error: Optional[str] = None
    result_file: Optional[str] = None
