import numpy as np
import pandas as pd
from loguru import logger
import joblib

from app.risk.position_sizing import PositionSizer

# Strategy params
LOT_SIZE      = 50
STOP_LOSS_PCT = 0.5   # 0.5% (used for V1/V2)
TARGET_PCT    = 1.5   # 1.5%
HOLD_BARS     = 60

REGIME_MAP = {0: "BULLISH", 1: "RANGE", 2: "BEARISH"}

def _max_drawdown(equity: list, initial: float) -> float:
    if not equity:
        return 0.0
    peak = initial
    max_dd = 0.0
    for val in equity:
        if val > peak:
            peak = val
        dd = (peak - val) / peak * 100
        if dd > max_dd:
            max_dd = dd
    return max_dd

def run_backtest(df_raw: pd.DataFrame, df_feat: pd.DataFrame, model_path: str, initial_capital: float = 100000.0, label: str = "", is_v3: bool = False, is_v4: bool = False, house_money_mode: bool = False) -> dict:
    if df_raw.empty or df_feat.empty:
        return {}

    # Load Model
    try:
        model = joblib.load(model_path)
    except Exception as e:
        logger.error(f"Failed to load model {model_path}: {e}")
        return {}

    expected_cols = model.feature_names_in_
    X = df_feat.reindex(columns=expected_cols, fill_value=0.0)

    # Predictions
    probs = model.predict_proba(X)
    preds = np.argmax(probs, axis=1)
    confs = np.max(probs, axis=1)

    # Apply probability calibration if calibrator exists
    import os
    calibrator_path = os.path.join(os.path.dirname(model_path), "calibrator.joblib")
    if os.path.exists(calibrator_path):
        try:
            calibrator = joblib.load(calibrator_path)
            confs = calibrator.predict(confs)
            logger.debug(f"Applied calibrator from {calibrator_path}")
        except Exception as e:
            logger.warning(f"Failed to load calibrator: {e}")

    timestamps = df_feat.index.tolist() if isinstance(df_feat.index, pd.DatetimeIndex) else df_feat['timestamp'].tolist() if 'timestamp' in df_feat.columns else df_feat.index.tolist()
    closes = df_feat["close"].values if "close" in df_feat.columns else df_raw["close"].values[-len(df_feat):]
    n = len(closes)

    capital = initial_capital
    equity = []
    eq_times = []
    trades = []
    i = 0
    has_withdrawn = False
    total_withdrawn = 0.0

    while i < n - HOLD_BARS:
        sig = preds[i]
        conf = confs[i]

        if sig == 1:
            equity.append(capital)
            eq_times.append(str(timestamps[i]))
            i += 1
            continue
            
        ts = pd.to_datetime(timestamps[i])

        if is_v4:
            adx_val = df_feat.iloc[i]["adx_14"] if "adx_14" in df_feat.columns else 25.0
            if adx_val < 20.0:
                # Regime filter: Skip trade if ADX is too low (choppy market)
                equity.append(capital + total_withdrawn)
                eq_times.append(str(timestamps[i]))
                i += 1
                continue
                
            # 1. Lunch Hour Trap Filter
            if ts.hour == 12 and float(conf) < 0.95:
                equity.append(capital + total_withdrawn)
                eq_times.append(str(timestamps[i]))
                i += 1
                continue
                
            # 2. VSA (Volume Validation) Filter
            if "vol_ratio" in df_feat.columns:
                if df_feat.iloc[i]["vol_ratio"] < 1.0:
                    equity.append(capital + total_withdrawn)
                    eq_times.append(str(timestamps[i]))
                    i += 1
                    continue

        # House Money Withdrawal Logic
        if house_money_mode and not has_withdrawn and capital >= (initial_capital * 2):
            capital -= initial_capital
            total_withdrawn += initial_capital
            has_withdrawn = True

        direction = "LONG" if sig == 0 else "SHORT"
        entry_price = closes[i]
        
        # 3. Dynamic Asymmetrical Targets & Expiry
        if direction == "LONG":
            current_target_pct = 1.2
            current_hold_bars = 90
        else:
            current_target_pct = 1.8
            current_hold_bars = 60
            
        if (is_v3 or is_v4) and "atr_14" in df_feat.columns:
            entry_atr = df_feat.iloc[i]["atr_14"]
            if entry_atr < 4.0:
                current_target_pct *= 0.5  # Scale target closer in chop
                current_hold_bars = int(current_hold_bars * 1.5)
            elif entry_atr > 10.0:
                current_target_pct *= 1.5  # Expand target in high volatility

        # Fixed SL/TP targets for V1/V2 (and TP for V3/V4)
        if direction == "LONG":
            sl_price = entry_price * (1 - STOP_LOSS_PCT / 100)
            tp_price = entry_price * (1 + current_target_pct / 100)
        else:
            sl_price = entry_price * (1 + STOP_LOSS_PCT / 100)
            tp_price = entry_price * (1 - current_target_pct / 100)

        max_idx = min(i + current_hold_bars, n - 1)
        exit_price  = closes[max_idx]
        exit_reason = "HOLD_EXPIRY"
        exit_bar    = max_idx

        if is_v3 or is_v4:
            # 4. ATR Trailing Stop Logic (Chandelier Exit)
            ATR_MULT_INITIAL = 3.0
            ATR_MULT_TRAIL = 2.0
            
            entry_atr = df_feat.iloc[i]["atr_14"] if "atr_14" in df_feat.columns else (entry_price * 0.002)
            highest_high = entry_price
            lowest_low = entry_price
            breakeven_activated = False

            # Calculate dynamic position size
            ev_data = {
                'max_loss': (entry_atr * ATR_MULT_INITIAL) * LOT_SIZE,
                'max_profit': entry_price * (current_target_pct/100) * LOT_SIZE,
                'prob_win': float(conf),
                'prob_loss': 1 - float(conf)
            }
            risk_to_use = 20.0 if (house_money_mode and has_withdrawn) else 1.0
            quantity = PositionSizer.calculate_fixed_fractional(capital, ev_data, risk_pct=risk_to_use, lot_size=LOT_SIZE)
            if quantity == 0:
                quantity = LOT_SIZE
                
            MAX_LOTS = 1000
            if quantity > (MAX_LOTS * LOT_SIZE):
                quantity = MAX_LOTS * LOT_SIZE

            for j in range(i+1, min(i+current_hold_bars+1, n)):
                bar_low  = df_feat.iloc[j]["low"]  if "low"  in df_feat.columns else closes[j]
                bar_high = df_feat.iloc[j]["high"] if "high" in df_feat.columns else closes[j]
                bar_atr  = df_feat.iloc[j]["atr_14"] if "atr_14" in df_feat.columns else entry_atr
                
                if direction == "LONG":
                    highest_high = max(highest_high, bar_high)
                    # Initial stop is wider (3x ATR), trailing is tighter (2x ATR)
                    if highest_high == entry_price:
                        trailing_sl = highest_high - (ATR_MULT_INITIAL * bar_atr)
                    else:
                        trailing_sl = highest_high - (ATR_MULT_TRAIL * bar_atr)
                    
                    if is_v4 and not breakeven_activated and (highest_high - entry_price) >= (0.5 * entry_atr):
                        breakeven_activated = True
                        
                    if breakeven_activated:
                        trailing_sl = max(trailing_sl, entry_price)
                        
                    if bar_low <= trailing_sl:
                        exit_price = trailing_sl; exit_reason = "TRAILING_STOP"; exit_bar = j; break
                    if bar_high >= tp_price:
                        exit_price = tp_price; exit_reason = "TARGET_HIT"; exit_bar = j; break
                else:
                    lowest_low = min(lowest_low, bar_low)
                    if lowest_low == entry_price:
                        trailing_sl = lowest_low + (ATR_MULT_INITIAL * bar_atr)
                    else:
                        trailing_sl = lowest_low + (ATR_MULT_TRAIL * bar_atr)
                    
                    if is_v4 and not breakeven_activated and (entry_price - lowest_low) >= (0.5 * entry_atr):
                        breakeven_activated = True
                        
                    if breakeven_activated:
                        trailing_sl = min(trailing_sl, entry_price)
                        
                    if bar_high >= trailing_sl:
                        exit_price = trailing_sl; exit_reason = "TRAILING_STOP"; exit_bar = j; break
                    if bar_low <= tp_price:
                        exit_price = tp_price; exit_reason = "TARGET_HIT"; exit_bar = j; break
        else:
            # V1 / V2 standard logic
            # Calculate dynamic position size
            ev_data = {
                'max_loss': entry_price * (STOP_LOSS_PCT/100) * LOT_SIZE,
                'max_profit': entry_price * (current_target_pct/100) * LOT_SIZE,
                'prob_win': float(conf),
                'prob_loss': 1 - float(conf)
            }
            risk_to_use = 20.0 if (house_money_mode and has_withdrawn) else 1.0
            quantity = PositionSizer.calculate_fixed_fractional(capital, ev_data, risk_pct=risk_to_use, lot_size=LOT_SIZE)
            if quantity == 0:
                quantity = LOT_SIZE

            MAX_LOTS = 1000
            if quantity > (MAX_LOTS * LOT_SIZE):
                quantity = MAX_LOTS * LOT_SIZE
                
            for j in range(i+1, min(i+current_hold_bars+1, n)):
                bar_low  = df_feat.iloc[j]["low"]  if "low"  in df_feat.columns else closes[j]
                bar_high = df_feat.iloc[j]["high"] if "high" in df_feat.columns else closes[j]
                if direction == "LONG":
                    if bar_low <= sl_price:
                        exit_price = sl_price; exit_reason = "STOP_LOSS"; exit_bar = j; break
                    if bar_high >= tp_price:
                        exit_price = tp_price; exit_reason = "TARGET_HIT"; exit_bar = j; break
                else:
                    if bar_high >= sl_price:
                        exit_price = sl_price; exit_reason = "STOP_LOSS"; exit_bar = j; break
                    if bar_low <= tp_price:
                        exit_price = tp_price; exit_reason = "TARGET_HIT"; exit_bar = j; break

        # Option Greeks Simulation
        OPTION_DELTA = 0.50
        THETA_DECAY_PER_MIN = 0.20 # ₹0.20 per minute per lot
        AVG_PREMIUM = 150.0
        
        hold_minutes = exit_bar - i
        
        if direction == "LONG":
            spot_pnl = (exit_price - entry_price) * quantity
        else:
            spot_pnl = (entry_price - exit_price) * quantity
            
        gross_option_pnl = (spot_pnl * OPTION_DELTA) - (THETA_DECAY_PER_MIN * hold_minutes * (quantity / LOT_SIZE))
            
        SLIPPAGE_PCT = 0.05
        TRANSACTION_COST = 60.0
        
        # Slippage calculated on Option Premium value, NOT Spot value!
        option_entry_value = AVG_PREMIUM * quantity
        option_exit_value = AVG_PREMIUM * quantity # Rough estimate
        slippage_cost = (option_entry_value + option_exit_value) * (SLIPPAGE_PCT / 100)
        
        pnl = gross_option_pnl - slippage_cost - TRANSACTION_COST

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
            "capital_after": round(float(capital + total_withdrawn), 2),
        })

        for k in range(i, exit_bar + 1):
            equity.append(capital + total_withdrawn)
            if k + 1 < n:
                eq_times.append(str(timestamps[k + 1]))
        i = exit_bar + 1

    while len(equity) < n:
        equity.append(capital + total_withdrawn)
    while len(eq_times) < n:
        eq_times.append(str(timestamps[min(len(eq_times), n-1)]))

    pnls = [t["pnl_rs"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    total_return_pct = (((capital + total_withdrawn) - initial_capital) / initial_capital) * 100
    win_rate = (len(wins) / len(pnls) * 100) if pnls else 0
    avg_win  = np.mean(wins)   if wins   else 0
    avg_loss = np.mean(losses) if losses else 0
    profit_factor = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else float("inf")
    max_dd = _max_drawdown(equity, initial_capital)

    summary = {
        "label":            label,
        "initial_capital":  initial_capital,
        "final_capital":    round(capital + total_withdrawn, 2),
        "trading_capital":  round(capital, 2),
        "total_withdrawn":  round(total_withdrawn, 2),
        "net_pnl":          round(capital + total_withdrawn - initial_capital, 2),
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
