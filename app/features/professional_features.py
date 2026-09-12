import pandas as pd
import numpy as np

class ProfessionalFeatures:
    @staticmethod
    def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        df = df.copy()
        high = df['high']
        low = df['low']
        close = df['close']
        
        plus_dm = high.diff()
        minus_dm = low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        
        tr1 = pd.DataFrame(high - low)
        tr2 = pd.DataFrame(abs(high - close.shift(1)))
        tr3 = pd.DataFrame(abs(low - close.shift(1)))
        frames = [tr1, tr2, tr3]
        tr = pd.concat(frames, axis=1, join='inner').max(axis=1)
        atr = tr.rolling(period).mean()
        
        plus_di = 100 * (plus_dm.ewm(alpha=1/period).mean() / atr)
        minus_di = abs(100 * (minus_dm.ewm(alpha=1/period).mean() / atr))
        
        dx = (abs(plus_di - minus_di) / abs(plus_di + minus_di)) * 100
        adx_smooth = dx.ewm(alpha=1/period).mean()
        
        df['adx'] = adx_smooth.fillna(0)
        df['plus_di'] = plus_di.fillna(0)
        df['minus_di'] = minus_di.fillna(0)
        return df

    @staticmethod
    def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        df = df.copy()
        exp1 = df['close'].ewm(span=fast, adjust=False).mean()
        exp2 = df['close'].ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        histogram = macd - signal_line
        
        df['macd'] = macd
        df['macd_signal'] = signal_line
        df['macd_hist'] = histogram
        return df

    @staticmethod
    def calculate_obv(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        obv = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
        df['obv'] = obv
        # Add a smoothed OBV for trend detection
        df['obv_ema'] = obv.ewm(span=20, adjust=False).mean()
        return df

    @staticmethod
    def calculate_keltner_channels(df: pd.DataFrame, period: int = 20, atr_mult: float = 2.0) -> pd.DataFrame:
        df = df.copy()
        ema = df['close'].ewm(span=period, adjust=False).mean()
        
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.ewm(span=period, adjust=False).mean()
        
        upper = ema + (atr_mult * atr)
        lower = ema - (atr_mult * atr)
        
        df['kc_upper'] = upper
        df['kc_lower'] = lower
        df['kc_middle'] = ema
        df['kc_width'] = (upper - lower) / ema
        df['kc_pos'] = (df['close'] - lower) / (upper - lower)
        return df
