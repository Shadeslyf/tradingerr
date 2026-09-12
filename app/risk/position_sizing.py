import math

class PositionSizer:
    @staticmethod
    def calculate_fixed_fractional(capital: float, ev_data: dict, risk_pct: float = 1.0, lot_size: int = 50) -> int:
        """
        Calculates the quantity to trade based on a fixed risk percentage of capital.
        """
        max_loss_per_lot = ev_data.get('max_loss', 0)
        if max_loss_per_lot <= 0:
            return 0
            
        risk_amount = capital * (risk_pct / 100.0)
        
        # Calculate how many lots we can afford
        num_lots = math.floor(risk_amount / max_loss_per_lot)
        return max(0, num_lots * lot_size)

    @staticmethod
    def calculate_kelly_fractional(capital: float, ev_data: dict, fraction: float = 0.5, lot_size: int = 50) -> int:
        """
        Calculates quantity based on the Fractional Kelly Criterion.
        """
        prob_win = ev_data.get('prob_win', 0)
        prob_loss = ev_data.get('prob_loss', 1 - prob_win)
        
        avg_win = ev_data.get('max_profit', 0)
        avg_loss = ev_data.get('max_loss', 0)
        
        if avg_loss <= 0 or avg_win <= 0 or prob_win <= 0:
            return 0
            
        win_loss_ratio = avg_win / avg_loss
        
        # Kelly % = W - ((1-W) / (Avg Win / Avg Loss))
        kelly_pct = prob_win - (prob_loss / win_loss_ratio)
        
        if kelly_pct <= 0:
            return 0 # Negative edge, don't trade
            
        # Apply fractional kelly (e.g. Half-Kelly)
        adj_kelly_pct = kelly_pct * fraction
        
        # The adjusted kelly pct tells us what percentage of capital to risk
        allocated_risk = capital * adj_kelly_pct
        
        num_lots = math.floor(allocated_risk / avg_loss)
        return max(0, num_lots * lot_size)
