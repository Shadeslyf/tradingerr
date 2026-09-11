import pandas as pd
import numpy as np
from typing import Dict, List, Any
from loguru import logger
from datetime import datetime

from app.broker.paper import PaperBroker
from app.risk.portfolio import RiskEngine
from app.trading.portfolio import PaperPortfolioManager
from app.trading.executor import PaperExecutor

class BacktestEngine:
    """
    Event-driven backtesting engine for options strategies.
    Simulates path-dependent execution over historical data.
    """
    def __init__(self, initial_capital: float = 300000.0, slippage_pct: float = 0.005):
        self.broker = PaperBroker(slippage_pct=slippage_pct)
        self.risk_engine = RiskEngine(starting_capital=initial_capital)
        self.portfolio = PaperPortfolioManager(self.broker, self.risk_engine)
        
        # We need a mock instrument manager for tests
        class MockInstrumentManager:
            def get_atm_strike(self, underlying, spot, step=50):
                return int(round(spot / step) * step)
            def get_option_token(self, underlying, strike, option_type):
                return f"{underlying}_{int(strike)}_{option_type}"
            def get_symbol_from_token(self, token):
                return token
                
        self.executor = PaperExecutor(self.portfolio, MockInstrumentManager())
        
        self.trade_log: List[Dict[str, Any]] = []

    def simulate_option_price(self, spot: float, strike: float, option_type: str, days_to_expiry: float = 1.0) -> float:
        """
        Very crude intrinsic + time value estimator since we lack real historical tick data.
        In production, this must use real historical option OHLCV.
        """
        intrinsic = max(0, spot - strike) if option_type == 'CE' else max(0, strike - spot)
        # Time value peaks at ATM and decays outward
        distance = abs(spot - strike)
        # At ATM (dist=0), time value is 100. At dist=200, time value is 0.
        time_value = max(0, 100 - distance/2) * np.sqrt(max(0.1, days_to_expiry))
        return intrinsic + time_value

    def run(self, df: pd.DataFrame, signals: pd.Series):
        """
        Runs the event-driven loop.
        df: Dataframe with 'close' (Spot), 'timestamp'
        signals: Series matching df.index with values 1(Bull), 2(Bear), 0(Range), -1(Flat)
        """
        logger.info(f"Starting Backtest on {len(df)} rows. Initial Capital: ₹{self.risk_engine.current_capital:.2f}")
        
        for idx in range(len(df)):
            row = df.iloc[idx]
            signal = signals.iloc[idx]
            timestamp = row['timestamp'] if 'timestamp' in row else df.index[idx]
            spot = row['close']
            
            # 1. Update Portfolio on Tick (SL / TP checks)
            if self.portfolio.open_trades:
                # Simulate the current prices of held options
                current_ticks = {}
                for trade in self.portfolio.open_trades:
                    # Parse strike and type from token (e.g. NIFTY_24000_CE)
                    parts = trade.token.split('_')
                    if len(parts) >= 3:
                        strike = float(parts[1])
                        opt_type = parts[2]
                        # Assume 1 day to expiry for simulation
                        sim_price = self.simulate_option_price(spot, strike, opt_type, 1.0)
                        current_ticks[trade.token] = sim_price
                        self.portfolio.on_tick(trade.token, sim_price, timestamp)
                        
            # 2. Check End of Day Square Off
            if isinstance(timestamp, datetime) and timestamp.hour == 15 and timestamp.minute >= 15:
                if self.portfolio.open_trades:
                    self.portfolio.close_all_eod(timestamp, current_ticks)
                continue
                
            # 3. Process New Signals if Flat
            if not self.portfolio.open_trades and signal in [1, 2, 3, 4, 5, 6, 7]:
                # Generate mock option prices for the executor
                atm = int(round(spot / 50) * 50)
                strikes = [atm - 200, atm - 100, atm, atm + 100, atm + 200]
                latest_ticks = {}
                for k in strikes:
                    latest_ticks[f"NIFTY_{int(k)}_CE"] = self.simulate_option_price(spot, k, 'CE', 1.0)
                    latest_ticks[f"NIFTY_{int(k)}_PE"] = self.simulate_option_price(spot, k, 'PE', 1.0)
                    
                self.executor.process_signal(signal, spot, timestamp, latest_ticks)
                
        # Close any remaining open trades at the end of the simulation
        if self.portfolio.open_trades:
            self.portfolio.close_all_eod(datetime.now(), {})
            
        logger.info(f"Backtest Complete. Final Capital: ₹{self.risk_engine.current_capital:.2f}")
        return self.broker.orders
