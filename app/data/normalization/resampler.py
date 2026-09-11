import pandas as pd
from typing import List, Dict, Any
from loguru import logger

class DataResampler:
    """
    Resamples raw tick data into 1-minute OHLCV candles.
    """
    @staticmethod
    def resample_to_ohlcv(ticks: List[Dict[str, Any]], timeframe='1min') -> List[Dict[str, Any]]:
        if not ticks:
            return []

        df = pd.DataFrame(ticks)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)

        ohlcv_list = []

        # Group by symbol/token and resample
        for token, group in df.groupby('token'):
            # Resample to specified timeframe
            resampled = group.resample(timeframe).agg({
                'ltp': ['first', 'max', 'min', 'last'],
                'volume': 'sum',
                'open_interest': 'last', # OI is snapshot, so we take the last known OI
                'symbol': 'first' # Symbol should be constant for the token
            })
            
            # Flatten multi-level columns
            resampled.columns = ['open', 'high', 'low', 'close', 'volume', 'open_interest', 'symbol']
            
            # Drop NaN rows (intervals where no ticks occurred)
            resampled = resampled.dropna(subset=['open', 'close'])

            # Reset index to get timestamp back as a column
            resampled = resampled.reset_index()

            for _, row in resampled.iterrows():
                ohlcv_list.append({
                    'timestamp': row['timestamp'].to_pydatetime(),
                    'symbol': row['symbol'],
                    'open': row['open'],
                    'high': row['high'],
                    'low': row['low'],
                    'close': row['close'],
                    'volume': int(row['volume']),
                    'open_interest': int(row['open_interest']) if pd.notna(row['open_interest']) else 0
                })

        logger.info(f"Resampled {len(ticks)} ticks into {len(ohlcv_list)} {timeframe} OHLCV candles.")
        return ohlcv_list
