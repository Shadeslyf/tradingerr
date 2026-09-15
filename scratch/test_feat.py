from app.api.routes.backtest import *
req = BacktestRequest(model_name="V4_Auto_J6NA", start_date="2026-09-15", end_date="2026-09-15", initial_capital=100000.0)
df_raw = pd.read_csv("data/raw/NIFTY50_1min_3years.csv")
df_raw["timestamp"] = pd.to_datetime(df_raw["timestamp"], utc=False)
if df_raw["timestamp"].dt.tz is not None: df_raw["timestamp"] = df_raw["timestamp"].dt.tz_localize(None)

import json
with open("data/live_paper_trading.json", "r") as f: live_state = json.load(f)
live_md = live_state.get("market_data", {})
df_live = pd.DataFrame(live_md)
df_live["timestamp"] = pd.to_datetime(df_live["timestamp"], utc=False)
if df_live["timestamp"].dt.tz is not None: df_live["timestamp"] = df_live["timestamp"].dt.tz_localize(None)
df_raw = pd.concat([df_raw, df_live]).drop_duplicates(subset=["timestamp"], keep="last").sort_values("timestamp").reset_index(drop=True)

start_dt = pd.to_datetime(req.start_date)
end_dt = pd.to_datetime(req.end_date)
buffer_start = start_dt - timedelta(days=2)
df_slice = df_raw[(df_raw["timestamp"].dt.date >= buffer_start.date()) & (df_raw["timestamp"].dt.date <= end_dt.date())].copy()

df_feat = FeaturePipeline.generate_features(df_slice)
df_slice = df_slice.iloc[-len(df_feat):].reset_index(drop=True)
df_feat = df_feat.reset_index(drop=True)
df_feat["timestamp"] = df_slice["timestamp"]

mask = df_feat["timestamp"].dt.date >= start_dt.date()
df_feat = df_feat[mask].copy()

print("Length of df_feat after mask:", len(df_feat))
