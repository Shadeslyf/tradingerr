import pytest
from datetime import datetime
from app.data.normalization.resampler import DataResampler

def test_resample_to_ohlcv():
    raw_ticks = [
        # Token A
        {'token': 'A', 'symbol': 'NIFTY_A', 'timestamp': '2026-09-11 10:00:05', 'ltp': 100, 'volume': 10, 'open_interest': 100},
        {'token': 'A', 'symbol': 'NIFTY_A', 'timestamp': '2026-09-11 10:00:30', 'ltp': 105, 'volume': 20, 'open_interest': 110},
        {'token': 'A', 'symbol': 'NIFTY_A', 'timestamp': '2026-09-11 10:00:55', 'ltp': 95, 'volume': 15, 'open_interest': 120},
        
        # Token B
        {'token': 'B', 'symbol': 'NIFTY_B', 'timestamp': '2026-09-11 10:00:10', 'ltp': 50, 'volume': 5, 'open_interest': 50},
    ]

    candles = DataResampler.resample_to_ohlcv(raw_ticks, timeframe='1min')

    assert len(candles) == 2
    
    # Find Token A candle
    candle_a = next(c for c in candles if c['symbol'] == 'NIFTY_A')
    assert candle_a['open'] == 100
    assert candle_a['high'] == 105
    assert candle_a['low'] == 95
    assert candle_a['close'] == 95
    assert candle_a['volume'] == 45
    assert candle_a['open_interest'] == 120
    assert candle_a['timestamp'] == datetime(2026, 9, 11, 10, 0, 0)

    # Find Token B candle
    candle_b = next(c for c in candles if c['symbol'] == 'NIFTY_B')
    assert candle_b['open'] == 50
    assert candle_b['volume'] == 5
