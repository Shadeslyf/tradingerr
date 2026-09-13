"""
ML Backtest Simulation Script
Runs the walk-forward best model over:
  - Jan 2026 → Apr 2026 (from Nifty50_2Years_1Min.csv)  → starting capital ₹1,00,000
  - Aug-Sep 11 2026     (from real_nifty_30d.csv)        → live model inference

Trading logic (simple, clear):
    BULLISH (0) → BUY  1 lot of NIFTY (treat as 50 units × price)
    RANGE   (1) → HOLD / skip
    BEARISH (2) → SHORT 1 lot of NIFTY

Position management:
    - Each trade held for HOLD_BARS (default 60 bars = 1 hour)
    - Only 1 position at a time
    - Stop-loss: -0.3%  |  Target: +0.5%

Outputs results to:
    data/backtest_results/backtest_jan_apr_2026.json
    data/backtest_results/backtest_30d_live.json
"""

import os
import sys
import json
import joblib
import warnings
import numpy as np
import pandas as pd
from datetime import datetime
from loguru import logger

warnings.filterwarnings("ignore")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.features.feature_pipeline import FeaturePipeline
from app.ml.labeling import RegimeLabeler
from app.risk.position_sizing import PositionSizer

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
MODEL_PATH       = "models/walk_forward_v4/best_model.joblib"
RAW_2Y_CSV       = "data/Nifty50_CrossAsset_Merged.csv"
REAL_30D_CSV     = "data/real_nifty_30d.csv"
OUT_JSON_MAIN    = "data/backtest_results/backtest_jan_apr_2026_v4.json"
OUT_JSON_LIVE    = "data/backtest_results/backtest_30d_live_v4.json"
RESULTS_DIR      = "data/backtest_results"

INITIAL_CAPITAL  = 100_000.0   # ₹1,00,000
LOT_SIZE         = 50          # 1 NIFTY lot = 50 units
HOLD_BARS        = 60          # hold position for 60 mins
STOP_LOSS_PCT    = 0.30        # 0.3% stop-loss
TARGET_PCT       = 0.50        # 0.5% take-profit
CONFIDENCE_MIN   = 0.45        # minimum model confidence to enter trade

LABEL_HORIZON    = 60
THRESHOLD_PCT    = 0.1

