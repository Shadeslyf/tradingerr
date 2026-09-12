import pandas as pd
from loguru import logger

from app.features.price_features import PriceFeatures
from app.features.market_structure import MarketStructureFeatures
from app.features.time_features import TimeFeatures
from app.features.options_features import OptionsFeatures
from app.features.cross_asset import CrossAssetFeatures
from app.features.professional_features import ProfessionalFeatures


class FeaturePipeline:
    @staticmethod
    def generate_features(spot_ohlcv: pd.DataFrame, options_ohlcv: pd.DataFrame = None) -> pd.DataFrame:
        """
        Takes raw spot OHLCV and optional options OHLCV and returns a rich feature DataFrame.

        Feature groups:
          1. Core Price:   VWAP, EMAs, RSI, ATR, Momentum (ROC)
          2. NEW — RSI Divergence:  rsi_slope, rsi_divergence, overbought/oversold flags
          3. NEW — VWAP Bands:      1σ/2σ channels, band position, breakout flag
          4. NEW — Volume Features: vol_ratio, vol_spike, vol_spike_dir, vol_delta
          5. NEW — Bollinger Bands: bb_width, bb_pos, bb_squeeze
          6. Market Structure:      intraday highs/lows, opening range, gap
          7. Time:                  hour, minute, day_of_week, session timing
          8. Cross-Asset (V2):      VIX slope/spike, Bank Nifty relative strength & divergence
          9. Options (optional):    PCR if options data provided
        """
        if spot_ohlcv.empty:
            return spot_ohlcv

        df = spot_ohlcv.copy()

        # Ensure timestamp is datetime and set as index
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)

        # ── 1. Core Price Features ──────────────────────────────────────────
        logger.info("Calculating Price Features...")
        df = PriceFeatures.calculate_vwap(df)
        df = PriceFeatures.calculate_emas(df, periods=[9, 21, 50])
        df = PriceFeatures.calculate_rsi(df, period=14)
        df = PriceFeatures.calculate_atr(df, period=14)
        df = PriceFeatures.calculate_momentum(df, periods=[5, 15])

        # ── 2. RSI Divergence (NEW) ─────────────────────────────────────────
        logger.info("Calculating RSI Divergence Features...")
        df = PriceFeatures.calculate_rsi_divergence(df, lookback=20)

        # ── 3. VWAP Bands (NEW) ────────────────────────────────────────────
        logger.info("Calculating VWAP Band Features...")
        df = PriceFeatures.calculate_vwap_bands(df, period=20, multipliers=(1.0, 2.0))

        # ── 4. Volume Spike Features (NEW) ─────────────────────────────────
        logger.info("Calculating Volume Spike Features...")
        df = PriceFeatures.calculate_volume_features(df, spike_window=20, spike_mult=2.0)

        # ── 5. Bollinger Bands (NEW) ───────────────────────────────────────
        logger.info("Calculating Bollinger Band Features...")
        df = PriceFeatures.calculate_bollinger_bands(df, period=20, std_mult=2.0)

        # ── 5.5 Cross Asset (V2) ───────────────────────────────────────────
        logger.info("Calculating Cross-Asset Features...")
        df = CrossAssetFeatures.calculate_cross_asset_features(df, lookback=15)

        # ── 6. Market Structure ────────────────────────────────────────────
        logger.info("Calculating Market Structure Features...")
        df = MarketStructureFeatures.calculate_intraday_structure(df)
        df = MarketStructureFeatures.calculate_daily_structure(df)

        # ── 6.5 Professional Trading Features (V3) ─────────────────────────
        logger.info("Calculating Professional Features (ADX, MACD, Keltner, OBV)...")
        df = ProfessionalFeatures.calculate_adx(df, period=14)
        df = ProfessionalFeatures.calculate_macd(df)
        df = ProfessionalFeatures.calculate_obv(df)
        df = ProfessionalFeatures.calculate_keltner_channels(df)

        # ── 7. Time Features ───────────────────────────────────────────────
        logger.info("Calculating Time Features...")
        df = TimeFeatures.calculate_time_features(df)

        # ── 8. Options (optional) ──────────────────────────────────────────
        if options_ohlcv is not None and not options_ohlcv.empty:
            logger.info("Calculating Options Features...")
            df = OptionsFeatures.calculate_pcr(options_ohlcv, df)

        # Drop rows with NaNs caused by rolling windows
        initial_len = len(df)
        df.dropna(inplace=True)
        logger.info(
            f"Feature pipeline complete. {len(df.columns)} features | "
            f"Dropped {initial_len - len(df)} rows due to rolling window warm-up."
        )

        return df
