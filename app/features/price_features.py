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
        df['RSI'] = df['RSI'].fillna(50)
        return df

    @staticmethod
    def calculate_rsi_divergence(df: pd.DataFrame, lookback: int = 20) -> pd.DataFrame:
        """
        RSI Divergence features:
          - rsi_slope:         Rate of change of RSI over `lookback` bars (momentum of momentum)
          - price_rsi_div:     Sign divergence — price trending up but RSI trending down (bearish div)
                               or price trending down but RSI trending up (bullish div)
          - rsi_overbought:    1 if RSI > 70, else 0
          - rsi_oversold:      1 if RSI < 30, else 0
          - rsi_mid_cross:     +1 cross above 50, -1 cross below 50, 0 otherwise
        """
        df = df.copy()
        if 'RSI' not in df.columns:
            df = PriceFeatures.calculate_rsi(df)

        rsi = df['RSI']

        # RSI slope (momentum of RSI)
        df['rsi_slope'] = rsi.diff(lookback).fillna(0)

        # Price slope over same window
        price_slope = df['close'].diff(lookback).fillna(0)

        # Divergence: price up & RSI down → bearish = -1; price down & RSI up → bullish = +1
        bull_div = ((price_slope < 0) & (df['rsi_slope'] > 0)).astype(int)
        bear_div = ((price_slope > 0) & (df['rsi_slope'] < 0)).astype(int)
        df['rsi_divergence'] = bull_div - bear_div   # +1 bullish, -1 bearish, 0 neutral

        # Overbought / oversold flags
        df['rsi_overbought'] = (rsi > 70).astype(int)
        df['rsi_oversold']   = (rsi < 30).astype(int)

        # RSI mid-line cross (50 level)
        rsi_above = (rsi > 50).astype(int)
        df['rsi_mid_cross'] = rsi_above.diff().fillna(0)  # +1 bullish cross, -1 bearish cross

        return df

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period=14) -> pd.DataFrame:
        df = df.copy()
        high_low   = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close  = np.abs(df['low']  - df['close'].shift())
        ranges     = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['ATR']  = true_range.rolling(period, min_periods=1).mean()
        return df

    @staticmethod
    def calculate_vwap(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['date'] = df.index.date
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        df['tp_vol'] = df['typical_price'] * df['volume']
        cum_vol    = df.groupby('date')['volume'].cumsum()
        cum_tp_vol = df.groupby('date')['tp_vol'].cumsum()
        df['VWAP'] = np.where(cum_vol == 0, df['close'], cum_tp_vol / cum_vol)
        df.drop(columns=['date', 'typical_price', 'tp_vol'], inplace=True)
        return df

    @staticmethod
    def calculate_vwap_bands(df: pd.DataFrame, period: int = 20, multipliers=(1.0, 2.0)) -> pd.DataFrame:
        """
        VWAP Bands (rolling standard-deviation channels around VWAP):
          - vwap_std:          Rolling std of close-VWAP deviation
          - vwap_upper_1/2:    VWAP + 1σ/2σ
          - vwap_lower_1/2:    VWAP - 1σ/2σ
          - vwap_band_pos:     Position of close within bands: (close - lower1) / (upper1 - lower1)
                               0 = at lower band, 1 = at upper band, <0 or >1 = outside
          - vwap_breakout:     +1 above upper2, -1 below lower2, 0 within
        """
        df = df.copy()
        if 'VWAP' not in df.columns:
            df = PriceFeatures.calculate_vwap(df)

        deviation = df['close'] - df['VWAP']
        rolling_std = deviation.rolling(window=period, min_periods=5).std().fillna(0)
        df['vwap_std'] = rolling_std

        for mult in multipliers:
            label = str(mult).replace('.', '_')
            df[f'vwap_upper_{label}'] = df['VWAP'] + mult * rolling_std
            df[f'vwap_lower_{label}'] = df['VWAP'] - mult * rolling_std

        band_width = df['vwap_upper_1_0'] - df['vwap_lower_1_0']
        df['vwap_band_pos'] = np.where(
            band_width > 0,
            (df['close'] - df['vwap_lower_1_0']) / band_width,
            0.5
        )
        # Clip to reasonable range
        df['vwap_band_pos'] = df['vwap_band_pos'].clip(-1, 2)

        df['vwap_breakout'] = 0
        df.loc[df['close'] > df['vwap_upper_2_0'], 'vwap_breakout'] =  1
        df.loc[df['close'] < df['vwap_lower_2_0'], 'vwap_breakout'] = -1

        return df

    @staticmethod
    def calculate_volume_features(df: pd.DataFrame, spike_window: int = 20, spike_mult: float = 2.0) -> pd.DataFrame:
        """
        Volume Spike & Profile features:
          - vol_ma:           Rolling mean volume over `spike_window` bars
          - vol_ratio:        Current volume / rolling mean (relative strength)
          - vol_spike:        1 if volume > spike_mult × rolling mean, else 0
          - vol_spike_dir:    +1 spike on up-candle, -1 spike on down-candle, 0 no spike
          - vol_delta:        Close-to-open price change × volume (proxy for buying/selling pressure)
          - vol_cumulative:   Cumulative daily volume (as fraction of day's total so far)
        """
        df = df.copy()

        # Handle zero-volume data (index/spot — use bar count as proxy)
        vol = df['volume'].copy()
        all_zero = (vol == 0).all()
        if all_zero:
            # Proxy: use ATR-scaled bar as volume proxy
            vol = (df['high'] - df['low']).clip(lower=1e-6)

        vol_ma = vol.rolling(window=spike_window, min_periods=3).mean().fillna(vol)
        df['vol_ma']    = vol_ma
        df['vol_ratio'] = (vol / vol_ma.replace(0, np.nan)).fillna(1.0).clip(0, 20)
        df['vol_spike'] = (df['vol_ratio'] >= spike_mult).astype(int)

        candle_dir = np.sign(df['close'] - df['open'])
        df['vol_spike_dir'] = df['vol_spike'] * candle_dir

        df['vol_delta'] = (df['close'] - df['open']) * vol

        # Daily cumulative volume fraction
        df['_date'] = df.index.date
        if all_zero:
            atr_proxy = (df['high'] - df['low']).clip(lower=1e-6)
            daily_atr  = df.groupby('_date')['high'].transform(lambda g: (df.loc[g.index, 'high'] - df.loc[g.index, 'low']).clip(lower=1e-6).sum())
            cum_atr    = atr_proxy.groupby(df['_date']).cumsum()
            df['vol_cumulative'] = (cum_atr / daily_atr.replace(0, 1)).clip(0, 1)
        else:
            cum_vol    = df['volume'].groupby(df['_date']).cumsum()
            daily_vol  = df.groupby('_date')['volume'].transform('sum')
            df['vol_cumulative'] = (cum_vol / daily_vol.replace(0, 1)).clip(0, 1)

        df.drop(columns=['_date'], inplace=True, errors='ignore')
        return df

    @staticmethod
    def calculate_momentum(df: pd.DataFrame, periods=[5, 15]) -> pd.DataFrame:
        df = df.copy()
        for p in periods:
            df[f'ROC_{p}'] = df['close'].pct_change(periods=p) * 100
            if (df['volume'] == 0).all():
                df[f'VOL_MOM_{p}'] = 0.0
            else:
                df[f'VOL_MOM_{p}'] = (df['volume'].pct_change(periods=p) * 100).fillna(0)
            df[f'ROC_{p}'] = df[f'ROC_{p}'].fillna(0)
        return df

    @staticmethod
    def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20, std_mult: float = 2.0) -> pd.DataFrame:
        """
        Bollinger Bands:
          - bb_mid:    SMA of close
          - bb_upper:  mid + std_mult × std
          - bb_lower:  mid - std_mult × std
          - bb_width:  (upper - lower) / mid  → volatility measure
          - bb_pos:    (close - lower) / (upper - lower)  → 0-1 position within bands
          - bb_squeeze: 1 if bb_width < 20th percentile (low volatility, squeeze)
        """
        df = df.copy()
        mid   = df['close'].rolling(period, min_periods=5).mean()
        std   = df['close'].rolling(period, min_periods=5).std().fillna(0)
        upper = mid + std_mult * std
        lower = mid - std_mult * std

        df['bb_mid']   = mid
        df['bb_upper'] = upper
        df['bb_lower'] = lower
        band_w = (upper - lower) / mid.replace(0, np.nan)
        df['bb_width'] = band_w.fillna(0)
        df['bb_pos']   = np.where(
            (upper - lower) > 0,
            (df['close'] - lower) / (upper - lower),
            0.5
        )
        df['bb_pos'] = df['bb_pos'].clip(-0.5, 1.5)
        pct20 = band_w.rolling(200, min_periods=20).quantile(0.20)
        df['bb_squeeze'] = (band_w < pct20).astype(int)
        return df
