import pandas as pd

class TimeFeatures:
    @staticmethod
    def calculate_time_features(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # Assuming index is datetime
        times = pd.Series(df.index, index=df.index)
        
        df['hour'] = times.dt.hour
        df['minute'] = times.dt.minute
        df['day_of_week'] = times.dt.dayofweek
        
        # Minute since market open (9:15)
        # Calculate as: (hour - 9)*60 + (minute - 15)
        mins_since_open = (df['hour'] - 9) * 60 + (df['minute'] - 15)
        # Clip at 0 for pre-market
        df['mins_since_open'] = mins_since_open.clip(lower=0)
        
        # Minutes until close (15:30)
        mins_until_close = (15 - df['hour']) * 60 + (30 - df['minute'])
        df['mins_until_close'] = mins_until_close.clip(lower=0)

        return df
