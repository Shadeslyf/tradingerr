import sys
import os
import time
import json
import pandas as pd
import numpy as np
import joblib
from datetime import datetime, timedelta
from loguru import logger

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.broker.angel_one import AngelOneBroker
from app.features.feature_pipeline import FeaturePipeline
from app.market.instruments import InstrumentManager

class LiveSimulator:
    def __init__(self, name: str, initial_capital: float = 100000.0, is_v3: bool = False, is_v4: bool = False):
        self.name = name
        self.capital = initial_capital
        self.is_v3 = is_v3
        self.is_v4 = is_v4
        self.position = None
        self.trades = []
        self.equity_curve = []
        self.equity_times = []
        self.recent_signals = []
        
    def process_tick(self, timestamp, current_price, current_atr, conf, sig, adx_val=None, vol_ratio=1.0):
        LOT_SIZE = 25
        ATR_MULT_INITIAL = 3.0
        ATR_MULT_TRAIL = 2.0
        TARGET_PCT_BASE = 1.5
        STOP_LOSS_PCT = 0.5
        CONFIDENCE_MIN = 0.45
        
        signal_str = "HOLD" if sig == 1 else ("LONG" if sig == 0 else "SHORT")
        acted_on = False
        skip_reason = None
        
        # 1. Check Exit if we have an open position
        if self.position:
            p = self.position
            p["bars_held"] += 1
            exit_reason = None
            
            # V3/V4 Trailing Stop (Chandelier Exit)
            if self.is_v3 or self.is_v4:
                if p["direction"] == "LONG":
                    p["highest_high"] = max(p["highest_high"], current_price)
                    if p["highest_high"] == p["entry_price"]:
                        p["trailing_sl"] = p["highest_high"] - (ATR_MULT_INITIAL * current_atr)
                    else:
                        p["trailing_sl"] = max(p["trailing_sl"], p["highest_high"] - (ATR_MULT_TRAIL * current_atr))
                else:
                    p["lowest_low"] = min(p["lowest_low"], current_price)
                    if p["lowest_low"] == p["entry_price"]:
                        p["trailing_sl"] = p["lowest_low"] + (ATR_MULT_INITIAL * current_atr)
                    else:
                        p["trailing_sl"] = min(p["trailing_sl"], p["lowest_low"] + (ATR_MULT_TRAIL * current_atr))
            
            # V4 Breakeven Stop
            if self.is_v4:
                if p["direction"] == "LONG" and (p["highest_high"] - p["entry_price"]) >= (0.5 * p["entry_atr"]):
                    p["trailing_sl"] = max(p["trailing_sl"], p["entry_price"])
                elif p["direction"] == "SHORT" and (p["entry_price"] - p["lowest_low"]) >= (0.5 * p["entry_atr"]):
                    p["trailing_sl"] = min(p["trailing_sl"], p["entry_price"])
                    
            # Check Stops and Targets
            if p["direction"] == "LONG":
                if current_price <= p["trailing_sl"]:
                    exit_reason = "TRAILING_STOP" if (self.is_v3 or self.is_v4) else "STOP_LOSS"
                elif current_price >= p["target"]:
                    exit_reason = "TARGET_HIT"
            else:
                if current_price >= p["trailing_sl"]:
                    exit_reason = "TRAILING_STOP" if (self.is_v3 or self.is_v4) else "STOP_LOSS"
                elif current_price <= p["target"]:
                    exit_reason = "TARGET_HIT"
                    
            if p["bars_held"] >= p["max_hold_bars"] and not exit_reason:
                exit_reason = "TIME_EXIT"
                
            if exit_reason:
                # Option Greeks Simulation
                OPTION_DELTA = 0.50
                THETA_DECAY_PER_MIN = 0.20 # ₹0.20 per minute per lot
                AVG_PREMIUM = 150.0
                SLIPPAGE_PCT = 0.05
                TRANSACTION_COST = 60.0
                
                if p["direction"] == "LONG":
                    spot_pnl = (current_price - p["entry_price"]) * p["quantity"]
                else:
                    spot_pnl = (p["entry_price"] - current_price) * p["quantity"]
                    
                gross_option_pnl = (spot_pnl * OPTION_DELTA) - (THETA_DECAY_PER_MIN * p["bars_held"] * (p["quantity"] / LOT_SIZE))
                
                option_entry_value = AVG_PREMIUM * p["quantity"]
                option_exit_value = AVG_PREMIUM * p["quantity"]
                slippage_cost = (option_entry_value + option_exit_value) * (SLIPPAGE_PCT / 100)
                
                pnl = gross_option_pnl - slippage_cost - TRANSACTION_COST

                self.capital += pnl
                self.trades.append({
                    "entry_time": p["entry_time"],
                    "exit_time": str(timestamp),
                    "direction": p["direction"],
                    "entry_price": p["entry_price"],
                    "exit_price": current_price,
                    "quantity": p["quantity"],
                    "pnl_rs": round(pnl, 2),
                    "exit_reason": exit_reason,
                    "confidence": p["confidence"]
                })
                logger.info(f"[{self.name}] Closed {p['direction']} | P&L: ₹{pnl:.2f} | Reason: {exit_reason}")
                self.position = None
                
        # 2. Check Entry if no open position
        if not self.position:
            if sig == 1:
                skip_reason = "HOLD Signal"
            elif conf < CONFIDENCE_MIN:
                skip_reason = "Low Confidence"
            else:
                # Regime Filters (Time & VSA)
                is_lunch = (timestamp.hour == 12)
                is_low_volume = (vol_ratio < 1.0)
                
                if (is_lunch and conf < 0.95):
                    skip_reason = "Lunch Hour"
                elif is_low_volume:
                    skip_reason = "Low Volume"
                elif self.is_v4 and adx_val is not None and adx_val < 20.0:
                    skip_reason = "Low ADX (Chop)"
                else:
                    acted_on = True
                    direction = "LONG" if sig == 0 else "SHORT"
                    
                    # Dynamic Asymmetrical Targets & Expiry
                    if direction == "LONG":
                        current_target_pct = 1.2
                        max_hold_bars = 90
                    else:
                        current_target_pct = 1.8
                        max_hold_bars = 60
                        
                    if (self.is_v3 or self.is_v4) and current_atr is not None:
                        if current_atr < 4.0:
                            current_target_pct *= 0.5
                            max_hold_bars = int(max_hold_bars * 1.5)
                        elif current_atr > 10.0:
                            current_target_pct *= 1.5
                    
                    if self.is_v3 or self.is_v4:
                        sl = current_price - (current_atr * ATR_MULT_INITIAL) if direction == "LONG" else current_price + (current_atr * ATR_MULT_INITIAL)
                        tp = current_price + (current_price * (current_target_pct/100)) if direction == "LONG" else current_price - (current_price * (current_target_pct/100))
                    else:
                        sl = current_price * (1 - STOP_LOSS_PCT/100) if direction == "LONG" else current_price * (1 + STOP_LOSS_PCT/100)
                        tp = current_price * (1 + current_target_pct/100) if direction == "LONG" else current_price * (1 - current_target_pct/100)
                        
                    quantity = LOT_SIZE
                    
                    self.position = {
                        "entry_time": str(timestamp),
                        "direction": direction,
                        "entry_price": current_price,
                        "highest_high": current_price,
                        "lowest_low": current_price,
                        "quantity": quantity,
                        "entry_atr": current_atr,
                        "trailing_sl": sl,
                        "target": tp,
                        "max_hold_bars": max_hold_bars,
                        "confidence": float(conf),
                        "bars_held": 0
                    }
                    logger.info(f"[{self.name}] Entered {direction} @ {current_price:.2f} (Conf: {conf:.2f})")

        # Log signal to feed
        self.recent_signals.append({
            "timestamp": str(timestamp),
            "signal": signal_str,
            "confidence": float(conf),
            "acted_on": acted_on,
            "skip_reason": skip_reason if not acted_on else None
        })
        if len(self.recent_signals) > 100:
            self.recent_signals.pop(0)

        self.equity_curve.append(self.capital)
        self.equity_times.append(str(timestamp))

