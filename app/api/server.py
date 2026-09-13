import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.api.routes import training, backtest, data

app = FastAPI(
    title="NIFTY AI Trader API",
    description="Backend API for ML Training and Backtesting",
    version="1.0.0"
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(training.router, prefix="/api", tags=["Training"])
app.include_router(backtest.router, prefix="/api", tags=["Backtesting"])
app.include_router(data.router, prefix="/api", tags=["Data"])

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "live_feed_status": "active" if os.path.exists("data/live_paper_trading.json") else "inactive"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
