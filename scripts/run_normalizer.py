import sys
import os
import time
from datetime import datetime, timedelta
from loguru import logger

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.monitoring.logging import setup_logging
from app.database.models import SessionLocal
from app.database.repositories import MarketDataRepository, OHLCVRepository
from app.data.normalization.validator import DataValidator
from app.data.normalization.resampler import DataResampler

def main():
    setup_logging()
    logger.info("Starting Normalization Task")

    session = SessionLocal()
    tick_repo = MarketDataRepository(session)
    ohlcv_repo = OHLCVRepository(session)

    # Process ticks from the last X minutes
    # In a real setup, we might keep track of the last processed timestamp
    # For now, we just process all ticks that are older than 1 minute (to ensure full minute candle)
    # and maybe delete them or flag them as processed.
    
    # We will fetch all ticks, resample them, save OHLCV, and delete those ticks.
    
    while True:
        try:
            logger.info("Checking for unprocessed ticks...")
            # We want to safely process candles that are "closed". 
            # A 1-minute candle is closed if the current time is > the end of that minute.
            current_time = datetime.now()
            # Process ticks up to 1 minute ago to ensure full minutes are formed
            cutoff_time = current_time - timedelta(minutes=1)

            # Get all ticks
            ticks = tick_repo.get_all_ticks()
            
            # Filter ticks older than cutoff
            ticks_to_process = [t for t in ticks if t.timestamp < cutoff_time]

            if not ticks_to_process:
                logger.info("No closed ticks to process. Sleeping for 30s.")
                time.sleep(30)
                continue

            # Convert to dict for validator/resampler
            raw_data = []
            for t in ticks_to_process:
                raw_data.append({
                    'timestamp': t.timestamp,
                    'symbol': t.symbol,
                    'token': t.token,
                    'exchange': t.exchange,
                    'ltp': t.ltp,
                    'volume': t.volume,
                    'open_interest': t.open_interest,
                    'bid': t.bid,
                    'ask': t.ask
                })

            # 1. Validation
            valid_data = DataValidator.validate_ticks(raw_data)

            # 2. Resampling
            ohlcv_data = DataResampler.resample_to_ohlcv(valid_data, timeframe='1min')

            # 3. Save to DB
            if ohlcv_data:
                ohlcv_repo.save_ohlcv_bulk(ohlcv_data)
                logger.info(f"Saved {len(ohlcv_data)} OHLCV candles to DB.")

            # 4. Clean up processed ticks
            tick_repo.delete_ticks_before(cutoff_time)
            logger.info(f"Deleted processed ticks older than {cutoff_time}.")

            logger.info("Batch complete. Sleeping for 30s.")
            time.sleep(30)

        except KeyboardInterrupt:
            logger.info("Normalizer stopped.")
            break
        except Exception as e:
            logger.error(f"Error in normalizer loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
