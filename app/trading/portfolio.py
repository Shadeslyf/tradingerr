import os
from datetime import datetime
from loguru import logger
from typing import Dict, Any, Optional

from app.database.models import SessionLocal
from app.database.repositories import TradeRepository

class PaperPortfolioManager:
    def __init__(self, stop_loss_pct: float = 15.0, take_profit_pct: float = 30.0):
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.session = SessionLocal()
        self.repo = TradeRepository(self.session)
        
        # Load any existing open trade from DB
        self.current_trade = self.repo.get_open_trade()
        if self.current_trade:
            logger.info(f"Loaded active open trade from DB: {self.current_trade.symbol} at {self.current_trade.entry_price}")

    def on_tick(self, token: str, ltp: float, timestamp: datetime):
        """
        Called on every single tick. Checks if the current open position hits SL or TP.
        """
        if not self.current_trade:
            return
            
        if self.current_trade.token != token:
            return # Tick is not for our held option
            
        entry_price = self.current_trade.entry_price
        pnl_pct = ((ltp - entry_price) / entry_price) * 100
        
        # Check Stop Loss
        if pnl_pct <= -self.stop_loss_pct:
            logger.warning(f"STOP LOSS HIT! PnL: {pnl_pct:.2f}% | Token: {token} | LTP: {ltp}")
            self._close_trade(ltp, timestamp, "SL")
            
        # Check Take Profit
        elif pnl_pct >= self.take_profit_pct:
            logger.success(f"TAKE PROFIT HIT! PnL: {pnl_pct:.2f}% | Token: {token} | LTP: {ltp}")
            self._close_trade(ltp, timestamp, "TP")

    def execute_signal(self, signal: int, token: str, symbol: str, option_type: str, ask_price: float, timestamp: datetime):
        """
        Called by the executor when the ML model generates a trade signal.
        """
        if self.current_trade:
            # We are already in a trade.
            # If the new signal is the OPPOSITE of our current position, close the current position.
            if (self.current_trade.option_type == 'CE' and signal == 2) or \
               (self.current_trade.option_type == 'PE' and signal == 1):
                logger.info("Opposite signal received. Closing current position.")
                self._close_trade(ask_price, timestamp, "SIGNAL_REVERSAL")
                
                # We could immediately open the new trade, but for strict risk, 
                # let's wait for the next minute/signal.
            return

        if signal not in [1, 2]:
            return # 0 = No trade

        # Open new trade
        logger.info(f"Executing NEW BUY entry for {symbol} at {ask_price}")
        trade_data = {
            'symbol': symbol,
            'token': token,
            'option_type': option_type,
            'entry_time': timestamp,
            'entry_price': ask_price,
            'status': 'OPEN'
        }
        trade_id = self.repo.create_trade(trade_data)
        self.current_trade = self.repo.get_open_trade()

    def _close_trade(self, exit_price: float, timestamp: datetime, reason: str):
        if not self.current_trade:
            return
            
        entry = self.current_trade.entry_price
        pnl = exit_price - entry
        pnl_pct = (pnl / entry) * 100
        
        update_data = {
            'exit_time': timestamp,
            'exit_price': exit_price,
            'pnl': pnl_pct,
            'status': 'CLOSED',
            'exit_reason': reason
        }
        self.repo.update_trade(self.current_trade.id, update_data)
        logger.info(f"Trade Closed. ID: {self.current_trade.id} | Reason: {reason} | PnL: {pnl_pct:.2f}%")
        self.current_trade = None
        
    def close_all_eod(self, timestamp: datetime, current_prices: Dict[str, float]):
        """
        Called at 3:15 PM or end of session to square off open intraday trades.
        current_prices maps token -> ltp.
        """
        if self.current_trade:
            ltp = current_prices.get(self.current_trade.token, self.current_trade.entry_price)
            self._close_trade(ltp, timestamp, "EOD")
