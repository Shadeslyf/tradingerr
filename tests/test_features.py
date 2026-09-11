import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.features.feature_pipeline import FeaturePipeline

@pytest.fixture
def sample_spot_ohlcv():
    dates = [datetime(2026, 9, 11, 9, 15) + timedelta(minutes=i) for i in range(100)]
    df = pd.DataFrame({
        'timestamp': dates,
        'open': np.linspace(100, 200, 100),
        'high': np.linspace(105, 205, 100),
        'low': np.linspace(95, 195, 100),
        'close': np.linspace(102, 202, 100),
        'volume': np.random.randint(100, 1000, 100)
    })
    return df

@pytest.fixture
def sample_options_ohlcv():
    dates = [datetime(2026, 9, 11, 9, 15) + timedelta(minutes=i) for i in range(100)]
    
    # Create CE options
    ce_df = pd.DataFrame({
        'timestamp': dates,
        'option_type': 'CE',
        'open_interest': np.linspace(1000, 2000, 100),
        'volume': np.random.randint(50, 500, 100)
    })
    
    # Create PE options
    pe_df = pd.DataFrame({
        'timestamp': dates,
        'option_type': 'PE',
        'open_interest': np.linspace(500, 1500, 100),
        'volume': np.random.randint(50, 500, 100)
    })
    
    return pd.concat([ce_df, pe_df])

def test_feature_pipeline(sample_spot_ohlcv, sample_options_ohlcv):
    features_df = FeaturePipeline.generate_features(sample_spot_ohlcv, sample_options_ohlcv)
    
    # Test that dataframe is returned
    assert not features_df.empty
    
    # Check that rows were dropped due to warm-up (EMA_50 requires 50 periods)
    assert len(features_df) < len(sample_spot_ohlcv)
    
    # Check for expected columns
    expected_cols = [
        'EMA_9', 'EMA_21', 'EMA_50', 'RSI', 'ATR', 'VWAP', 'ROC_5', 'VOL_MOM_5',
        'day_high', 'day_low', 'or_high', 'or_low', 'dist_vwap_pct', 
        'mins_since_open', 'mins_until_close',
        'PCR_OI', 'Total_Call_OI', 'Total_Put_OI'
    ]
    
    for col in expected_cols:
        assert col in features_df.columns, f"Missing column: {col}"
    
    # Test PCR calculation logic (PE / CE)
    # At the end of the sample, PE is around 1500, CE is around 2000. PCR should be ~0.75
    last_pcr = features_df['PCR_OI'].iloc[-1]
    assert 0.7 < last_pcr < 0.8