def main():
    logger.info("Starting Live Paper Trading Engine...")
    
    broker = AngelOneBroker()
    if not broker.login():
        logger.error("Failed to login to Angel One. Exiting.")
        return
        
    logger.info("Initializing Instrument Manager...")
    raw = broker.get_instrument_master()
    im = InstrumentManager(raw)
        
    models = {
        "V1": {"path": "models/walk_forward/best_model.joblib", "is_v3": False, "is_v4": False},
        "V2": {"path": "models/walk_forward_v2/best_model.joblib", "is_v3": False, "is_v4": False},
        "V3": {"path": "models/walk_forward_v3/best_model.joblib", "is_v3": True, "is_v4": False},
        "V4": {"path": "models/walk_forward_v4/best_model.joblib", "is_v3": False, "is_v4": True},
    }
    
    loaded_models = {}
    loaded_calibrators = {}
    simulators = {}
    
    for name, m_info in models.items():
        if os.path.exists(m_info["path"]):
            loaded_models[name] = joblib.load(m_info["path"])
            simulators[name] = LiveSimulator(name, initial_capital=100000.0, is_v3=m_info["is_v3"], is_v4=m_info["is_v4"])
            logger.info(f"Loaded {name} Model")
            
            # Load calibrator if exists
            cal_path = os.path.join(os.path.dirname(m_info["path"]), "calibrator.joblib")
            if os.path.exists(cal_path):
                loaded_calibrators[name] = joblib.load(cal_path)
                logger.info(f"  └─ Loaded calibrator for {name}")
            
    if not loaded_models:
        logger.error("No models found!")
        return

    last_processed_timestamp = None

    import queue
    tick_queue = queue.Queue()
    
    def on_tick(msg):
        # SmartWebSocketV2 sends a dict (not list) with prices in paise (raw int / 100)
        items = [msg] if isinstance(msg, dict) else (msg if isinstance(msg, list) else [])
        for item in items:
            if 'last_traded_price' in item and str(item.get('token', '')).strip() == '26000':
                normalized = dict(item)
                normalized['last_traded_price'] = item['last_traded_price'] / 100.0
                tick_queue.put(normalized)

    if not broker.init_websocket(on_tick_callback=on_tick):
        logger.error("Failed to initialize WebSocket.")
        return
        
    # Subscribe to Nifty Spot (Token 26000, Exchange 1=NSE, Mode 1=LTP)
    broker.subscribe_websocket("NIFTY_LIVE", 1, [{"exchangeType": 1, "tokens": ["26000"]}])

    # 1. Fetch initial historical data to seed the FeaturePipeline
    # Fetch from the start of the trading day (09:15) so the UI shows the full day's chart.
    now = datetime.now()
    todate = now.strftime("%Y-%m-%d %H:%M")
    
    # If it's before 09:15, or weekend, we might need a fallback, but for today we just ask for today's 09:15
    fromdate = now.strftime("%Y-%m-%d 09:15")
    
    # If now is somehow before 09:15 (e.g. 07:00 AM), fromdate will be in the future,
    # so let's just make sure it's valid for Angel One:
    if now.hour < 9 or (now.hour == 9 and now.minute < 15):
        fromdate = (now - timedelta(days=1)).strftime("%Y-%m-%d 09:15")
    logger.info(f"Fetching Initial Seed Data from {fromdate} to {todate} via REST API...")
    
    raw_data = None
    for attempt in range(3):
        # NIFTY 50 historical data requires token 99926000 (Spot Index)
        raw_data = broker.get_candle_data(exchange="NSE", symboltoken="99926000", interval="ONE_MINUTE", fromdate=fromdate, todate=todate)
        if raw_data:
            break
        logger.warning(f"Seed fetch attempt {attempt+1}/3 failed. Waiting 2s before retry...")
        time.sleep(2)
    
    if not raw_data:
        logger.error("Failed to fetch initial seed data from REST API. Cannot start pipeline.")
        return

    df = pd.DataFrame(raw_data, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)

    current_minute = None
    current_candle = None
    last_processed_timestamp = None

    logger.info("Entering Live WebSocket Event Loop...")
    while True:
        try:
            # 2. Wait for incoming ticks
            try:
                tick = tick_queue.get(timeout=1.0)
            except queue.Empty:
                # No tick arrived in the last second
                continue

            # Parse Tick
            ltp = float(tick.get('last_traded_price', 0))
            if ltp == 0:
                continue
                
            # If exchange timestamp is available, use it, else use system time
            # For simplicity in simulation, we use system time
            tick_time = datetime.now()
            minute_floor = tick_time.replace(second=0, microsecond=0)

            # 3. Aggregate Ticks into 1-Minute Candles
            if current_minute != minute_floor:
                # Minute Rollover: We have a completed candle!
                if current_candle:
                    # Append candle to DataFrame
                    new_row = pd.DataFrame([{
                        "timestamp": pd.to_datetime(current_candle["time"], unit='s'),
                        "open": current_candle["open"],
                        "high": current_candle["high"],
                        "low": current_candle["low"],
                        "close": current_candle["close"],
                        "volume": 0 # Not provided by LTP stream
                    }])
                    df = pd.concat([df, new_row], ignore_index=True)
                    # Keep max 150 rows to prevent memory leak
                    if len(df) > 150:
                        df = df.iloc[-150:].reset_index(drop=True)

                    current_timestamp = new_row["timestamp"].iloc[0]
                    
                    if last_processed_timestamp != current_timestamp:
                        # 4. Generate Features & Run Inference
                        df_feat = FeaturePipeline.generate_features(df.copy())
                        if not df_feat.empty:
                            df_raw_aligned = df.iloc[-len(df_feat):].reset_index(drop=True)
                            df_feat = df_feat.reset_index(drop=True)
                            
                            latest_feat = df_feat.iloc[-1:]
                            current_price = current_candle["close"]
                            
                            logger.info(f"Processing Live Tick: {current_timestamp} @ ₹{current_price}")
                            
                            for name, model in loaded_models.items():
                                expected_cols = model.feature_names_in_
                                X = latest_feat.reindex(columns=expected_cols, fill_value=0.0)
                                
                                probs = model.predict_proba(X)
                                pred = np.argmax(probs, axis=1)[0]
                                conf = np.max(probs, axis=1)[0]
                                
                                if name in loaded_calibrators:
                                    conf = float(loaded_calibrators[name].predict([conf])[0])
                                
                                sim = simulators[name]
                                adx_val = latest_feat["adx_14"].values[0] if "adx_14" in latest_feat.columns else 25.0
                                current_atr = latest_feat["atr_14"].values[0] if "atr_14" in latest_feat.columns else 20.0
                                vol_ratio = latest_feat["vol_ratio"].values[0] if "vol_ratio" in latest_feat.columns else 1.0
                                
                                sim.process_tick(current_timestamp, current_price, current_atr, conf, pred, adx_val, vol_ratio)
                            
                            # --- Option Chain Logic ---
                            option_chain_data = []
                            try:
                                atm = round(current_price / 50) * 50
                                strikes = [atm + (i * 50) for i in range(-5, 6)]
                                opts = im.get_current_nifty_options()
                                opts['expiry_dt'] = pd.to_datetime(opts['expiry'], format='%d%b%Y', errors='coerce')
                                opts = opts[opts['expiry_dt'] >= tick_time]
                                if not opts.empty:
                                    nearest = opts.iloc[0]['expiry_dt']
                                    opts = opts[(opts['expiry_dt'] == nearest) & (opts['strike'].isin(strikes))]
                                    tokens = opts['token'].tolist()
                                    md = broker.smart_api.getMarketData("FULL", {"NFO": tokens})
                                    if md and md.get("status"):
                                        fetched = md.get("data", {}).get("fetched", [])
                                        ltp_map = {item["symbolToken"]: item["ltp"] for item in fetched}
                                        oi_map = {item["symbolToken"]: item.get("opnInterest", 0) for item in fetched}
                                        
                                        for st in strikes:
                                            st_opts = opts[opts['strike'] == st]
                                            ce = st_opts[st_opts['symbol'].str.endswith('CE')]
                                            pe = st_opts[st_opts['symbol'].str.endswith('PE')]
                                            
                                            ce_token = ce.iloc[0]['token'] if not ce.empty else None
                                            pe_token = pe.iloc[0]['token'] if not pe.empty else None
                                            
                                            option_chain_data.append({
                                                "CE_OI": oi_map.get(ce_token, 0),
                                                "CE_LTP": ltp_map.get(ce_token),
                                                "Strike": st,
                                                "PE_LTP": ltp_map.get(pe_token),
                                                "PE_OI": oi_map.get(pe_token, 0)
                                            })
                            except Exception as e:
                                logger.error(f"Failed to fetch Option Chain: {e}")
                                
                            last_processed_timestamp = current_timestamp
                            save_state(df_raw_aligned, simulators, option_chain_data)

                # Reset for new minute
                current_minute = minute_floor
                current_candle = {
                    "time": int(minute_floor.timestamp()),
                    "open": ltp,
                    "high": ltp,
                    "low": ltp,
                    "close": ltp
                }
            else:
                # Update current minute candle
                if current_candle:
                    current_candle["high"] = max(current_candle["high"], ltp)
                    current_candle["low"] = min(current_candle["low"], ltp)
                    current_candle["close"] = ltp

        except Exception as e:
            logger.error(f"Loop Exception: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(5)
            
def save_state(df_raw, simulators, option_chain_data=None):
    out = {
        "market_data": {
            "timestamp": df_raw["timestamp"].astype(str).tolist(),
            "open": df_raw["open"].tolist(),
            "high": df_raw["high"].tolist(),
            "low": df_raw["low"].tolist(),
            "close": df_raw["close"].tolist()
        },
        "models": {},
        "option_chain": option_chain_data or []
    }
    
    for name, sim in simulators.items():
        out["models"][name] = {
            "capital": sim.capital,
            "trades": sim.trades,
            "equity_curve": sim.equity_curve,
            "equity_times": sim.equity_times,
            "net_pnl": sim.capital - 100000.0,
            "open_position": sim.position,
            "recent_signals": sim.recent_signals
        }
        
    with open("data/live_paper_trading.json", "w") as f:
        json.dump(out, f)
    logger.info("Saved Live State to data/live_paper_trading.json")

if __name__ == "__main__":
    main()
