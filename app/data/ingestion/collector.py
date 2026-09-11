import time
import threading
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
from loguru import logger
from SmartApi.smartWebSocketV2 import SmartWebSocketV2

from app.config.settings import settings
from app.broker.angel_one import AngelOneBroker
from app.market.instruments import InstrumentManager
from app.database.models import SessionLocal, init_db
from app.database.repositories import MarketDataRepository, OptionContractRepository

class MarketDataCollector:
    def __init__(self):
        self.broker = AngelOneBroker()
        self.sws = None
        self.instrument_manager = None
        self.active_tokens = []
        self.db_session = SessionLocal()
        self.tick_repo = MarketDataRepository(self.db_session)
        self.contract_repo = OptionContractRepository(self.db_session)

    def start(self):
        logger.info("Starting Market Data Collector...")
        init_db()

        if not self.broker.login():
            logger.error("Broker login failed. Cannot start collector.")
            return

        raw_instruments = self.broker.get_instrument_master()
        if not raw_instruments:
            logger.error("Failed to load instrument master.")
            return

        self.instrument_manager = InstrumentManager(raw_instruments)

        nifty_spot = self.instrument_manager.get_nifty_spot()
        if not nifty_spot:
            logger.error("NIFTY Spot not found in instrument master.")
            return

        # Let's get the NIFTY spot token. But Angel One WebSocket requires token and exchange type.
        # exchange type for NSE is 1, NFO is 2
        
        # We need the current LTP of NIFTY to find the ATM strike. 
        # Since we can't easily fetch a single LTP synchronously via the SmartAPI object without an active session (which we have),
        # let's use the SmartAPI ltpData method.
        try:
            res = self.broker.smart_api.ltpData("NSE", nifty_spot['symbol'], nifty_spot['token'])
            if res and res.get('status'):
                spot_ltp = res['data']['ltp']
                logger.info(f"Current NIFTY Spot LTP: {spot_ltp}")
            else:
                logger.error(f"Failed to fetch NIFTY Spot LTP: {res}")
                return
        except Exception as e:
            logger.error(f"Exception fetching LTP: {e}")
            return

        # Determine ATM Strike
        # NIFTY strikes are typically in multiples of 50
        atm_strike = round(spot_ltp / 50) * 50
        logger.info(f"Calculated ATM Strike: {atm_strike}")

        # Get relevant option contracts
        all_opts = self.instrument_manager.get_current_nifty_options()
        if all_opts.empty:
            logger.error("No options data available.")
            return
            
        # Get closest expiry
        all_opts['expiry_dt'] = pd.to_datetime(all_opts['expiry'], format='%d%b%Y', errors='coerce')
        closest_expiry = all_opts['expiry_dt'].min()
        current_opts = all_opts[all_opts['expiry_dt'] == closest_expiry]

        # Filter by strike range (e.g., ATM ± 10 strikes means ATM ± 500 points)
        strike_range_pts = settings.strike_range * 50
        target_opts = current_opts[
            (current_opts['strike'] >= atm_strike - strike_range_pts) & 
            (current_opts['strike'] <= atm_strike + strike_range_pts)
        ]

        logger.info(f"Selected {len(target_opts)} option contracts for collection.")

        # Save these contracts to the DB
        contracts_data = []
        for _, row in target_opts.iterrows():
            option_type = 'CE' if str(row['symbol']).endswith('CE') else 'PE'
            contracts_data.append({
                'underlying': row['name'],
                'expiry': row['expiry_dt'],
                'strike': float(row['strike']),
                'option_type': option_type,
                'symbol': row['symbol'],
                'token': row['token'],
                'lot_size': int(row['lotsize'])
            })
        self.contract_repo.save_contracts_bulk(contracts_data)

        # Prepare tokens for websocket
        # Format: { "exchangeType": 1 for NSE, 2 for NFO, "tokens": ["token1", "token2"] }
        nfo_tokens = target_opts['token'].tolist()
        nse_tokens = [nifty_spot['token']]

        correlation_id = "ai_trading_bot_1"
        action = 1 # 1=subscribe, 0=unsubscribe
        mode = 3 # 1=LTP, 2=Quote, 3=SnapQuote (for MarketTick with volume/OI etc)

        token_list = [
            {"exchangeType": 1, "tokens": nse_tokens},
            {"exchangeType": 2, "tokens": nfo_tokens}
        ]

        self.sws = SmartWebSocketV2(
            auth_token=self.broker.auth_token,
            api_key=self.broker.api_key,
            client_code=self.broker.client_id,
            feed_token=self.broker.feed_token
        )

        def on_data(wsapp, message):
            self._handle_tick(message)

        def on_open(wsapp):
            logger.info("WebSocket opened.")
            self.sws.subscribe(correlation_id, mode, token_list)
            logger.info(f"Subscribed to tokens: {token_list}")

        def on_error(wsapp, error):
            logger.error(f"WebSocket error: {error}")

        def on_close(wsapp, close_status_code, close_msg):
            logger.info(f"WebSocket closed: {close_status_code} - {close_msg}")

        self.sws.on_open = on_open
        self.sws.on_data = on_data
        self.sws.on_error = on_error
        self.sws.on_close = on_close

        logger.info("Connecting to WebSocket...")
        self.sws.connect()

    def _handle_tick(self, message):
        # Example message structure for SnapQuote (Mode 3):
        # {'type': 3, 'exchangeType': 1, 'token': '99926000', 'sequenceNumber': 123456,
        #  'exchangeTimeStamp': 1630456789123, 'lastTradedPrice': 1730000, ...}
        
        try:
            if not isinstance(message, dict) or 'token' not in message:
                return

            # Exchange 1 = NSE, 2 = NFO
            exchange = 'NSE' if message.get('exchangeType') == 1 else 'NFO'
            token = str(message.get('token'))
            
            # Angel returns prices divided by 100 for proper value
            ltp = message.get('lastTradedPrice', 0) / 100.0
            volume = message.get('volumeTradedToday', 0)
            oi = message.get('openInterest', 0)
            
            best_bid = 0.0
            best_ask = 0.0
            if 'bestFiveBuy' in message and len(message['bestFiveBuy']) > 0:
                best_bid = message['bestFiveBuy'][0].get('price', 0) / 100.0
            if 'bestFiveSell' in message and len(message['bestFiveSell']) > 0:
                best_ask = message['bestFiveSell'][0].get('price', 0) / 100.0

            timestamp_ms = message.get('exchangeTimeStamp', int(time.time() * 1000))
            ts = datetime.fromtimestamp(timestamp_ms / 1000.0)

            tick_data = {
                'timestamp': ts,
                'symbol': 'UNKNOWN', # We'd need a token-to-symbol map if we really want it here, but token is unique
                'token': token,
                'exchange': exchange,
                'ltp': ltp,
                'volume': volume,
                'open_interest': oi,
                'bid': best_bid,
                'ask': best_ask
            }

            self.tick_repo.save_tick(tick_data)
            logger.debug(f"Tick saved: {token} | {ltp}")
        except Exception as e:
            logger.error(f"Error handling tick: {e}")
