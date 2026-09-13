import pandas as pd
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger

def calculate_regimes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.set_index("timestamp", inplace=True)
    
    # 60-min True Range
    high = df['high']
    low = df['low']
    prev_close = df['close'].shift(1)
    
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    df['tr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # 60-min ATR (Average True Range) -> Volatility
    df['atr_60'] = df['tr'].rolling(60).mean()
    
    # 60-min SMA -> Trend
    df['sma_60'] = df['close'].rolling(60).mean()
    
    # Define Volatility Regimes based on 3-year percentiles
    p25 = df['atr_60'].quantile(0.25)
    p75 = df['atr_60'].quantile(0.75)
    
    df['volatility_regime'] = "Normal"
    df.loc[df['atr_60'] > p75, 'volatility_regime'] = "High Volatility"
    df.loc[df['atr_60'] < p25, 'volatility_regime'] = "Low Volatility (Chop)"
    
    # Define Trend Regimes
    df['trend_regime'] = "Ranging"
    df.loc[df['close'] > df['sma_60'] * 1.001, 'trend_regime'] = "Bullish Trend" # +0.1% away from SMA
    df.loc[df['close'] < df['sma_60'] * 0.999, 'trend_regime'] = "Bearish Trend"
    
    return df.reset_index()

def main():
    logger.info("Loading and calculating market regimes...")
    df_raw = pd.read_csv("data/raw/NIFTY50_1min_3years.csv")
    df_regime = calculate_regimes(df_raw)
    
    # Convert regime lookup to a fast dictionary based on string timestamps
    regime_lookup = {}
    df_regime['timestamp_str'] = df_regime['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Dropna to avoid breaking to_dict
    df_regime_clean = df_regime.dropna(subset=['volatility_regime', 'trend_regime'])
    regime_lookup = df_regime_clean.set_index('timestamp_str')[['volatility_regime', 'trend_regime']].to_dict('index')
    
    logger.info("Regime lookup built. Processing backtests...")
    
    targets = [
        ("V1 (Pre-Train)", "data/backtest_results/backtest_unseen_pretrain_v1_hm.json"),
        ("V2 (Pre-Train)", "data/backtest_results/backtest_unseen_pretrain_v2_hm.json"),
        ("V3 (Pre-Train)", "data/backtest_results/backtest_unseen_pretrain_v3_hm.json"),
        ("V4 (Pre-Train)", "data/backtest_results/backtest_unseen_pretrain_v4_hm.json"),
        ("V1 (Post-Train)", "data/backtest_results/backtest_posttrain_v1_hm.json"),
        ("V2 (Post-Train)", "data/backtest_results/backtest_posttrain_v2_hm.json"),
        ("V3 (Post-Train)", "data/backtest_results/backtest_posttrain_v3_hm.json"),
        ("V4 (Post-Train)", "data/backtest_results/backtest_posttrain_v4_hm.json")
    ]
    
    all_loss_data = {}
    
    for label, path in targets:
        if not os.path.exists(path):
            continue
            
        with open(path, "r") as f:
            bt = json.load(f)
            
        trades = bt.get("trades", [])
        losing_trades = [t for t in trades if t["pnl_rs"] < 0]
        
        enriched_losses = []
        for t in losing_trades:
            entry = t["entry_time"]
            regime_info = regime_lookup.get(entry, {"volatility_regime": "Unknown", "trend_regime": "Unknown"})
            
            t_enriched = t.copy()
            t_enriched["volatility_regime"] = regime_info["volatility_regime"]
            t_enriched["trend_regime"] = regime_info["trend_regime"]
            enriched_losses.append(t_enriched)
            
        all_loss_data[label] = {
            "total_losses": len(losing_trades),
            "trades": enriched_losses
        }
        
    out_path = "data/backtest_results/loss_analysis.json"
    with open(out_path, "w") as f:
        json.dump(all_loss_data, f, indent=2)
        
    logger.info(f"Loss analysis saved to {out_path}!")

if __name__ == "__main__":
    main()
