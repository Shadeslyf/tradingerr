import pandas as pd
import numpy as np

class BaselineStrategies:
    """
    Naive baseline strategies to compare against ML performance.
    """
    
    @staticmethod
    def vwap_ema_crossover(df: pd.DataFrame) -> pd.Series:
        """
        Baseline 1: Buy when 9 EMA > VWAP. Sell when 9 EMA < VWAP.
        Returns a signal series: 1 for Bullish, 2 for Bearish, 0 for Flat.
        """
        # Ensure we have required columns
        if 'vwap' not in df.columns or 'ema_9' not in df.columns:
            # Recompute simple version if missing
            typical_price = (df['high'] + df['low'] + df['close']) / 3
            df['vwap'] = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
            df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
            
        signals = np.zeros(len(df))
        
        # 1 = Bullish (EMA > VWAP)
        bullish_mask = df['ema_9'] > df['vwap']
        signals[bullish_mask] = 1
        
        # 2 = Bearish (EMA < VWAP)
        bearish_mask = df['ema_9'] < df['vwap']
        signals[bearish_mask] = 2
        
        return pd.Series(signals, index=df.index)

    @staticmethod
    def simple_momentum(df: pd.DataFrame) -> pd.Series:
        """
        Baseline 2: Simple momentum based on RSI and MACD.
        Returns 1 for Bullish, 2 for Bearish, 0 for Flat.
        """
        if 'rsi' not in df.columns:
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
        signals = np.zeros(len(df))
        
        # Over 60 is bullish momentum
        bullish_mask = df['rsi'] > 60
        signals[bullish_mask] = 1
        
        # Under 40 is bearish momentum
        bearish_mask = df['rsi'] < 40
        signals[bearish_mask] = 2
        
        return pd.Series(signals, index=df.index)
