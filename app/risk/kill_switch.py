from loguru import logger
from datetime import datetime

class KillSwitch:
    """
    Emergency kill switch for the trading system.
    """
    def __init__(self):
        self.triggered = False
        self.reason = ""
        
    def trigger(self, reason: str):
        if not self.triggered:
            self.triggered = True
            self.reason = reason
            logger.critical(f"KILL SWITCH TRIGGERED! Reason: {reason}")
            # In a live system, this would fire an SMS or email alert
            
    def is_triggered(self) -> bool:
        return self.triggered
        
    def check_market_data_staleness(self, last_tick_time: datetime, max_delay_seconds: int = 120):
        """
        If we haven't received a tick in 2 minutes during market hours, trigger switch.
        """
        now = datetime.now()
        # Ensure we are in market hours (09:15 to 15:30)
        if now.hour < 9 or (now.hour == 9 and now.minute < 15) or (now.hour == 15 and now.minute > 30) or now.hour > 15:
            return # Ignore outside market hours
            
        delay = (now - last_tick_time).total_seconds()
        if delay > max_delay_seconds:
            self.trigger(f"Stale market data! Last tick was {delay:.1f} seconds ago.")
