import pandas as pd
from loguru import logger

from app.features.price_features import PriceFeatures
from app.features.market_structure import MarketStructureFeatures
from app.features.time_features import TimeFeatures
from app.features.options_features import OptionsFeatures

class FeaturePipeline:
    @staticmethod
    def generate_features(spot_ohlcv: pd.DataFrame, options_ohlcv: pd.DataFrame = None) -> pd.DataFrame:
        """
        Takes raw spot OHLCV and optional options OHLCV (to compute PCR etc.)
        and returns a rich feature DataFrame.
        """
        if spot_ohlcv.empty:
            return spot_ohlcv

        df = spot_ohlcv.copy()
        # Ensure timestamp is datetime and set as index
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)

        logger.info("Calculating Price Features...")
        df = PriceFeatures.calculate_vwap(df)
        df = PriceFeatures.calculate_emas(df, periods=[9, 21, 50])
        df = PriceFeatures.calculate_rsi(df, period=14)
        df = PriceFeatures.calculate_atr(df, period=14)
        df = PriceFeatures.calculate_momentum(df, periods=[5, 15])

        logger.info("Calculating Market Structure Features...")
        df = MarketStructureFeatures.calculate_intraday_structure(df)
        df = MarketStructureFeatures.calculate_daily_structure(df)

        logger.info("Calculating Time Features...")
        df = TimeFeatures.calculate_time_features(df)

        if options_ohlcv is not None and not options_ohlcv.empty:
            logger.info("Calculating Options Features...")
            # options_ohlcv must have 'timestamp', 'option_type', 'open_interest', 'volume'
            df = OptionsFeatures.calculate_pcr(options_ohlcv, df)

        # Drop rows with NaNs caused by rolling windows
        initial_len = len(df)
        df.dropna(inplace=True)
        logger.info(f"Feature pipeline complete. Dropped {initial_len - len(df)} rows due to rolling window warm-up.")

        return df
