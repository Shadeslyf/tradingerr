import pandas as pd
from typing import List, Dict, Any, Optional
from loguru import logger
from datetime import datetime
import os

class InstrumentManager:
    def __init__(self, raw_instruments: List[Dict[str, Any]]):
        self.raw_instruments = raw_instruments
        self.df = pd.DataFrame(raw_instruments)
        self._preprocess()

    def _preprocess(self):
        logger.info("Preprocessing instrument data...")
        if self.df.empty:
            logger.warning("Instrument DataFrame is empty.")
            return

        # Filter for NSE and NFO
        self.df = self.df[self.df['exch_seg'].isin(['NSE', 'NFO'])]
        
        # Convert strike from string to float (strike is usually string ending with 0000)
        self.df['strike'] = pd.to_numeric(self.df['strike'], errors='coerce')
        if not self.df['strike'].isna().all():
            self.df['strike'] = self.df['strike'] / 100.0  # Angel uses strike * 100 in string

    def get_nifty_spot(self) -> Optional[Dict[str, Any]]:
        # NIFTY spot on NSE
        nifty_spot = self.df[(self.df['name'] == 'NIFTY') & (self.df['symbol'] == 'Nifty 50') & (self.df['exch_seg'] == 'NSE') & (self.df['instrumenttype'] == 'AMXIDX')]
        if not nifty_spot.empty:
            return nifty_spot.iloc[0].to_dict()
        return None

    def get_nifty_options(self) -> pd.DataFrame:
        # NIFTY options on NFO
        nifty_opts = self.df[(self.df['name'] == 'NIFTY') & (self.df['instrumenttype'] == 'OPTIDX') & (self.df['exch_seg'] == 'NFO')]
        return nifty_opts

    def get_current_nifty_options(self) -> pd.DataFrame:
        opts = self.get_nifty_options()
        if opts.empty:
            return opts
        
        # Filter out expired contracts if we wanted to, but the master usually has active ones
        # We can sort by expiry and strike
        
        # Optional: Convert expiry to datetime
        opts['expiry_dt'] = pd.to_datetime(opts['expiry'], format='%d%b%Y', errors='coerce')
        
        # Sort
        opts = opts.sort_values(by=['expiry_dt', 'strike'])
        return opts
