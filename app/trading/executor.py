from datetime import datetime
from loguru import logger
from typing import Dict

from app.api.instrument_manager import InstrumentManager
from app.trading.portfolio import PaperPortfolioManager

class PaperExecutor:
    def __init__(self, portfolio: PaperPortfolioManager, instrument_manager: InstrumentManager):
        self.portfolio = portfolio
        self.instrument_manager = instrument_manager
        
    def process_signal(self, signal: int, spot_ltp: float, timestamp: datetime, latest_options_ticks: Dict[str, float]):
        """
        Translates a generic ML signal (1=Bullish, 2=Bearish) into a specific option trade.
        latest_options_ticks is a dict mapping option token -> current ask price.
        """
        if signal not in [1, 2]:
            return # No action
            
        # We are only trading NIFTY for now
        underlying = "NIFTY"
        
        # 1. Determine Option Type based on signal
        option_type = 'CE' if signal == 1 else 'PE'
        
        # 2. Get the closest strike (ATM)
        try:
            atm_strike = self.instrument_manager.get_atm_strike(underlying, spot_ltp, step=50)
        except Exception as e:
            logger.error(f"Failed to calculate ATM strike: {e}")
            return
            
        # 3. Get the token for the nearest expiry ATM option
        token = self.instrument_manager.get_option_token(underlying, atm_strike, option_type)
        if not token:
            logger.warning(f"No valid token found for {underlying} {atm_strike} {option_type}")
            return
            
        # 4. Get the current Ask price to simulate a market buy
        # If we don't have the exact tick, we might fall back to the last known LTP, but we prefer Ask.
        # Here we just assume latest_options_ticks holds the LTP/Ask for simplicity.
        ask_price = latest_options_ticks.get(token)
        
        if not ask_price or ask_price <= 0:
            logger.warning(f"Cannot execute trade. No valid price data for token {token}")
            return
            
        # 5. Get the human-readable symbol
        symbol = self.instrument_manager.get_symbol_from_token(token)
        if not symbol:
            symbol = f"{underlying}_{atm_strike}_{option_type}"
            
        # 6. Send to Portfolio Manager
        self.portfolio.execute_signal(
            signal=signal,
            token=token,
            symbol=symbol,
            option_type=option_type,
            ask_price=ask_price,
            timestamp=timestamp
        )
