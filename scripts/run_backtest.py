import sys
import os
import pandas as pd
from loguru import logger
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.backtest.engine import BacktestEngine
from app.backtest.metrics import Metrics
from app.strategies.baselines import BaselineStrategies

def generate_dummy_backtest_data(days=30):
    """
    Since we don't have a massive historical DB yet, we generate dummy OHLCV data.
    """
    logger.info("Generating dummy historical data for backtesting...")
    dates = pd.date_range(end=datetime.now(), periods=days*375, freq='min') # roughly 375 mins in a trading day
    
    # Random walk for NIFTY
    np_random = pd.Series(1 + (pd.Series(range(len(dates))).apply(lambda x: 0.0001 * (pd.np.random.random() - 0.5))))
    close = 24000 * np_random.cumprod()
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': close,
        'high': close + 10,
        'low': close - 10,
        'close': close,
        'volume': 1000000
    })
    
    # Only keep trading hours
    df = df[(df.timestamp.dt.hour >= 9) & (df.timestamp.dt.hour <= 15)]
    df = df[~((df.timestamp.dt.hour == 9) & (df.timestamp.dt.minute < 15))]
    df = df[~((df.timestamp.dt.hour == 15) & (df.timestamp.dt.minute > 30))]
    
    return df.reset_index(drop=True)

def run_baseline_backtest():
    df = generate_dummy_backtest_data(30)
    
    logger.info("Running Baseline 1: VWAP + EMA Directional")
    signals = BaselineStrategies.vwap_ema_crossover(df)
    
    # We pass the signals to the BacktestEngine
    engine = BacktestEngine(initial_capital=300000.0, slippage_pct=0.005)
    orders = engine.run(df, signals)
    
    metrics = Metrics.from_pnl_series(engine.risk_engine.trade_pnls, engine.risk_engine.starting_capital)
    
    logger.info("--- BACKTEST METRICS ---")
    for k, v in metrics.items():
        if isinstance(v, float):
            logger.info(f"{k}: {v:.2f}")
        else:
            logger.info(f"{k}: {v}")
            
if __name__ == '__main__':
    # Fix pandas np.random deprecation
    import numpy as np
    pd.np = np
    
    run_baseline_backtest()
