from loguru import logger
from app.risk.daily_limits import DailyLimits
from app.risk.kill_switch import KillSwitch

class RiskEngine:
    """
    Master Risk Engine sitting between Strategy and Execution.
    Tracks capital and enforces rules.
    """
    def __init__(self, starting_capital: float = 300000.0, max_risk_per_trade_pct: float = 1.0):
        self.starting_capital = starting_capital
        self.current_capital = starting_capital
        self.max_risk_per_trade_pct = max_risk_per_trade_pct
        
        self.daily_limits = DailyLimits(max_daily_loss_pct=1.5, max_weekly_loss_pct=3.0)
        self.kill_switch = KillSwitch()
        self.trade_pnls = []
        
    def evaluate_trade(self, ev_data: dict) -> bool:
        """
        Receives Expected Value data. Returns True if trade is approved.
        """
        if self.kill_switch.is_triggered():
            logger.warning("Risk Engine: Trade rejected. Kill Switch is active.")
            return False
            
        if not self.daily_limits.check_limits(self.current_capital):
            logger.warning("Risk Engine: Trade rejected. Daily/Weekly loss limits reached.")
            return False
            
        # Check EV
        if ev_data['ev'] < 0:
            logger.warning(f"Risk Engine: Trade rejected. Negative Expected Value (EV = ₹{ev_data['ev']:.2f}).")
            return False
            
        # Check Max Risk per Trade
        max_allowed_risk_amount = self.current_capital * (self.max_risk_per_trade_pct / 100.0)
        if ev_data['max_loss'] > max_allowed_risk_amount:
            logger.warning(f"Risk Engine: Trade rejected. Max loss (₹{ev_data['max_loss']:.2f}) exceeds per-trade risk limit (₹{max_allowed_risk_amount:.2f}).")
            return False
            
        logger.info("Risk Engine: Trade APPROVED.")
        return True
        
    def apply_trade_result(self, pnl: float):
        """
        Update capital after a trade closes.
        """
        self.current_capital += pnl
        self.daily_limits.add_trade_pnl(pnl, self.current_capital)
        self.trade_pnls.append(pnl)
        logger.info(f"Risk Engine: Trade Result ₹{pnl:.2f}. Current Capital: ₹{self.current_capital:.2f}")
