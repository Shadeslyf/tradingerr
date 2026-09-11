import pandas as pd
import numpy as np
from typing import Dict, Any, List

class Metrics:
    """
    Calculates institutional-grade trading metrics from executed trades.
    """
    
    @staticmethod
    def calculate(orders: Dict[str, Dict[str, Any]], initial_capital: float) -> Dict[str, Any]:
        """
        Orders dict contains individual legs. We need to group them by trade/time 
        to calculate actual strategy PnL, but for simplicity we can track the exact 
        portfolio equity curve over time if we had timestamps.
        
        Since PaperBroker calculates exact costs and cash PnL, we can approximate 
        the metrics from the order ledger.
        """
        if not orders:
            return {}
            
        df = pd.DataFrame(list(orders.values()))
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        # We need to pair BUY and SELL to calculate realized PnL.
        # This is complex in a multi-leg setup. 
        # For the backtest metrics, it is easier if we reconstruct the PnL 
        # from the RiskEngine's capital curve. 
        # Let's write a simplified metric assuming we are passed a series of realized trade PnLs.
        pass

    @staticmethod
    def from_pnl_series(pnl_series: List[float], initial_capital: float) -> Dict[str, Any]:
        """
        Calculate metrics given a list of net cash PnLs for closed baskets.
        """
        if not pnl_series:
            return {}
            
        pnls = np.array(pnl_series)
        
        total_trades = len(pnls)
        winning_trades = len(pnls[pnls > 0])
        losing_trades = len(pnls[pnls <= 0])
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        gross_profit = pnls[pnls > 0].sum() if winning_trades > 0 else 0
        gross_loss = abs(pnls[pnls <= 0].sum()) if losing_trades > 0 else 0
        
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
        
        avg_win = pnls[pnls > 0].mean() if winning_trades > 0 else 0
        avg_loss = pnls[pnls <= 0].mean() if losing_trades > 0 else 0
        
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * abs(avg_loss))
        
        # Equity curve
        equity = initial_capital + np.cumsum(pnls)
        peak = np.maximum.accumulate(equity)
        drawdown = (equity - peak) / peak
        max_drawdown = abs(drawdown.min()) * 100
        
        total_pnl = pnls.sum()
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate * 100,
            'profit_factor': profit_factor,
            'average_win': avg_win,
            'average_loss': avg_loss,
            'expectancy': expectancy,
            'max_drawdown_pct': max_drawdown,
            'total_net_pnl': total_pnl,
            'final_capital': initial_capital + total_pnl
        }
