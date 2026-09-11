import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.features.feature_pipeline import FeaturePipeline

def explore_features():
    print("Generating synthetic market data for 3 hours (180 minutes)...")
    
    # 1. Generate 3 hours of dummy NIFTY data (9:15 to 12:15)
    dates = [datetime(2026, 9, 11, 9, 15) + timedelta(minutes=i) for i in range(180)]
    
    spot_df = pd.DataFrame({
        'timestamp': dates,
        'open': np.linspace(23400, 23550, 180),
        'high': np.linspace(23420, 23580, 180),
        'low': np.linspace(23380, 23520, 180),
        'close': np.linspace(23410, 23560, 180),
        'volume': np.random.randint(50000, 200000, 180)
    })

    # 2. Generate dummy Options data
    ce_df = pd.DataFrame({
        'timestamp': dates,
        'option_type': 'CE',
        'open_interest': np.linspace(1000000, 1200000, 180),
        'volume': np.random.randint(10000, 50000, 180)
    })
    
    pe_df = pd.DataFrame({
        'timestamp': dates,
        'option_type': 'PE',
        'open_interest': np.linspace(800000, 1500000, 180),
        'volume': np.random.randint(10000, 70000, 180)
    })
    options_df = pd.concat([ce_df, pe_df])

    # 3. Run Pipeline
    print("Running data through Feature Pipeline...")
    features_df = FeaturePipeline.generate_features(spot_df, options_df)
    
    print("\n--- Pipeline Output Summary ---")
    print(f"Total Rows generated (after warm-up drop): {len(features_df)}")
    print(f"Total Features calculated: {len(features_df.columns)}")
    
    print("\n--- Snapshot of Calculated Features (Last Row) ---")
    last_row = features_df.iloc[-1]
    
    # Organize features into groups for display
    groups = {
        "Price & Trend": ['close', 'VWAP', 'EMA_9', 'EMA_21', 'EMA_50'],
        "Momentum & Volatility": ['RSI', 'ATR', 'ROC_5', 'VOL_MOM_5'],
        "Market Structure": ['or_high', 'or_low', 'dist_vwap_pct', 'dist_day_high_pct'],
        "Options Data": ['Total_Call_OI', 'Total_Put_OI', 'PCR_OI', 'PCR_VOL'],
        "Time Data": ['mins_since_open', 'mins_until_close']
    }
    
    for group_name, cols in groups.items():
        print(f"\n[{group_name}]")
        for col in cols:
            if col in last_row:
                val = last_row[col]
                # Format floats
                if isinstance(val, float):
                    print(f"  {col:<20} : {val:.2f}")
                else:
                    print(f"  {col:<20} : {val}")

if __name__ == "__main__":
    explore_features()
