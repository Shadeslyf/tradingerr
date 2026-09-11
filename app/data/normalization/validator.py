from typing import List, Dict, Any
from datetime import datetime
from loguru import logger
import pandas as pd

class DataValidator:
    """
    Validates raw market ticks.
    """
    @staticmethod
    def validate_ticks(ticks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        valid_ticks = []
        seen = set()

        for tick in ticks:
            # 1. Negative Prices or Zero LTP
            if tick.get('ltp', 0) <= 0:
                logger.warning(f"Invalid LTP {tick.get('ltp')} for token {tick.get('token')}. Dropping.")
                continue

            # 2. Negative Volume or OI
            if tick.get('volume', 0) < 0 or tick.get('open_interest', 0) < 0:
                logger.warning(f"Negative volume/OI for token {tick.get('token')}. Dropping.")
                continue

            # 3. Missing Timestamp
            if not tick.get('timestamp'):
                logger.warning(f"Missing timestamp for token {tick.get('token')}. Dropping.")
                continue

            # 4. Duplicate Tick Detection
            # We identify a duplicate by token, timestamp, and ltp.
            # In a highly liquid market, multiple trades can happen in same ms, but identical tick info is often duplicate broadcast.
            sig = (tick['token'], tick['timestamp'], tick['ltp'], tick['volume'])
            if sig in seen:
                continue
            seen.add(sig)

            valid_ticks.append(tick)

        logger.info(f"Validation complete: Kept {len(valid_ticks)} out of {len(ticks)} ticks.")
        return valid_ticks
