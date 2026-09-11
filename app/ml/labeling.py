import pandas as pd
import numpy as np
from loguru import logger

class TripleBarrierLabeler:
    """
    Implements the Triple Barrier Method for time-series labeling.
    Labels:
      1: Bullish (Upper barrier hit first)
      2: Bearish (Lower barrier hit first)
      0: Range-bound (Horizon barrier hit first without touching upper/lower)
    """
    
    @staticmethod
    def apply_triple_barrier(
        df: pd.DataFrame, 
        horizon: int = 60, 
        upper_barrier_pct: float = 0.2, 
        lower_barrier_pct: float = 0.2
    ) -> pd.DataFrame:
        """
        Calculates labels for each row in the DataFrame.
        df must have a 'close' column. Index should ideally be datetime, sorted.
        """
        if 'close' not in df.columns:
            raise ValueError("DataFrame must contain a 'close' column for labeling.")
        
        df = df.copy()
        closes = df['close'].values
        n = len(closes)
        
        labels = np.zeros(n, dtype=int)
        
        # Upper and lower multipliers
        upper_mult = 1.0 + (upper_barrier_pct / 100.0)
        lower_mult = 1.0 - (lower_barrier_pct / 100.0)

        for i in range(n):
            # If we are too close to the end, we can't look fully ahead, 
            # but we still check the available horizon.
            end_idx = min(i + horizon, n)
            
            p0 = closes[i]
            upper_target = p0 * upper_mult
            lower_target = p0 * lower_mult
            
            path = closes[i+1:end_idx+1]
            
            # Find the index where barriers are crossed
            upper_crossed_idx = np.argmax(path >= upper_target) if np.any(path >= upper_target) else -1
            lower_crossed_idx = np.argmax(path <= lower_target) if np.any(path <= lower_target) else -1
            
            # Determine which happens first
            if upper_crossed_idx != -1 and lower_crossed_idx != -1:
                if upper_crossed_idx < lower_crossed_idx:
                    labels[i] = 1 # Bullish
                elif lower_crossed_idx < upper_crossed_idx:
                    labels[i] = 2 # Bearish
                else:
                    # Crossed simultaneously in the same minute candle, we can treat as 0 or arbitrary.
                    # Since it's extremely volatile, let's say 0 to avoid false confidence.
                    labels[i] = 0
            elif upper_crossed_idx != -1:
                labels[i] = 1
            elif lower_crossed_idx != -1:
                labels[i] = 2
            else:
                labels[i] = 0 # Time horizon expired
                
        df['label'] = labels
        
        # We should drop the last `horizon` rows because they didn't have the full time to develop
        if n <= horizon:
            df['label'] = np.nan
        else:
            df.iloc[-horizon:, df.columns.get_loc('label')] = np.nan
            
        logger.info(f"Labeling complete. Distribution: {df['label'].value_counts().to_dict()}")
        return df
