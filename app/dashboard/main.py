import sys
import os
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Add root project directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database.models import SessionLocal, init_db
from app.dashboard.data_loader import load_trade_history, load_active_positions

# Initialize DB connection
init_db()
session = SessionLocal()

# Set page config
st.set_page_config(page_title="Options AI Dashboard", page_icon="📈", layout="wide")

st.title("📈 NIFTY AI Trading Dashboard")
st.markdown("Monitor live paper trading performance, risk, and equity curves.")

# Load Data
df_history = load_trade_history(session)
df_active = load_active_positions(session)

# ----------------- TOP METRICS -----------------
st.subheader("Performance Overview")

INITIAL_CAPITAL = 300000.0

if not df_history.empty:
    total_trades = len(df_history)
    winning_trades = len(df_history[df_history['Cash PnL (₹)'] > 0])
    win_rate = (winning_trades / total_trades) * 100
    total_cash_pnl = df_history['Cash PnL (₹)'].sum()
    final_capital = INITIAL_CAPITAL + total_cash_pnl
    
    # Calculate losses only
    losing_trades = df_history[df_history['Cash PnL (₹)'] < 0]
    total_losses = losing_trades['Cash PnL (₹)'].sum()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Initial Capital", f"₹{INITIAL_CAPITAL:,.2f}")
    col2.metric("Final Capital", f"₹{final_capital:,.2f}", delta=f"₹{total_cash_pnl:,.2f}")
    col3.metric("Total Trades", total_trades)
    col4.metric("Win Rate", f"{win_rate:.1f}%")
    col5.metric("Total Losses", f"₹{total_losses:,.2f}")
else:
    st.info("No closed trades yet. Run the paper trading engine to generate history.")

st.markdown("---")

# ----------------- EQUITY CURVE -----------------
st.subheader("Cumulative Equity Curve (₹)")
if not df_history.empty:
    # Sort by time to calculate cumulative PnL correctly
    df_chart = df_history.sort_values('Entry Time').copy()
    df_chart['Cumulative PnL (₹)'] = df_chart['Cash PnL (₹)'].cumsum()
    df_chart['Equity'] = INITIAL_CAPITAL + df_chart['Cumulative PnL (₹)']
    
    fig = px.line(
        df_chart, 
        x='Exit Time', 
        y='Equity', 
        title="Portfolio Growth (₹)",
        markers=True,
        template="plotly_dark"
    )
    # Add a zero line at initial capital
    fig.add_hline(y=INITIAL_CAPITAL, line_dash="dash", line_color="gray")
    fig.update_traces(line_color='#00ff88', marker=dict(size=8))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Not enough data to draw equity curve.")
    
st.markdown("---")

# ----------------- TABLES -----------------
colA, colB = st.columns([2, 1])

with colA:
    st.subheader("Trade Ledger (Closed)")
    if not df_history.empty:
        # Style negative PnL red and positive green
        def color_pnl(val):
            color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
            return f'color: {color}'
            
        st.dataframe(df_history.style.map(color_pnl, subset=['Net PnL %']), use_container_width=True)
    else:
        st.write("No closed trades.")
        
with colB:
    st.subheader("Live Open Legs")
    if not df_active.empty:
        st.dataframe(df_active, use_container_width=True)
    else:
        st.success("No active trades currently open.")

session.close()
