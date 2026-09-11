import pytest
from datetime import datetime
from app.trading.portfolio import PaperPortfolioManager
from app.database.models import init_db

# Initialize database schema so tables exist
init_db()

class MockTradeRepo:
    def __init__(self):
        self.trades = []
        self.trade_id_counter = 1
        
    def create_trade(self, data):
        class DummyTrade:
            pass
        t = DummyTrade()
        for k, v in data.items():
            setattr(t, k, v)
        t.id = self.trade_id_counter
        self.trade_id_counter += 1
        self.trades.append(t)
        return t.id
        
    def update_trade(self, trade_id, data):
        for t in self.trades:
            if t.id == trade_id:
                for k, v in data.items():
                    setattr(t, k, v)
                
    def get_open_trades(self):
        return [t for t in self.trades if getattr(t, 'status', '') == 'OPEN']

class MockBroker:
    def __init__(self):
        self.orders = {}
        self.order_id_counter = 1
    def place_order(self, symbol, token, action, quantity, price, order_type="MARKET"):
        order_id = str(self.order_id_counter)
        self.order_id_counter += 1
        self.orders[order_id] = {
            'executed_price': price, # no slippage for test
            'transaction_costs': 0.0 # no costs for simple test
        }
        return order_id

class MockRiskEngine:
    def __init__(self):
        self.current_capital = 300000.0
    def apply_trade_result(self, pnl):
        self.current_capital += pnl

def test_multi_leg_stop_loss():
    broker = MockBroker()
    risk_engine = MockRiskEngine()
    portfolio = PaperPortfolioManager(broker, risk_engine, stop_loss_pct=15.0, take_profit_pct=30.0)
    portfolio.repo = MockTradeRepo()
    portfolio.open_trades = []
    portfolio.current_prices.clear()
    
    # Simulate Bull Put Spread
    # Sell ATM PE @ 100, Buy ATM-100 PE @ 50.
    # Total credit = 50.
    # Entry value tracked as sum of absolute prices: 100 + 50 = 150 for pct calculation
    basket = [
        {'action': 'SELL', 'token': 'pe_sell', 'symbol': 'NIFTY_PE', 'option_type': 'PE', 'price': 100.0},
        {'action': 'BUY', 'token': 'pe_buy', 'symbol': 'NIFTY_PE_OTM', 'option_type': 'PE', 'price': 50.0}
    ]
    
    portfolio.execute_basket(basket, 1, datetime.now())
    
    assert len(portfolio.open_trades) == 2
    
    # Market goes AGAINST us (Bullish trade, but market falls). Puts increase in value.
    # Sell leg goes to 120 (Loss of 20). Buy leg goes to 55 (Profit of 5).
    # Net PnL = -15.
    # Pct = -15 / 150 = -10%. (Should not hit SL of 15%).
    portfolio.current_prices['pe_sell'] = 120.0
    portfolio.on_tick('pe_buy', 55.0, datetime.now())
    assert len(portfolio.open_trades) == 2
    
    # Market falls further.
    # Sell leg goes to 135 (-35). Buy leg goes to 60 (+10).
    # Net PnL = -25.
    # Pct = -25 / 150 = -16.66%. Should hit SL of 15%.
    portfolio.current_prices['pe_sell'] = 135.0
    portfolio.on_tick('pe_buy', 60.0, datetime.now())
    assert len(portfolio.open_trades) == 0 # Closed
    
    closed_trades = portfolio.repo.trades
    assert closed_trades[0].status == 'CLOSED'
    assert closed_trades[0].exit_reason == 'SL'

def test_iron_condor_take_profit():
    broker = MockBroker()
    risk_engine = MockRiskEngine()
    portfolio = PaperPortfolioManager(broker, risk_engine, stop_loss_pct=15.0, take_profit_pct=30.0)
    portfolio.repo = MockTradeRepo()
    portfolio.open_trades = []
    portfolio.current_prices.clear()
    
    # Iron Condor (4 legs)
    basket = [
        {'action': 'SELL', 'token': 'ce_sell', 'symbol': 'CE1', 'option_type': 'CE', 'price': 100.0},
        {'action': 'BUY', 'token': 'ce_buy', 'symbol': 'CE2', 'option_type': 'CE', 'price': 50.0},
        {'action': 'SELL', 'token': 'pe_sell', 'symbol': 'PE1', 'option_type': 'PE', 'price': 100.0},
        {'action': 'BUY', 'token': 'pe_buy', 'symbol': 'PE2', 'option_type': 'PE', 'price': 50.0}
    ]
    # Total absolute entry value = 300.
    portfolio.execute_basket(basket, 0, datetime.now())
    
    assert len(portfolio.open_trades) == 4
    
    # Market stays range bound! All options lose value (theta decay).
    # Sold options drop to 20 (Profit 80 each = +160)
    # Bought options drop to 5 (Loss 45 each = -90)
    # Net PnL = +70.
    # Pct = +70 / 300 = +23.3%. Still under 30% TP.
    # Update all prices in cache first to simulate simultaneous tick arrival,
    # then trigger the PnL check so we don't hit false spikes due to sequential staleness.
    portfolio.current_prices['ce_sell'] = 20.0
    portfolio.current_prices['ce_buy'] = 5.0
    portfolio.current_prices['pe_sell'] = 20.0
    portfolio.on_tick('pe_buy', 5.0, datetime.now()) # Triggers check
    
    assert len(portfolio.open_trades) == 4
    
    # More theta decay.
    # Sold drop to 5 (+95 each = +190)
    # Bought drop to 1 (-49 each = -98)
    # Net PnL = +92.
    # Pct = +92 / 300 = +30.66%. TP HIT!
    portfolio.current_prices['ce_sell'] = 5.0
    portfolio.current_prices['ce_buy'] = 1.0
    portfolio.current_prices['pe_sell'] = 5.0
    portfolio.on_tick('pe_buy', 1.0, datetime.now()) # Triggers check
    assert len(portfolio.open_trades) == 0
    
    assert portfolio.repo.trades[0].exit_reason == 'TP'
