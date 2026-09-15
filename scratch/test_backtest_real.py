from app.api.schemas import BacktestRequest
from app.api.routes.backtest import run_backtest_pipeline
import logging
import sys
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

req = BacktestRequest(model_name="V4_Auto_J6NA", start_date="2026-09-15", end_date="2026-09-15", initial_capital=100000.0)
try:
    run_backtest_pipeline("test-real", req)
except Exception as e:
    import traceback
    traceback.print_exc()
