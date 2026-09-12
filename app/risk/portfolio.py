from loguru import logger
from typing import Tuple
from app.risk.daily_limits import DailyLimits
from app.risk.kill_switch import KillSwitch
from app.risk.position_sizing import PositionSizer

class RiskEngine:
    """
    Master Risk Engine sitting between Strategy and Execution.
    Tracks capital and enforces rules.
    """
    def __init__(self, starting_capital: float = 300000.0, max_risk_per_trade_pct: float = 1.0, sizing_method: str = "fixed_fractional"):
        self.starting_capital = starting_capital
        self.current_capital = starting_capital
        self.max_risk_per_trade_pct = max_risk_per_trade_pct
        self.sizing_method = sizing_method
        
        self.daily_limits = DailyLimits(max_daily_loss_pct=1.5, max_weekly_loss_pct=3.0)
        self.kill_switch = KillSwitch()
        self.trade_pnls = []
        
    def evaluate_trade(self, ev_data: dict) -> Tuple[bool, int]:
        """
        Receives Expected Value data. Returns (True, quantity) if trade is approved.
        """
        if self.kill_switch.is_triggered():
            logger.warning("Risk Engine: Trade rejected. Kill Switch is active.")
            return False, 0
            
        if not self.daily_limits.check_limits(self.current_capital):
            logger.warning("Risk Engine: Trade rejected. Daily/Weekly loss limits reached.")
            return False, 0
            
        # Check EV
        if ev_data.get('ev', 0) < 0:
            logger.warning(f"Risk Engine: Trade rejected. Negative Expected Value (EV = ₹{ev_data.get('ev', 0):.2f}).")
            return False, 0
            
        # Determine Position Size
        if self.sizing_method == "kelly":
            quantity = PositionSizer.calculate_kelly_fractional(self.current_capital, ev_data)
        else:
            quantity = PositionSizer.calculate_fixed_fractional(self.current_capital, ev_data, self.max_risk_per_trade_pct)
            
        if quantity <= 0:
            logger.warning("Risk Engine: Trade rejected. Calculated position size is 0 (risk limits too tight or edge too small).")
            return False, 0
            
        logger.info(f"Risk Engine: Trade APPROVED. Allocated Quantity: {quantity}")
        return True, quantity
        
    def apply_trade_result(self, pnl: float):
        """
        Update capital after a trade closes.
        """
        self.current_capital += pnl
        self.daily_limits.add_trade_pnl(pnl, self.current_capital)
        self.trade_pnls.append(pnl)
        logger.info(f"Risk Engine: Trade Result ₹{pnl:.2f}. Current Capital: ₹{self.current_capital:.2f}")
