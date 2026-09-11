import pytest
from datetime import datetime
from app.trading.portfolio import PaperPortfolioManager
from app.database.models import init_db

# Initialize database schema so tables exist
init_db()

class MockTradeRepo:
    def __init__(self):
        self.trade = None
        self.trade_id_counter = 1
        
    def create_trade(self, data):
        class DummyTrade:
            pass
        t = DummyTrade()
        for k, v in data.items():
            setattr(t, k, v)
        t.id = self.trade_id_counter
        self.trade_id_counter += 1
        self.trade = t
        return t.id
        
    def update_trade(self, trade_id, data):
        if self.trade and self.trade.id == trade_id:
            for k, v in data.items():
                setattr(self.trade, k, v)
                
    def get_open_trade(self):
        if self.trade and getattr(self.trade, 'status', '') == 'OPEN':
            return self.trade
        return None

def test_stop_loss():
    portfolio = PaperPortfolioManager(stop_loss_pct=10.0, take_profit_pct=20.0)
    portfolio.repo = MockTradeRepo()
    
    # Enter trade
    portfolio.execute_signal(1, "12345", "NIFTY_CE", "CE", 100.0, datetime.now())
    
    assert portfolio.current_trade is not None
    assert portfolio.current_trade.entry_price == 100.0
    
    # Price drops to 95 (-5%) -> Should stay open
    portfolio.on_tick("12345", 95.0, datetime.now())
    assert portfolio.current_trade is not None
    
    # Price drops to 90 (-10%) -> Should hit SL and close
    portfolio.on_tick("12345", 90.0, datetime.now())
    assert portfolio.current_trade is None
    
    # Check updated trade in repo
    trade = portfolio.repo.trade
    assert trade.status == 'CLOSED'
    assert trade.exit_reason == 'SL'
    assert trade.exit_price == 90.0
    assert trade.pnl == -10.0

def test_take_profit():
    portfolio = PaperPortfolioManager(stop_loss_pct=10.0, take_profit_pct=20.0)
    portfolio.repo = MockTradeRepo()
    
    # Enter trade
    portfolio.execute_signal(2, "67890", "NIFTY_PE", "PE", 100.0, datetime.now())
    
    assert portfolio.current_trade is not None
    
    # Price rises to 110 (+10%) -> Should stay open
    portfolio.on_tick("67890", 110.0, datetime.now())
    assert portfolio.current_trade is not None
    
    # Price rises to 120 (+20%) -> Should hit TP and close
    portfolio.on_tick("67890", 120.0, datetime.now())
    assert portfolio.current_trade is None
    
    trade = portfolio.repo.trade
    assert trade.status == 'CLOSED'
    assert trade.exit_reason == 'TP'
    assert trade.exit_price == 120.0
    assert trade.pnl == 20.0

def test_signal_reversal():
    portfolio = PaperPortfolioManager()
    portfolio.repo = MockTradeRepo()
    
    # Buy Call
    portfolio.execute_signal(1, "111", "NIFTY_CE", "CE", 100.0, datetime.now())
    assert portfolio.current_trade is not None
    
    # Receive another Bullish signal -> Ignore
    portfolio.execute_signal(1, "111", "NIFTY_CE", "CE", 105.0, datetime.now())
    assert portfolio.current_trade is not None
    
    # Receive Bearish signal -> Close Call
    portfolio.execute_signal(2, "222", "NIFTY_PE", "PE", 100.0, datetime.now())
    assert portfolio.current_trade is None
    
    trade = portfolio.repo.trade
    assert trade.exit_reason == 'SIGNAL_REVERSAL'
