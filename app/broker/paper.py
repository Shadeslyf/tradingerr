import uuid
from typing import List, Dict, Any, Optional
from loguru import logger
from datetime import datetime

from app.broker.base import BrokerClient
from app.database.models import SessionLocal
from app.database.repositories import TradeRepository

class PaperBroker(BrokerClient):
    """
    A simulated broker that precisely mimics Angel One's interface.
    It calculates Indian F&O costs (Brokerage, STT, GST, Exchange Fees, Stamp Duty) and simulates slippage.
    """
    def __init__(self, slippage_pct: float = 0.005): # 0.5% slippage on option premium
        self.slippage_pct = slippage_pct
        self.session = SessionLocal()
        self.repo = TradeRepository(self.session)
        self.live_prices: Dict[str, float] = {}
        self.orders: Dict[str, Dict[str, Any]] = {}
        self.positions: Dict[str, Dict[str, Any]] = {} # keyed by token

    def login(self) -> bool:
        logger.info("PaperBroker: Simulated Login Successful")
        return True

    def get_instrument_master(self) -> List[Dict[str, Any]]:
        # Usually handled by InstrumentManager, but interface requires it
        return []

    def get_quote(self, token: str) -> float:
        return self.live_prices.get(token, 0.0)
        
    def update_live_price(self, token: str, price: float):
        self.live_prices[token] = price

    def _calculate_costs(self, action: str, price: float, quantity: int) -> float:
        """
        Calculates realistic transaction costs for NIFTY Options.
        Lot size is usually 25 or 50. Let's assume standard NIFTY.
        """
        turnover = price * quantity
        
        # 1. Brokerage: flat ₹20 per executed order (buy or sell)
        brokerage = 20.0
        
        # 2. STT (Securities Transaction Tax): 0.125% on SELL side only (on premium) for options
        stt = (0.00125 * turnover) if action == 'SELL' else 0.0
        
        # 3. Exchange Transaction Charge: approx 0.03503% on premium
        exchange_charges = 0.0003503 * turnover
        
        # 4. GST: 18% on (Brokerage + Exchange Charges)
        gst = 0.18 * (brokerage + exchange_charges)
        
        # 5. SEBI turnover fee: ₹10 per crore (0.0001%)
        sebi_charges = 0.000001 * turnover
        
        # 6. Stamp Duty: 0.003% on BUY side only
        stamp_duty = (0.00003 * turnover) if action == 'BUY' else 0.0
        
        total_cost = brokerage + stt + exchange_charges + gst + sebi_charges + stamp_duty
        return total_cost

    def place_order(self, symbol: str, token: str, action: str, quantity: int, price: float, order_type: str = "MARKET") -> str:
        """
        Simulate placing an order. Fills immediately with slippage.
        """
        order_id = str(uuid.uuid4())
        
        # Simulate slippage
        executed_price = price
        if action == 'BUY':
            executed_price = price * (1 + self.slippage_pct)
        elif action == 'SELL':
            executed_price = price * (1 - self.slippage_pct)
            
        costs = self._calculate_costs(action, executed_price, quantity)
        
        order = {
            'order_id': order_id,
            'symbol': symbol,
            'token': token,
            'action': action,
            'quantity': quantity,
            'requested_price': price,
            'executed_price': executed_price,
            'transaction_costs': costs,
            'status': 'COMPLETE',
            'timestamp': datetime.now()
        }
        self.orders[order_id] = order
        
        # Update pseudo-positions
        if token not in self.positions:
            self.positions[token] = {'quantity': 0, 'average_price': 0.0, 'total_cost': 0.0}
            
        pos = self.positions[token]
        if action == 'BUY':
            pos['quantity'] += quantity
            pos['total_cost'] += costs
            # Weighted average simplified
            pos['average_price'] = executed_price
        elif action == 'SELL':
            pos['quantity'] -= quantity
            pos['total_cost'] += costs
            # If closing, we keep avg price same for simplicity
            
        if pos['quantity'] == 0:
            del self.positions[token] # Position closed
            
        logger.info(f"PaperBroker: Order {action} {quantity} {symbol} @ {executed_price:.2f} (Costs: ₹{costs:.2f})")
        return order_id

    def cancel_order(self, order_id: str) -> bool:
        logger.warning("PaperBroker: Cannot cancel simulated market orders")
        return False

    def get_order_status(self, order_id: str) -> str:
        if order_id in self.orders:
            return self.orders[order_id]['status']
        return "UNKNOWN"
        
    def get_positions(self) -> List[Dict[str, Any]]:
        return [{'token': k, **v} for k, v in self.positions.items()]
