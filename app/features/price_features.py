import pandas as pd
import numpy as np

class PriceFeatures:
    @staticmethod
    def calculate_emas(df: pd.DataFrame, periods=[9, 21, 50]) -> pd.DataFrame:
        df = df.copy()
        for p in periods:
            df[f'EMA_{p}'] = df['close'].ewm(span=p, adjust=False).mean()
        return df

    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period=14) -> pd.DataFrame:
        df = df.copy()
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).fillna(0)
        loss = (-delta.where(delta < 0, 0)).fillna(0)
        
        avg_gain = gain.rolling(window=period, min_periods=1).mean()
        avg_loss = loss.rolling(window=period, min_periods=1).mean()
        
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))
        df['RSI'] = df['RSI'].fillna(50) # default neutral
        return df

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period=14) -> pd.DataFrame:
        df = df.copy()
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['ATR'] = true_range.rolling(period, min_periods=1).mean()
        return df

    @staticmethod
    def calculate_vwap(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        # Ensure we group by day for VWAP
        df['date'] = df.index.date
        
        # Calculate typical price
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        df['tp_vol'] = df['typical_price'] * df['volume']
        
        # Calculate cumulative volume and cumulative tp_vol per day
        cum_vol = df.groupby('date')['volume'].cumsum()
        cum_tp_vol = df.groupby('date')['tp_vol'].cumsum()
        
        # Avoid division by zero
        df['VWAP'] = np.where(cum_vol == 0, df['close'], cum_tp_vol / cum_vol)
        
        df.drop(columns=['date', 'typical_price', 'tp_vol'], inplace=True)
        return df

    @staticmethod
    def calculate_momentum(df: pd.DataFrame, periods=[5, 15]) -> pd.DataFrame:
        df = df.copy()
        for p in periods:
            df[f'ROC_{p}'] = df['close'].pct_change(periods=p) * 100
            df[f'VOL_MOM_{p}'] = df['volume'].pct_change(periods=p) * 100
        return df
