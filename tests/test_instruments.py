import pytest
import pandas as pd
from app.market.instruments import InstrumentManager

@pytest.fixture
def mock_instruments():
    return [
        {
            "token": "99926000",
            "symbol": "Nifty 50",
            "name": "NIFTY",
            "expiry": "",
            "strike": "-1.000000",
            "lotsize": "1",
            "instrumenttype": "AMXIDX",
            "exch_seg": "NSE",
            "tick_size": "5.000000"
        },
        {
            "token": "35001",
            "symbol": "NIFTY28SEP2320000CE",
            "name": "NIFTY",
            "expiry": "28SEP2023",
            "strike": "2000000.000000",
            "lotsize": "50",
            "instrumenttype": "OPTIDX",
            "exch_seg": "NFO",
            "tick_size": "5.000000"
        },
        {
            "token": "35002",
            "symbol": "NIFTY28SEP2320000PE",
            "name": "NIFTY",
            "expiry": "28SEP2023",
            "strike": "2000000.000000",
            "lotsize": "50",
            "instrumenttype": "OPTIDX",
            "exch_seg": "NFO",
            "tick_size": "5.000000"
        },
        {
            "token": "12345",
            "symbol": "RELIANCE",
            "name": "RELIANCE",
            "expiry": "",
            "strike": "-1.000000",
            "lotsize": "1",
            "instrumenttype": "EQ",
            "exch_seg": "NSE",
            "tick_size": "5.000000"
        }
    ]

def test_get_nifty_spot(mock_instruments):
    manager = InstrumentManager(mock_instruments)
    spot = manager.get_nifty_spot()
    assert spot is not None
    assert spot['symbol'] == 'Nifty 50'
    assert spot['token'] == '99926000'

def test_get_nifty_options(mock_instruments):
    manager = InstrumentManager(mock_instruments)
    opts = manager.get_nifty_options()
    assert not opts.empty
    assert len(opts) == 2
    assert all(opts['name'] == 'NIFTY')
    assert all(opts['exch_seg'] == 'NFO')

def test_strike_conversion(mock_instruments):
    manager = InstrumentManager(mock_instruments)
    opts = manager.get_nifty_options()
    # 2000000.000000 / 100 = 20000.0
    assert opts.iloc[0]['strike'] == 20000.0
