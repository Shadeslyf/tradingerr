import sys
import os
from tabulate import tabulate
from loguru import logger

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.settings import settings
from app.monitoring.logging import setup_logging
from app.broker.angel_one import AngelOneBroker
from app.market.instruments import InstrumentManager

def main():
    setup_logging()
    logger.info("Starting AI-Based Indian Options Trading System - Phase 1 & 2")

    broker = AngelOneBroker()
    
    # In a real scenario, you'd want to login.
    # For Phase 1 & 2, if dummy credentials are provided, login will gracefully fail
    # but we can still fetch the instrument master (which is an open URL).
    broker.login()

    raw_instruments = broker.get_instrument_master()
    if not raw_instruments:
        logger.error("Failed to retrieve instrument master.")
        return

    manager = InstrumentManager(raw_instruments)

    nifty_spot = manager.get_nifty_spot()
    if nifty_spot:
        logger.info(f"Found NIFTY Spot: Symbol: {nifty_spot['symbol']}, Token: {nifty_spot['token']}")
    else:
        logger.warning("NIFTY Spot not found.")

    nifty_opts_df = manager.get_current_nifty_options()
    if nifty_opts_df.empty:
        logger.warning("No NIFTY Options found.")
        return

    logger.info(f"Found {len(nifty_opts_df)} NIFTY option contracts.")

    # Select a small sample to print cleanly, e.g., closest expiry, a few strikes
    if 'expiry_dt' in nifty_opts_df.columns:
        closest_expiry = nifty_opts_df['expiry_dt'].min()
        sample_opts = nifty_opts_df[nifty_opts_df['expiry_dt'] == closest_expiry]
        
        # Take a subset around a plausible ATM (e.g., 20000, or just median strike if unknown)
        median_strike = sample_opts['strike'].median()
        # Grab a few strikes around median
        sample_opts = sample_opts[(sample_opts['strike'] >= median_strike - 200) & (sample_opts['strike'] <= median_strike + 200)]
    else:
        sample_opts = nifty_opts_df.head(20)

    # Required columns: Underlying, Expiry, Strike, CE/PE, Symbol, Token, Lot Size
    # In Angel One: 'name' is underlying, 'expiry', 'strike', 'symbol' contains CE/PE, 'symbol', 'token', 'lotsize'
    
    def get_option_type(symbol: str) -> str:
        if symbol.endswith('CE'):
            return 'CE'
        elif symbol.endswith('PE'):
            return 'PE'
        return 'UNKNOWN'

    sample_opts['CE/PE'] = sample_opts['symbol'].apply(get_option_type)
    
    display_df = sample_opts[['name', 'expiry', 'strike', 'CE/PE', 'symbol', 'token', 'lotsize']]
    display_df.columns = ['Underlying', 'Expiry', 'Strike', 'CE/PE', 'Symbol', 'Token', 'Lot Size']

    print("\n--- Sample NIFTY Option Contracts ---")
    print(tabulate(display_df, headers='keys', tablefmt='psql', showindex=False))

if __name__ == "__main__":
    main()
