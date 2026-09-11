import pytest
from app.data.normalization.validator import DataValidator

def test_validate_ticks():
    raw_ticks = [
        # Valid tick
        {'token': '1', 'timestamp': '2026-09-11 10:00:00', 'ltp': 100, 'volume': 10, 'open_interest': 5},
        # Negative LTP
        {'token': '2', 'timestamp': '2026-09-11 10:00:01', 'ltp': -10, 'volume': 10, 'open_interest': 5},
        # Zero LTP
        {'token': '3', 'timestamp': '2026-09-11 10:00:02', 'ltp': 0, 'volume': 10, 'open_interest': 5},
        # Negative Volume
        {'token': '4', 'timestamp': '2026-09-11 10:00:03', 'ltp': 100, 'volume': -5, 'open_interest': 5},
        # Missing Timestamp
        {'token': '5', 'ltp': 100, 'volume': 10, 'open_interest': 5},
        # Exact Duplicate
        {'token': '1', 'timestamp': '2026-09-11 10:00:00', 'ltp': 100, 'volume': 10, 'open_interest': 5},
    ]

    valid_ticks = DataValidator.validate_ticks(raw_ticks)
    
    # Only the first tick should be kept
    assert len(valid_ticks) == 1
    assert valid_ticks[0]['token'] == '1'
