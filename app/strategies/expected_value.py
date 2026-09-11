from typing import List, Dict, Any, Tuple
from loguru import logger

class ExpectedValueCalculator:
    """
    Calculates the maximum profit, maximum loss, breakeven, and Expected Value (EV)
    of option spreads BEFORE execution.
    """
    
    @staticmethod
    def calculate_credit_spread(sell_leg: Dict[str, Any], buy_leg: Dict[str, Any], prob_win: float, lot_size: int = 50) -> Dict[str, Any]:
        """
        Calculates EV for a Defined Risk Credit Spread.
        sell_leg: {'strike': 24000, 'price': 100}
        buy_leg: {'strike': 23900, 'price': 50}
        """
        # Net premium received
        net_credit = sell_leg['price'] - buy_leg['price']
        
        # Spread width
        spread_width = abs(sell_leg['strike'] - buy_leg['strike'])
        
        # Max Profit = Net Credit Received
        max_profit_per_share = net_credit
        max_profit = max_profit_per_share * lot_size
        
        # Max Loss = Spread Width - Net Credit Received
        max_loss_per_share = spread_width - net_credit
        max_loss = max_loss_per_share * lot_size
        
        # Estimated Total Transaction Costs for a 2-leg strategy
        # We assume 1 lot. Roughly ₹40 brokerage + STT + GST + slippage (~0.5%)
        est_slippage = (sell_leg['price'] + buy_leg['price']) * 0.005 * lot_size
        est_fees = 60.0 # Conservative flat estimate for a 2-leg spread
        total_est_costs = est_slippage + est_fees
        
        prob_loss = 1.0 - prob_win
        
        # EV = (Prob Win * Avg Win) - (Prob Loss * Avg Loss) - Costs
        # Avg Win is conservatively the net credit.
        # Avg Loss is conservatively the max loss (assuming SL is hit).
        ev = (prob_win * max_profit) - (prob_loss * max_loss) - total_est_costs
        
        return {
            'net_credit': net_credit,
            'max_profit': max_profit,
            'max_loss': max_loss,
            'ev': ev,
            'total_est_costs': total_est_costs,
            'prob_win': prob_win,
            'prob_loss': prob_loss
        }

    @staticmethod
    def calculate_long_option(leg: Dict[str, Any], prob_win: float = 0.4, target_multiple: float = 2.0) -> Dict[str, Any]:
        """
        Calculates EV for a simple long option (buying a Call or Put).
        We assume our target is `target_multiple` * premium.
        """
        premium = leg['price']
        
        # Max loss is 100% of the premium paid
        max_loss = premium * 50 # lot size 50
        
        # Max profit is theoretically unlimited, but for EV we cap it at target
        target_profit = (premium * target_multiple * 50) - max_loss
        
        ev = (prob_win * target_profit) - ((1 - prob_win) * max_loss)
        
        return {
            'max_profit': float('inf'), # Theoretically
            'max_loss': max_loss,
            'ev': ev,
            'net_credit': -premium * 50,
            'spread_width': 0
        }

    @staticmethod
    def evaluate_iron_condor(call_spread: Dict[str, Any], put_spread: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates the EV of an Iron Condor by summing the net credit of both spreads.
        Max loss is usually the width of the wider spread minus total credit.
        """
        net_credit = call_spread['net_credit'] + put_spread['net_credit']
        max_profit = call_spread['max_profit'] + put_spread['max_profit']
        
        # In an Iron Condor, only one side can lose at a time.
        max_loss = max(call_spread['max_loss'], put_spread['max_loss']) - put_spread['max_profit']
        
        # Total costs
        total_costs = call_spread['total_est_costs'] + put_spread['total_est_costs']
        
        # We assume independent or combined prob win for range bound.
        prob_win = call_spread['prob_win'] # using the same AI confidence for the range
        prob_loss = 1.0 - prob_win
        
        ev = (prob_win * max_profit) - (prob_loss * max_loss) - total_costs
        
        return {
            'net_credit': net_credit,
            'max_profit': max_profit,
            'max_loss': max_loss,
            'ev': ev,
            'total_est_costs': total_costs
        }
