from datetime import datetime, date
from loguru import logger

class DailyLimits:
    """
    Enforces maximum daily and weekly loss limits.
    """
    def __init__(self, max_daily_loss_pct: float = 1.5, max_weekly_loss_pct: float = 3.0):
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_weekly_loss_pct = max_weekly_loss_pct
        
        self.daily_pnl = 0.0
        self.weekly_pnl = 0.0
        self.last_reset_date = date.today()
        
    def add_trade_pnl(self, pnl_amount: float, capital: float):
        """
        Add closed trade PnL to daily/weekly accumulators.
        """
        today = date.today()
        if today > self.last_reset_date:
            # New day, reset daily
            self.daily_pnl = 0.0
            # If new week (Monday), reset weekly
            if today.weekday() == 0 and self.last_reset_date.weekday() != 0:
                self.weekly_pnl = 0.0
            self.last_reset_date = today
            
        self.daily_pnl += pnl_amount
        self.weekly_pnl += pnl_amount
        
        logger.info(f"Daily PnL updated: ₹{self.daily_pnl:.2f} | Weekly PnL: ₹{self.weekly_pnl:.2f}")

    def check_limits(self, capital: float) -> bool:
        """
        Returns False if limits are breached.
        """
        max_daily_amount = capital * (self.max_daily_loss_pct / 100.0)
        max_weekly_amount = capital * (self.max_weekly_loss_pct / 100.0)
        
        if self.daily_pnl <= -max_daily_amount:
            logger.error(f"MAX DAILY LOSS BREACHED! Loss: ₹{self.daily_pnl:.2f} (Limit: ₹{max_daily_amount:.2f})")
            return False
            
        if self.weekly_pnl <= -max_weekly_amount:
            logger.error(f"MAX WEEKLY LOSS BREACHED! Loss: ₹{self.weekly_pnl:.2f} (Limit: ₹{max_weekly_amount:.2f})")
            return False
            
        return True
