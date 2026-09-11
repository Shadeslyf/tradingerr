import pandas as pd
import numpy as np

class MarketStructureFeatures:
    @staticmethod
    def calculate_intraday_structure(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # We need date to group by day
        df['date'] = df.index.date
        
        # Current day high/low expanding
        df['day_high'] = df.groupby('date')['high'].expanding().max().reset_index(level=0, drop=True)
        df['day_low'] = df.groupby('date')['low'].expanding().min().reset_index(level=0, drop=True)
        
        # Opening range (first 15 mins)
        # We assume the index is datetime and sorted
        def get_or(group):
            if len(group) == 0:
                return group
            # Just take the first 15 rows if 1min timeframe
            or_high = group['high'].head(15).max()
            or_low = group['low'].head(15).min()
            group['or_high'] = or_high
            group['or_low'] = or_low
            return group

        df = df.groupby('date', group_keys=False).apply(get_or)

        # Distances
        if 'VWAP' in df.columns:
            df['dist_vwap_pct'] = (df['close'] - df['VWAP']) / df['VWAP'] * 100
        
        df['dist_day_high_pct'] = (df['day_high'] - df['close']) / df['close'] * 100
        df['dist_day_low_pct'] = (df['close'] - df['day_low']) / df['day_low'] * 100

        df.drop(columns=['date'], inplace=True, errors='ignore')
        return df

    @staticmethod
    def calculate_daily_structure(df: pd.DataFrame) -> pd.DataFrame:
        # Requires getting the previous day's data. 
        # Since this pipeline runs on an aggregated OHLCV df, we calculate daily metrics by grouping
        df = df.copy()
        df['date'] = df.index.date
        
        daily_df = df.groupby('date').agg({'high': 'max', 'low': 'min', 'close': 'last'})
        daily_df['prev_high'] = daily_df['high'].shift(1)
        daily_df['prev_low'] = daily_df['low'].shift(1)
        daily_df['prev_close'] = daily_df['close'].shift(1)
        
        # Merge back
        df = df.merge(daily_df[['prev_high', 'prev_low', 'prev_close']], left_on='date', right_index=True, how='left')
        
        # If no previous day, fill with current open to make gap 0 and avoid NaNs
        df['prev_close'] = df['prev_close'].fillna(df['open'])
        df['prev_high'] = df['prev_high'].fillna(df['open'])
        df['prev_low'] = df['prev_low'].fillna(df['open'])

        # Gap
        df['gap_pct'] = (df.groupby('date')['open'].transform('first') - df['prev_close']) / df['prev_close'] * 100

        df.drop(columns=['date'], inplace=True, errors='ignore')
        return df