REGIME_MAP = {0: "BULLISH", 1: "RANGE", 2: "BEARISH"}


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def load_and_clean(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df.columns = [c.strip().lower() for c in df.columns]
    ts_col = next((c for c in df.columns if c in ("time","date","datetime","timestamp")), df.columns[0])
    df.rename(columns={ts_col: "timestamp"}, inplace=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=False)
    if df["timestamp"].dt.tz is not None:
        df["timestamp"] = df["timestamp"].dt.tz_localize(None)
    df.sort_values("timestamp", inplace=True)
    df.reset_index(drop=True, inplace=True)
    for col in ("open","high","low","close"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if "volume" not in df.columns:
        df["volume"] = 0
    # Market hours filter
    h, m = df["timestamp"].dt.hour, df["timestamp"].dt.minute
    df = df[((h > 9) | ((h == 9) & (m >= 15))) & ((h < 15) | ((h == 15) & (m <= 30)))]
    return df.reset_index(drop=True)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    feats = FeaturePipeline.generate_features(df.copy(), options_ohlcv=None)
    if feats.empty:
        return feats
    labeled = RegimeLabeler.apply_3class_regime_labeling(feats, horizon=LABEL_HORIZON, threshold_pct=THRESHOLD_PCT)
    return labeled.dropna(subset=["label"])


def run_backtest(df_feat: pd.DataFrame, model, initial_capital: float, label: str) -> dict:
    """
    Vectorised backtest using model predictions.
    Returns a dict with trades, equity curve and summary stats.
    """
    drop_cols = [c for c in ("label","timestamp","symbol","token","exchange") if c in df_feat.columns]
    X = df_feat.drop(columns=drop_cols, errors="ignore")
    
    # Align features to what model was trained on
    model_features = model.get_booster().feature_names
    # Keep only known features, fill missing with 0
    X = X.reindex(columns=model_features, fill_value=0.0)

    proba = model.predict_proba(X)                    # shape (N, 3)
    signals = np.argmax(proba, axis=1)                # 0=BULL 1=RANGE 2=BEAR
    confidence = np.max(proba, axis=1)

    closes = df_feat["close"].values
    timestamps = df_feat.index if isinstance(df_feat.index, pd.DatetimeIndex) else pd.to_datetime(df_feat["timestamp"] if "timestamp" in df_feat.columns else df_feat.index)

    capital   = initial_capital
    equity    = [capital]
    eq_times  = [str(timestamps[0])]
    trades    = []
    i         = 0
    n         = len(closes)

    while i < n - HOLD_BARS:
        sig  = signals[i]
        conf = confidence[i]
        adx_val = df_feat.iloc[i]["adx_14"] if "adx_14" in df_feat.columns else 25.0

        if sig == 1 or conf < CONFIDENCE_MIN or adx_val < 20.0:   # RANGE, low confidence or low ADX → skip
            i += 1
            equity.append(capital)
            eq_times.append(str(timestamps[i]))
            continue

        entry_price = closes[i]
        direction   = "LONG" if sig == 0 else "SHORT"
        tp_price    = entry_price * (1 + TARGET_PCT/100)    if direction=="LONG" else entry_price * (1 - TARGET_PCT/100)

        exit_price  = closes[i + HOLD_BARS]
        exit_reason = "HOLD_EXPIRY"
        exit_bar    = i + HOLD_BARS

        # V4 ATR Trailing Stop Logic (Chandelier Exit) + Breakeven Stops
        ATR_MULT = 2.5
        entry_atr = df_feat.iloc[i]["atr_14"] if "atr_14" in df_feat.columns else (entry_price * 0.002)
        highest_high = entry_price
        lowest_low = entry_price
        breakeven_activated = False

        # Calculate dynamic position size based on Fixed Fractional (1% risk)
        ev_data = {
            'max_loss': (entry_atr * ATR_MULT) * LOT_SIZE,
            'max_profit': entry_price * (TARGET_PCT/100) * LOT_SIZE,
            'prob_win': float(conf),
            'prob_loss': 1 - float(conf)
        }
        quantity = PositionSizer.calculate_fixed_fractional(capital, ev_data, risk_pct=1.0, lot_size=LOT_SIZE)
        if quantity == 0:
            quantity = LOT_SIZE # Default to 1 lot

        # Check stop / target hit within hold window
        for j in range(i+1, min(i+HOLD_BARS+1, n)):
            bar_low  = df_feat.iloc[j]["low"]  if "low"  in df_feat.columns else closes[j]
            bar_high = df_feat.iloc[j]["high"] if "high" in df_feat.columns else closes[j]
            bar_atr  = df_feat.iloc[j]["atr_14"] if "atr_14" in df_feat.columns else entry_atr
            
            if direction == "LONG":
                highest_high = max(highest_high, bar_high)
                trailing_sl = highest_high - (ATR_MULT * bar_atr)
                
                if not breakeven_activated and (highest_high - entry_price) >= (0.5 * entry_atr):
                    breakeven_activated = True
                    
                if breakeven_activated:
                    trailing_sl = max(trailing_sl, entry_price)
                    
                if bar_low <= trailing_sl:
                    exit_price = trailing_sl; exit_reason = "TRAILING_STOP"; exit_bar = j; break
                if bar_high >= tp_price:
                    exit_price = tp_price; exit_reason = "TARGET_HIT"; exit_bar = j; break
            else:
                lowest_low = min(lowest_low, bar_low)
                trailing_sl = lowest_low + (ATR_MULT * bar_atr)
                
                if not breakeven_activated and (entry_price - lowest_low) >= (0.5 * entry_atr):
                    breakeven_activated = True
                    
                if breakeven_activated:
                    trailing_sl = min(trailing_sl, entry_price)
                    
                if bar_high >= trailing_sl:
                    exit_price = trailing_sl; exit_reason = "TRAILING_STOP"; exit_bar = j; break
                if bar_low <= tp_price:
                    exit_price = tp_price; exit_reason = "TARGET_HIT"; exit_bar = j; break

        if direction == "LONG":
            pnl = (exit_price - entry_price) * quantity
        else:
            pnl = (entry_price - exit_price) * quantity

        capital += pnl
        regime   = REGIME_MAP[sig]

        trades.append({
            "entry_time":   str(timestamps[i]),
            "exit_time":    str(timestamps[exit_bar]),
            "direction":    direction,
            "signal":       regime,
            "confidence":   round(float(conf), 4),
            "entry_price":  round(float(entry_price), 2),
            "exit_price":   round(float(exit_price), 2),
            "quantity":     quantity,
            "pnl_rs":       round(float(pnl), 2),
            "pnl_pct":      round(float(pnl / (entry_price * quantity)) * 100, 4),
            "exit_reason":  exit_reason,
            "capital_after": round(float(capital), 2),
        })

        # Advance to after exit bar
        for k in range(i, exit_bar + 1):
            equity.append(capital)
            if k + 1 < n:
                eq_times.append(str(timestamps[k + 1]))
        i = exit_bar + 1

    # Fill remaining equity
    while len(equity) < n:
        equity.append(capital)
    while len(eq_times) < n:
        eq_times.append(str(timestamps[min(len(eq_times), n-1)]))

    # Compute stats
    pnls = [t["pnl_rs"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    total_return_pct = ((capital - initial_capital) / initial_capital) * 100
    win_rate = (len(wins) / len(pnls) * 100) if pnls else 0
    avg_win  = np.mean(wins)   if wins   else 0
    avg_loss = np.mean(losses) if losses else 0
    profit_factor = abs(sum(wins) / sum(losses)) if losses else float("inf")
    max_dd = _max_drawdown(equity, initial_capital)

    summary = {
        "label":            label,
        "initial_capital":  initial_capital,
        "final_capital":    round(capital, 2),
        "net_pnl":          round(capital - initial_capital, 2),
        "total_return_pct": round(total_return_pct, 2),
        "total_trades":     len(trades),
        "win_trades":       len(wins),
        "loss_trades":      len(losses),
        "win_rate_pct":     round(win_rate, 2),
        "avg_win_rs":       round(avg_win, 2),
        "avg_loss_rs":      round(avg_loss, 2),
        "profit_factor":    round(profit_factor, 3),
        "max_drawdown_pct": round(max_dd, 2),
        "equity_curve":     equity[:n],
        "equity_times":     eq_times[:n],
        "trades":           trades,
    }
    return summary


def _max_drawdown(equity: list, initial: float) -> float:
    peak = initial
    max_dd = 0.0
    for val in equity:
        if val > peak:
            peak = val
        dd = (peak - val) / peak * 100
        if dd > max_dd:
            max_dd = dd
    return max_dd


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    logger.info(f"Loading model from {MODEL_PATH}")
    model = joblib.load(MODEL_PATH)
    logger.info("Model loaded successfully.")

    # ── BACKTEST 1: Apr 2025 → Apr 2026 ─────────────────────
    logger.info("\n=== BACKTEST 1: Apr 2025 → Apr 2026 (₹1,00,000 capital) ===")
    raw_2y = load_and_clean(RAW_2Y_CSV)
    jan_apr = raw_2y[
        (raw_2y["timestamp"] >= "2025-04-23") &
        (raw_2y["timestamp"] <  "2026-04-30")
    ].copy()
    logger.info(f"Slice: {len(jan_apr):,} bars  ({jan_apr['timestamp'].min().date()} → {jan_apr['timestamp'].max().date()})")

    feats_1 = build_features(jan_apr)
    if feats_1.empty:
        logger.error("Feature build returned empty for Apr 2025 - Apr 2026!")
    else:
        result_1 = run_backtest(feats_1, model, INITIAL_CAPITAL, "1-Year Backtest (Apr '25 - Apr '26)")
        out_1 = OUT_JSON_MAIN
        with open(out_1, "w") as f:
            json.dump(result_1, f, indent=2)
        logger.info(f"Result saved: {out_1}")
        logger.info(
            f"  Net P&L: ₹{result_1['net_pnl']:,.2f}  |  Return: {result_1['total_return_pct']}%  |  "
            f"Trades: {result_1['total_trades']}  |  Win Rate: {result_1['win_rate_pct']}%"
        )

    # ── BACKTEST 2: Real 30-day data (Aug-Sep 11 2026) ──────
    logger.info("\n=== BACKTEST 2: Real 30-Day Data (Aug–Sep 2026) ===")
    real_30d = load_and_clean(REAL_30D_CSV)
    logger.info(f"Real data: {len(real_30d):,} bars  ({real_30d['timestamp'].min().date()} → {real_30d['timestamp'].max().date()})")

    feats_2 = build_features(real_30d)
    if feats_2.empty:
        logger.error("Feature build returned empty for 30-day real data!")
    else:
        # For 30-day forward test, start capital from where Jan-Apr ended (or 1L fresh)
        start_cap_2 = result_1["final_capital"] if feats_1 is not None and not feats_1.empty else INITIAL_CAPITAL
        result_2 = run_backtest(feats_2, model, start_cap_2, "Live 30-Day (Aug-Sep 2026)")
        out_2 = OUT_JSON_LIVE
        with open(out_2, "w") as f:
            json.dump(result_2, f, indent=2)
        logger.info(f"Result saved: {out_2}")
        logger.info(
            f"  Net P&L: ₹{result_2['net_pnl']:,.2f}  |  Return: {result_2['total_return_pct']}%  |  "
            f"Trades: {result_2['total_trades']}  |  Win Rate: {result_2['win_rate_pct']}%"
        )

    # ── Combined summary ─────────────────────────────────────
    combined = {
        "backtest_jan_apr_2026_v4": result_1 if not feats_1.empty else {},
        "backtest_30d_live_v4":     result_2 if not feats_2.empty else {},
        "generated_at":          datetime.now().isoformat(),
    }
    
    combined_path = os.path.join(RESULTS_DIR, "combined_results_v4.json")
    with open(combined_path, "w") as f:
        json.dump(combined, f, indent=2)
    logger.info(f"V4 combined results saved: {combined_path}")


if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    logger.add(f"logs/backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", level="DEBUG")
    main()
