import pandas as pd
import numpy as np

class CrossAssetFeatures:
    @staticmethod
    def calculate_cross_asset_features(df: pd.DataFrame, lookback: int = 15) -> pd.DataFrame:
        """
        Calculates cross-asset features based on VIX and Bank Nifty.
        If the required columns are missing (e.g. during live testing), it pads them with neutral values (0).
        """
        df = df.copy()
        
        # 1. India VIX Features
        if 'vix_close' in df.columns:
            # VIX Slope (Momentum)
            df['vix_slope'] = df['vix_close'].diff(lookback).fillna(0)
            # VIX % Change (Spike)
            df['vix_pct_change'] = df['vix_close'].pct_change(lookback).fillna(0) * 100
        else:
            # Pad missing
            df['vix_slope'] = 0.0
            df['vix_pct_change'] = 0.0
            
        # 2. Bank Nifty Features
        if 'bank_close' in df.columns and 'close' in df.columns:
            bank_ret = df['bank_close'].pct_change(lookback)
            nifty_ret = df['close'].pct_change(lookback)
            
            # Relative Strength: Positive means Bank Nifty is outperforming Nifty 50
            df['bank_nifty_rs'] = (bank_ret - nifty_ret).fillna(0) * 100
            
            # Divergence: 
            # +1 (Bullish Div) = Nifty 50 down, Bank Nifty up
            # -1 (Bearish Div) = Nifty 50 up, Bank Nifty down
            bull_div = ((nifty_ret < 0) & (bank_ret > 0)).astype(int)
            bear_div = ((nifty_ret > 0) & (bank_ret < 0)).astype(int)
            df['bank_nifty_div'] = bull_div - bear_div
        else:
            # Pad missing
            df['bank_nifty_rs'] = 0.0
            df['bank_nifty_div'] = 0
            
        # Drop the raw cross-asset columns as we don't want the model training on raw index prices
        df.drop(columns=['vix_close', 'bank_close'], inplace=True, errors='ignore')
        
        return df
