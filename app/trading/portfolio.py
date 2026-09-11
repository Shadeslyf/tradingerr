import os
import uuid
from datetime import datetime
from loguru import logger
from typing import Dict, List, Any, Optional

from app.database.models import SessionLocal
from app.database.repositories import TradeRepository

class PaperPortfolioManager:
    def __init__(self, stop_loss_pct: float = 15.0, take_profit_pct: float = 30.0):
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.session = SessionLocal()
        self.repo = TradeRepository(self.session)
        
        # Load any existing open trades from DB
        self.open_trades = self.repo.get_open_trades()
        self.current_prices: Dict[str, float] = {}
        
        if self.open_trades:
            group_id = self.open_trades[0].group_id
            logger.info(f"Loaded {len(self.open_trades)} active trades for group {group_id}")
            for t in self.open_trades:
                self.current_prices[t.token] = t.entry_price

    def on_tick(self, token: str, ltp: float, timestamp: datetime):
        """
        Called on every single tick. Updates cached price and checks group PnL.
        """
        if not self.open_trades:
            return
            
        # Is this tick relevant to our open trades?
        relevant = any(t.token == token for t in self.open_trades)
        if not relevant:
            return
            
        # Update current price
        self.current_prices[token] = ltp
        
        # Calculate group PnL
        self._check_group_pnl(timestamp)

    def _check_group_pnl(self, timestamp: datetime):
        total_entry_value = 0.0
        total_current_value = 0.0
        
        for trade in self.open_trades:
            # For BUY trades: PnL is Current - Entry
            # For SELL trades: PnL is Entry - Current
            # To calculate net correctly, we can track total absolute value or net credit/debit.
            # Simpler: just calculate individual PnL and sum them up.
            
            entry = trade.entry_price
            current = self.current_prices.get(trade.token, entry)
            
            if trade.action == 'BUY':
                pnl = current - entry
            else: # SELL
                pnl = entry - current
                
            total_entry_value += entry
            total_current_value += pnl
            
        # If total_entry_value is 0 (should not happen), avoid division by zero
        if total_entry_value == 0:
            return
            
        pnl_pct = (total_current_value / total_entry_value) * 100
        
        # Check Stop Loss
        if pnl_pct <= -self.stop_loss_pct:
            logger.warning(f"STOP LOSS HIT! Net PnL: {pnl_pct:.2f}%")
            self._close_all_trades(timestamp, "SL")
            
        # Check Take Profit
        elif pnl_pct >= self.take_profit_pct:
            logger.success(f"TAKE PROFIT HIT! Net PnL: {pnl_pct:.2f}%")
            self._close_all_trades(timestamp, "TP")

    def execute_basket(self, basket: List[Dict[str, Any]], signal: int, timestamp: datetime):
        """
        Executes a group of trades simultaneously.
        basket format: [{'action': 'BUY', 'token': '123', 'symbol': '...', 'option_type': 'CE', 'price': 100.0}]
        """
        if self.open_trades:
            # We are already in a position.
            logger.info("Signal received but a position is already open. Waiting for closure.")
            return

        if not basket:
            return

        group_id = str(uuid.uuid4())
        logger.info(f"Executing NEW basket of {len(basket)} trades. Group: {group_id}")
        
        for leg in basket:
            trade_data = {
                'group_id': group_id,
                'action': leg['action'],
                'symbol': leg['symbol'],
                'token': leg['token'],
                'option_type': leg['option_type'],
                'entry_time': timestamp,
                'entry_price': leg['price'],
                'status': 'OPEN'
            }
            self.repo.create_trade(trade_data)
            self.current_prices[leg['token']] = leg['price']
            
        self.open_trades = self.repo.get_open_trades()

    def _close_all_trades(self, timestamp: datetime, reason: str):
        if not self.open_trades:
            return
            
        total_pnl = 0.0
        for trade in self.open_trades:
            entry = trade.entry_price
            exit_price = self.current_prices.get(trade.token, entry)
            
            if trade.action == 'BUY':
                pnl = exit_price - entry
            else:
                pnl = entry - exit_price
                
            pnl_pct = (pnl / entry) * 100 if entry > 0 else 0
            total_pnl += pnl_pct
            
            update_data = {
                'exit_time': timestamp,
                'exit_price': exit_price,
                'pnl': pnl_pct,
                'status': 'CLOSED',
                'exit_reason': reason
            }
            self.repo.update_trade(trade.id, update_data)
            
        logger.info(f"Closed {len(self.open_trades)} trades. Reason: {reason} | Net PnL: {total_pnl:.2f}%")
        self.open_trades = []
        self.current_prices.clear()
        
    def close_all_eod(self, timestamp: datetime, current_prices: Dict[str, float]):
        """
        Called at 3:15 PM or end of session to square off open intraday trades.
        """
        if self.open_trades:
            # Update cache with final prices
            for token, ltp in current_prices.items():
                if token in self.current_prices:
                    self.current_prices[token] = ltp
                    
            self._close_all_trades(timestamp, "EOD")
