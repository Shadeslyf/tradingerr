#!/bin/bash
cd "$(dirname "$0")/.."
source venv/bin/activate
export PYTHONPATH=.
echo "Starting FastAPI Server on Port 9000..."
uvicorn app.api.server:app --host 0.0.0.0 --port 9000 --reload
