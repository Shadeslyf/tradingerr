import sys
import os
import time
import threading
import pandas as pd
import numpy as np
import xgboost as xgb
from datetime import datetime, timedelta
from loguru import logger
import glob
import joblib

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.auth import AngelOneAuth
from app.market.instruments import InstrumentManager
from app.database.models import init_db
from app.database.repositories import MarketDataRepository, SessionLocal
from app.trading.portfolio import PaperPortfolioManager
from app.trading.executor import PaperExecutor
from app.features.feature_pipeline import FeaturePipeline
from app.broker.paper import PaperBroker
from app.risk.portfolio import RiskEngine

# We simulate the Live feed by fetching the last 100 minutes of data from DB,
# running features, and applying the model.
# A true live websocket feed would populate the database asynchronously.

def load_latest_model():
    model_files = glob.glob("data/models/xgboost_regime_*.pkl")
    if not model_files:
        raise FileNotFoundError("No XGBoost model found in data/models/")
    latest = max(model_files, key=os.path.getctime)
    logger.info(f"Loading Model: {latest}")
    return joblib.load(latest)

def live_paper_trading_loop():
    logger.info("Initializing Live Paper Trading Engine...")
    
    # 1. Initialize DB & Core components
    init_db()
    session = SessionLocal()
    repo = MarketDataRepository(session)
    
    instrument_manager = InstrumentManager()
    if not os.path.exists("data/instruments.json"):
        # We need instruments for strike calculation
        auth = AngelOneAuth()
        instrument_manager.fetch_and_save_instruments()
    else:
        instrument_manager.load_instruments()
        
    broker = PaperBroker()
    risk_engine = RiskEngine(starting_capital=300000.0, max_risk_per_trade_pct=1.0)
    
    portfolio = PaperPortfolioManager(broker, risk_engine, stop_loss_pct=15.0, take_profit_pct=30.0)
    executor = PaperExecutor(portfolio, instrument_manager)
    
    # 2. Load Model
    model = load_latest_model()
    
    # Required features mapping from model training
    # We assume the model expects the features outputted by FeaturePipeline
    
    logger.info("Engine Ready. Starting 1-minute execution loop...")
    
    try:
        while True:
            current_time = datetime.now()
            
            # End of day square off
            if current_time.hour == 15 and current_time.minute >= 15:
                logger.info("End of Day. Squaring off all positions.")
                # We pass an empty dict for prices; portfolio uses entry_price as fallback
                portfolio.close_all_eod(current_time, {})
                break
                
            # Simulate pulling the last 150 minutes of OHLCV to calculate features
            # In a real setup, a separate thread pulls Websocket ticks and writes to OHLCV table
            # Here we just fetch what's available
            
            # Fetch Spot OHLCV
            query = session.query(repo.session.get_bind()).text("SELECT * FROM ohlcv ORDER BY timestamp ASC LIMIT 150")
            df = pd.read_sql(query, session.bind)
            
            if len(df) < 60:
                logger.warning(f"Not enough data to calculate features. Have {len(df)} rows. Waiting...")
                time.sleep(60)
                continue
                
            # Process Features
            features_df = FeaturePipeline.generate_features(df, options_ohlcv=None)
            
            if features_df.empty:
                time.sleep(60)
                continue
                
            # Get latest features
            latest_features = features_df.iloc[[-1]].copy()
            
            # Keep only columns used in training
            drop_cols = ['label', 'timestamp', 'symbol', 'token', 'exchange']
            X = latest_features.drop(columns=[c for c in drop_cols if c in latest_features.columns])
            
            # 3. Predict Market Regime
            probs = model.predict_proba(X)[0]
            pred_class = int(np.argmax(probs)) + 1 # Add 1 because we trained on 0-6 for 1-7
            confidence = probs[pred_class - 1]
            
            spot_ltp = df['close'].iloc[-1]
            logger.info(f"Time: {current_time.strftime('%H:%M')} | Spot: {spot_ltp} | Pred: {pred_class} | Conf: {confidence:.2f}")
            
            # 4. Execute Logic
            # E.g. AI_MIN_CONFIDENCE = 0.45 (since it's a 3 class problem, random is 0.33)
            if confidence > 0.45:
                # We need the latest options ticks. We simulate this for now.
                # In production, this comes from the WebSocket buffer.
                simulated_ask_price = 150.0 # Dummy price
                # Map option token to simulated price
                latest_ticks = {t: simulated_ask_price for t in instrument_manager.tokens.keys()}
                
                executor.process_signal(pred_class, spot_ltp, current_time, latest_ticks)
                
            # 5. Portfolio tick check (Stop loss / Take profit)
            # In production, this is called on every websocket tick.
            # We simulate a tick event here for the currently held position.
            if portfolio.open_trades:
                # In basket mode, we just need to pass the prices of the legs
                for trade in portfolio.open_trades:
                    sim_ltp = latest_ticks.get(trade.token, trade.entry_price)
                    portfolio.on_tick(trade.token, sim_ltp, current_time)

            # Sleep until next minute
            time.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("Paper Trading Engine stopped manually.")

if __name__ == "__main__":
    live_paper_trading_loop()
