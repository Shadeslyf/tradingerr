import pandas as pd
import numpy as np
from loguru import logger

class RegimeLabeler:
    """
    Advanced Regime Labeler for 7 Market Regimes:
    1: STRONG_BULLISH
    2: BULLISH
    3: STRONG_BEARISH
    4: BEARISH
    5: RANGE
    6: HIGH_VOLATILITY
    7: UNCERTAIN
    """
    
    @staticmethod
    def apply_advanced_regime_labeling(
        df: pd.DataFrame, 
        horizon: int = 60, 
        r_strong_pct: float = 0.3, 
        r_weak_pct: float = 0.15,
        v_high_pct: float = 0.6,
        v_mid_pct: float = 0.3
    ) -> pd.DataFrame:
        """
        Calculates labels for each row in the DataFrame based on the forward window.
        """
        if 'close' not in df.columns or 'high' not in df.columns or 'low' not in df.columns:
            raise ValueError("DataFrame must contain 'close', 'high', 'low' columns for labeling.")
        
        df = df.copy()
        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values
        n = len(closes)
        
        labels = np.zeros(n, dtype=int)
        
        # We need relative changes
        r_strong = r_strong_pct / 100.0
        r_weak = r_weak_pct / 100.0
        v_high = v_high_pct / 100.0
        v_mid = v_mid_pct / 100.0

        for i in range(n - horizon):
            end_idx = i + horizon
            
            p0 = closes[i]
            p_end = closes[end_idx]
            
            path_highs = highs[i+1:end_idx+1]
            path_lows = lows[i+1:end_idx+1]
            
            H = np.max(path_highs)
            L = np.min(path_lows)
            
            forward_return = (p_end - p0) / p0
            forward_volatility = (H - L) / p0
            
            # Logic for 7 Regimes
            if forward_volatility > v_high:
                labels[i] = 6 # HIGH_VOLATILITY
            elif forward_return > r_strong:
                labels[i] = 1 # STRONG_BULLISH
            elif forward_return > r_weak:
                labels[i] = 2 # BULLISH
            elif forward_return < -r_strong:
                labels[i] = 3 # STRONG_BEARISH
            elif forward_return < -r_weak:
                labels[i] = 4 # BEARISH
            else:
                if forward_volatility > v_mid:
                    labels[i] = 7 # UNCERTAIN (Choppy, low net return but high swings)
                else:
                    labels[i] = 5 # RANGE (Low return, low swings)
                    
        df['label'] = labels
        df.loc[df.index[-horizon:], 'label'] = np.nan
        
        logger.info(f"Regime Labeling complete. Distribution: {df['label'].value_counts().to_dict()}")
        return df
