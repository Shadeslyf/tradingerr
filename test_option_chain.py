import pyotp
import pandas as pd
from datetime import datetime
from SmartApi import SmartConnect
from app.config.settings import settings
from app.broker.angel_one import AngelOneBroker
from app.market.instruments import InstrumentManager

broker = AngelOneBroker()
broker.login()
raw = broker.get_instrument_master()
im = InstrumentManager(raw)

nifty_price = 23398.1
atm = round(nifty_price / 50) * 50
strikes = [atm + (i * 50) for i in range(-5, 6)]

opts = im.get_current_nifty_options()
# get nearest expiry
opts = opts[opts['expiry_dt'] >= datetime.now()]
if not opts.empty:
    nearest = opts.iloc[0]['expiry_dt']
    opts = opts[(opts['expiry_dt'] == nearest) & (opts['strike'].isin(strikes))]
    
    tokens = opts['token'].tolist()
    print(f"Found {len(tokens)} tokens for expiry {nearest}")
    md = broker.smart_api.getMarketData("LTP", {"NFO": tokens})
    print(md)
