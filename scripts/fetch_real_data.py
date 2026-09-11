import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.broker.angel_one import AngelOneBroker

def fetch_last_30_days():
    broker = AngelOneBroker()
    if not broker.login():
        logger.error("Failed to login to Angel One.")
        return
        
    from app.market.instruments import InstrumentManager
    
    raw_instruments = broker.get_instrument_master()
    if not raw_instruments:
        logger.error("Failed to load instrument master.")
        return
        
    im = InstrumentManager(raw_instruments)
    nifty_spot = im.get_nifty_spot()
    if not nifty_spot:
        logger.error("NIFTY Spot not found in instrument master.")
        return
        
    # NIFTY Spot Token
    symbol_token = nifty_spot['token']
    exchange = "NSE"
    logger.info(f"Using NIFTY Spot Token: {symbol_token}")
    
    end_date = datetime.now()
    # We want 30 days of data. We'll fetch in 5-day chunks to avoid API limits.
    start_date = end_date - timedelta(days=30)
    
    all_data = []
    
    current_start = start_date
    while current_start < end_date:
        current_end = current_start + timedelta(days=5)
        if current_end > end_date:
            current_end = end_date
            
        from_str = current_start.strftime('%Y-%m-%d 09:15')
        to_str = current_end.strftime('%Y-%m-%d 15:30')
        
        historicParam = {
            "exchange": exchange,
            "symboltoken": symbol_token,
            "interval": "ONE_MINUTE",
            "fromdate": from_str, 
            "todate": to_str
        }
        
        logger.info(f"Fetching data from {from_str} to {to_str}...")
        try:
            res = broker.smart_api.getCandleData(historicParam)
            if res and res.get('status') and res.get('data'):
                # Data format: [timestamp, open, high, low, close, volume]
                for row in res['data']:
                    # Angel One timestamp format: '2021-02-08T09:00:00+05:30'
                    all_data.append({
                        'timestamp': row[0],
                        'open': float(row[1]),
                        'high': float(row[2]),
                        'low': float(row[3]),
                        'close': float(row[4]),
                        'volume': float(row[5]),
                        'symbol': 'NIFTY',
                        'token': symbol_token,
                        'exchange': exchange
                    })
            else:
                logger.warning(f"No data or error returned: {res}")
        except Exception as e:
            logger.error(f"Error fetching chunk: {e}")
            
        current_start = current_end + timedelta(minutes=1) # Advance to avoid overlap
        import time
        time.sleep(0.5) # Rate limit protection
        
    if not all_data:
        logger.error("No data fetched at all.")
        return
        
    df = pd.DataFrame(all_data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    
    logger.info(f"Successfully fetched {len(df)} rows.")
    
    os.makedirs("data", exist_ok=True)
    out_path = "data/real_nifty_30d.csv"
    df.to_csv(out_path, index=False)
    logger.success(f"Saved real data to {out_path}")

if __name__ == "__main__":
    fetch_last_30_days()
