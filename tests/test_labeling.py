import pytest
import pandas as pd
import numpy as np
from app.ml.labeling import TripleBarrierLabeler

def test_bullish_label():
    # Price goes up 10% within 5 periods
    df = pd.DataFrame({
        'close': [100, 102, 105, 110, 115, 120]
    })
    
    labeled = TripleBarrierLabeler.apply_triple_barrier(df, horizon=5, upper_barrier_pct=5.0, lower_barrier_pct=5.0)
    # The first row (100) hits upper barrier (105) at index 2.
    assert labeled['label'].iloc[0] == 1

def test_bearish_label():
    # Price goes down 10% within 5 periods
    df = pd.DataFrame({
        'close': [100, 98, 95, 90, 85, 80]
    })
    
    labeled = TripleBarrierLabeler.apply_triple_barrier(df, horizon=5, upper_barrier_pct=5.0, lower_barrier_pct=5.0)
    # The first row (100) hits lower barrier (95) at index 2.
    assert labeled['label'].iloc[0] == 2

def test_range_bound_label():
    # Price stays flat
    df = pd.DataFrame({
        'close': [100, 101, 99, 101, 99, 100, 100, 100, 100, 100]
    })
    
    labeled = TripleBarrierLabeler.apply_triple_barrier(df, horizon=5, upper_barrier_pct=5.0, lower_barrier_pct=5.0)
    # First row hits neither 105 nor 95 within horizon
    assert labeled['label'].iloc[0] == 0

def test_horizon_cutoff():
    df = pd.DataFrame({
        'close': [100, 100, 100, 100]
    })
    labeled = TripleBarrierLabeler.apply_triple_barrier(df, horizon=5, upper_barrier_pct=1.0, lower_barrier_pct=1.0)
    
    # Because n <= horizon, all labels should be NaN as per the logic to drop incomplete horizons
    assert pd.isna(labeled['label'].iloc[0])
