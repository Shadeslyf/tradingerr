from datetime import datetime
from loguru import logger
from typing import Dict, Optional, Tuple, List, Any

from app.api.instrument_manager import InstrumentManager
from app.trading.portfolio import PaperPortfolioManager

class PaperExecutor:
    def __init__(self, portfolio: PaperPortfolioManager, instrument_manager: InstrumentManager):
        self.portfolio = portfolio
        self.instrument_manager = instrument_manager
        self.underlying = "NIFTY"
        
    def process_signal(self, signal: int, spot_ltp: float, timestamp: datetime, latest_options_ticks: Dict[str, float]):
        """
        Translates a Regime Signal into a Hybrid Multi-leg Strategy.
        1: Bull Put Spread (Sell ATM PE, Buy ATM-100 PE)
        2: Bear Call Spread (Sell ATM CE, Buy ATM+100 CE)
        0: Iron Condor (Sell ATM+100 CE, Buy ATM+200 CE, Sell ATM-100 PE, Buy ATM-200 PE)
        """
        try:
            atm_strike = self.instrument_manager.get_atm_strike(self.underlying, spot_ltp, step=50)
        except Exception as e:
            logger.error(f"Failed to calculate ATM strike: {e}")
            return
            
        basket = []
        ev_data = None
        prob_win = 0.65 # Placeholder for now, later passed from AI
        
        from app.strategies.expected_value import ExpectedValueCalculator
        
        if signal == 1:
            logger.info(f"Signal 1 (Bullish): Building Bull Put Spread at ATM {atm_strike}")
            basket = self._build_bull_put_spread(atm_strike, latest_options_ticks)
            if len(basket) == 2:
                ev_data = ExpectedValueCalculator.calculate_credit_spread(basket[0], basket[1], prob_win)
                
        elif signal == 2:
            logger.info(f"Signal 2 (Bearish): Building Bear Call Spread at ATM {atm_strike}")
            basket = self._build_bear_call_spread(atm_strike, latest_options_ticks)
            if len(basket) == 2:
                ev_data = ExpectedValueCalculator.calculate_credit_spread(basket[0], basket[1], prob_win)
                
        elif signal == 0:
            logger.info(f"Signal 0 (Range): Building Iron Condor around ATM {atm_strike}")
            basket = self._build_iron_condor(atm_strike, latest_options_ticks)
            if len(basket) == 4:
                call_ev = ExpectedValueCalculator.calculate_credit_spread(basket[0], basket[1], prob_win)
                put_ev = ExpectedValueCalculator.calculate_credit_spread(basket[2], basket[3], prob_win)
                ev_data = ExpectedValueCalculator.evaluate_iron_condor(call_ev, put_ev)
                
        if not basket or not ev_data:
            return
            
        # Step 2: Risk Engine Filter
        if not self.portfolio.risk_engine.evaluate_trade(ev_data):
            logger.warning("Trade rejected by Risk Engine based on EV/Capital.")
            return
            
        # Step 3: Execute
        self.portfolio.execute_basket(basket, signal, timestamp)

    def _get_leg(self, strike: float, option_type: str, action: str, prices: Dict[str, float]) -> Optional[Dict[str, Any]]:
        token = self.instrument_manager.get_option_token(self.underlying, strike, option_type)
        if not token:
            logger.warning(f"Could not find token for {self.underlying} {strike} {option_type}")
            return None
            
        price = prices.get(token)
        if not price or price <= 0:
            logger.warning(f"No price available for token {token} ({strike} {option_type})")
            return None
            
        symbol = self.instrument_manager.get_symbol_from_token(token) or f"{self.underlying}_{strike}_{option_type}"
        
        return {
            'action': action,
            'token': token,
            'symbol': symbol,
            'option_type': option_type,
            'price': price
        }

    def _build_bull_put_spread(self, atm: float, prices: Dict[str, float]) -> List[Dict[str, Any]]:
        # Sell ATM PE, Buy ATM-100 PE
        sell_leg = self._get_leg(atm, 'PE', 'SELL', prices)
        buy_leg = self._get_leg(atm - 100, 'PE', 'BUY', prices)
        if sell_leg and buy_leg:
            return [sell_leg, buy_leg]
        return []

    def _build_bear_call_spread(self, atm: float, prices: Dict[str, float]) -> List[Dict[str, Any]]:
        # Sell ATM CE, Buy ATM+100 CE
        sell_leg = self._get_leg(atm, 'CE', 'SELL', prices)
        buy_leg = self._get_leg(atm + 100, 'CE', 'BUY', prices)
        if sell_leg and buy_leg:
            return [sell_leg, buy_leg]
        return []

    def _build_iron_condor(self, atm: float, prices: Dict[str, float]) -> List[Dict[str, Any]]:
        # Bear Call Spread on top, Bull Put Spread on bottom
        sell_ce = self._get_leg(atm + 100, 'CE', 'SELL', prices)
        buy_ce = self._get_leg(atm + 200, 'CE', 'BUY', prices)
        sell_pe = self._get_leg(atm - 100, 'PE', 'SELL', prices)
        buy_pe = self._get_leg(atm - 200, 'PE', 'BUY', prices)
        
        if all([sell_ce, buy_ce, sell_pe, buy_pe]):
            return [sell_ce, buy_ce, sell_pe, buy_pe]
        return []
