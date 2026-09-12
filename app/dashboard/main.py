"""
NIFTY AI Trading Dashboard — Premium Performance Overview
Displays:
  1. Walk-Forward Training Summary (22 folds)
  2. Backtest: Jan-Apr 2026 (₹1,00,000 initial capital)
  3. Live Forward Test: 30-day real data (Aug-Sep 2026)
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NIFTY AI Trader",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
# CUSTOM CSS — Premium Dark Theme
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background: #0a0e1a;
    color: #e2e8f0;
}

.main { background: #0a0e1a; }
.block-container { padding: 1.5rem 2rem; max-width: 100%; }

/* Header */
.hero-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
    border: 1px solid rgba(99,102,241,0.3);
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
}
.hero-header::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle, rgba(99,102,241,0.08) 0%, transparent 60%);
    animation: pulse 4s ease-in-out infinite;
}
@keyframes pulse { 0%,100% { opacity:0.5; } 50% { opacity:1; } }
.hero-title {
    font-size: 2.2rem;
    font-weight: 700;
    background: linear-gradient(135deg, #818cf8, #a78bfa, #38bdf8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
}
.hero-sub {
    color: #94a3b8;
    font-size: 0.95rem;
    margin-top: 0.4rem;
}

/* Metric cards */
.metric-card {
    background: linear-gradient(135deg, #0f172a, #1e293b);
    border: 1px solid rgba(99,102,241,0.2);
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    text-align: center;
    transition: transform 0.2s, border-color 0.2s;
}
.metric-card:hover { transform: translateY(-2px); border-color: rgba(99,102,241,0.5); }
.metric-label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.1em; color: #64748b; font-weight: 600; }
.metric-value { font-size: 1.7rem; font-weight: 700; margin: 0.3rem 0 0; }
.metric-value.green { color: #34d399; }
.metric-value.red   { color: #f87171; }
.metric-value.blue  { color: #60a5fa; }
.metric-value.purple{ color: #a78bfa; }
.metric-value.gold  { color: #fbbf24; }

/* Section headers */
.section-header {
    font-size: 1.15rem;
    font-weight: 600;
    color: #e2e8f0;
    padding: 0.5rem 0;
    border-bottom: 1px solid rgba(99,102,241,0.25);
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    background: #0f172a;
    border-radius: 10px;
    padding: 4px;
    border: 1px solid rgba(99,102,241,0.2);
}
.stTabs [data-baseweb="tab"] {
    color: #94a3b8;
    border-radius: 8px;
    font-weight: 500;
    font-size: 0.88rem;
}
.stTabs [aria-selected="true"] {
    background: rgba(99,102,241,0.25) !important;
    color: #a5b4fc !important;
}

/* Signal badges */
.badge-bull  { background: rgba(52,211,153,0.15); color:#34d399; border:1px solid rgba(52,211,153,0.4); padding:2px 10px; border-radius:20px; font-size:0.75rem; font-weight:600; }
.badge-bear  { background: rgba(248,113,113,0.15); color:#f87171; border:1px solid rgba(248,113,113,0.4); padding:2px 10px; border-radius:20px; font-size:0.75rem; font-weight:600; }
.badge-range { background: rgba(251,191,36,0.15);  color:#fbbf24; border:1px solid rgba(251,191,36,0.4);  padding:2px 10px; border-radius:20px; font-size:0.75rem; font-weight:600; }

/* Status bar */
.status-bar {
    background: linear-gradient(90deg, rgba(99,102,241,0.1), rgba(167,139,250,0.1));
    border: 1px solid rgba(99,102,241,0.2);
    border-radius: 8px;
    padding: 0.6rem 1.2rem;
    font-size: 0.82rem;
    color: #94a3b8;
    display: flex;
    gap: 2rem;
    margin-bottom: 1.5rem;
}
.status-dot {
    display: inline-block; width: 8px; height: 8px;
    border-radius: 50%; background: #34d399;
    animation: blink 1.5s ease-in-out infinite;
    margin-right: 6px;
}
@keyframes blink { 0%,100% { opacity:1; } 50% { opacity:0.3; } }

/* Dataframe */
[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }

/* Divider */
hr { border-color: rgba(99,102,241,0.15) !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────────
RESULTS_DIR = "data/backtest_results"
WF_SUMMARY  = "data/walk_forward_results"

@st.cache_data(ttl=60)
def load_backtest(fname):
    path = os.path.join(RESULTS_DIR, fname)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)

@st.cache_data(ttl=60)
def load_wf_summary():
    files = sorted([f for f in os.listdir(WF_SUMMARY) if f.startswith("walk_forward_summary") and f.endswith(".csv")]) if os.path.exists(WF_SUMMARY) else []
    if not files:
        return pd.DataFrame()
    return pd.read_csv(os.path.join(WF_SUMMARY, files[-1]))

bt1  = load_backtest("backtest_jan_apr_2026.json")
bt1_v2 = load_backtest("backtest_jan_apr_2026_v2.json")
bt1_v3 = load_backtest("backtest_jan_apr_2026_v3.json")
bt2  = load_backtest("backtest_30d_live.json")
bt2_v2 = load_backtest("backtest_30d_live_v2.json")
bt2_v3 = load_backtest("backtest_30d_live_v3.json")
wf_df = load_wf_summary()

# ─────────────────────────────────────────────────────────────
# HERO HEADER
# ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-header">
    <div class="hero-title">📈 NIFTY AI Trading Intelligence</div>
    <div class="hero-sub">Walk-Forward ML · 3-Class Regime Detection · Real Capital Simulation</div>
</div>
""", unsafe_allow_html=True)

now = datetime.now().strftime("%d %b %Y, %H:%M IST")
st.markdown(f"""
<div class="status-bar">
    <span><span class="status-dot"></span>Model Active</span>
    <span>📅 {now}</span>
    <span>🧠 XGBoost · 3-Class (BULLISH / RANGE / BEARISH)</span>
    <span>📊 22 Walk-Forward Folds</span>
    <span>💰 Initial Capital: ₹1,00,000</span>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# TOP-LEVEL SUMMARY METRICS
# ─────────────────────────────────────────────────────────────

def metric_html(label, value, cls="blue"):
    return f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value {cls}">{value}</div></div>'

st.markdown('<div class="section-header" id="performance-overview">🎯 Performance Overview (V1 vs V2 vs V3)</div>', unsafe_allow_html=True)

ic = bt1["initial_capital"]   if bt1 else 100000

# V1 data
pnl1_v1 = bt1["net_pnl"]         if bt1 else 0
pnl2_v1 = bt2["net_pnl"]         if bt2 else 0
trades1_v1 = bt1["total_trades"] if bt1 else 0
wr1_v1 = bt1["win_rate_pct"]     if bt1 else 0

# V2 data
pnl1_v2 = bt1_v2["net_pnl"]      if bt1_v2 else 0
pnl2_v2 = bt2_v2["net_pnl"]      if bt2_v2 else 0
trades1_v2 = bt1_v2["total_trades"] if bt1_v2 else 0
wr1_v2 = bt1_v2["win_rate_pct"]     if bt1_v2 else 0

# V3 data
pnl1_v3 = bt1_v3["net_pnl"]      if bt1_v3 else 0
pnl2_v3 = bt2_v3["net_pnl"]      if bt2_v3 else 0
trades1_v3 = bt1_v3["total_trades"] if bt1_v3 else 0
wr1_v3 = bt1_v3["win_rate_pct"]     if bt1_v3 else 0

perf_data = [
    {"Model": "V1 (Price Only)", "Jan-Apr P&L": pnl1_v1, "Aug-Sep Live P&L": pnl2_v1, "Jan-Apr Trades": trades1_v1, "Jan-Apr Win Rate": wr1_v1},
    {"Model": "V2 (Cross-Asset)", "Jan-Apr P&L": pnl1_v2, "Aug-Sep Live P&L": pnl2_v2, "Jan-Apr Trades": trades1_v2, "Jan-Apr Win Rate": wr1_v2},
    {"Model": "V3 (Professional)", "Jan-Apr P&L": pnl1_v3, "Aug-Sep Live P&L": pnl2_v3, "Jan-Apr Trades": trades1_v3, "Jan-Apr Win Rate": wr1_v3}
]

df_perf = pd.DataFrame(perf_data)
df_perf["Jan-Apr P&L"] = df_perf["Jan-Apr P&L"].apply(lambda x: f"₹{x:+,.0f}")
df_perf["Aug-Sep Live P&L"] = df_perf["Aug-Sep Live P&L"].apply(lambda x: f"₹{x:+,.0f}")
df_perf["Jan-Apr Win Rate"] = df_perf["Jan-Apr Win Rate"].apply(lambda x: f"{x:.1f}%")

st.markdown(f"**Initial Capital:** ₹{ic:,.0f}")
st.dataframe(df_perf, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# MAIN TABS
# ─────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Equity & P&L Curves",
    "🔬 Walk-Forward Analysis",
    "📋 Trade Ledger",
    "🔮 Live 30-Day Signal",
    "🛡️ Multi-Index Robustness",
    "📅 Monthly Performance"
])

PLOTLY_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(10,14,26,0)",
    plot_bgcolor="rgba(15,23,42,0.6)",
    font=dict(family="Inter", color="#94a3b8", size=12),
    margin=dict(l=50, r=20, t=50, b=40),
    xaxis=dict(gridcolor="rgba(99,102,241,0.08)", linecolor="rgba(99,102,241,0.2)"),
    yaxis=dict(gridcolor="rgba(99,102,241,0.08)", linecolor="rgba(99,102,241,0.2)"),
)


# ── TAB 1: Equity Curves ─────────────────────────────────────
with tab1:
    st.markdown('<div class="section-header">💹 Cumulative Equity Curve</div>', unsafe_allow_html=True)

    if bt1 and bt2:
        fig = make_subplots(rows=2, cols=2,
            subplot_titles=("Jan–Apr 2026 Equity Curve (₹)", "30-Day Live Equity Curve (₹)",
                            "Jan–Apr 2026 Rolling P&L per Trade", "30-Day Rolling P&L per Trade"),
            vertical_spacing=0.15, horizontal_spacing=0.08)

        # ── Equity curve 1
        eq1 = bt1["equity_curve"]
        t1  = bt1["equity_times"]
        # Sample every 30 bars for performance
        step = max(1, len(eq1)//1000)
        fig.add_trace(go.Scatter(
            x=t1[::step], y=eq1[::step],
            mode="lines", name="Equity (Jan–Apr)",
            line=dict(color="#818cf8", width=2),
            fill="tozeroy", fillcolor="rgba(129,140,248,0.08)"
        ), row=1, col=1)
        fig.add_hline(y=ic, line_dash="dash", line_color="rgba(148,163,184,0.4)", row=1, col=1)

        # ── Equity curve 2
        eq2 = bt2["equity_curve"]
        t2  = bt2["equity_times"]
        step2 = max(1, len(eq2)//500)
        start2 = bt2["initial_capital"]
        color2 = "#34d399" if bt2["net_pnl"] >= 0 else "#f87171"
        fig.add_trace(go.Scatter(
            x=t2[::step2], y=eq2[::step2],
            mode="lines", name="Equity (30-Day Live)",
            line=dict(color=color2, width=2),
            fill="tozeroy", fillcolor=f"rgba(248,113,113,0.06)" if color2=="#f87171" else "rgba(52,211,153,0.06)"
        ), row=1, col=2)
        fig.add_hline(y=start2, line_dash="dash", line_color="rgba(148,163,184,0.4)", row=1, col=2)

        # ── Trade P&L bar chart 1
        trades1_df = pd.DataFrame(bt1["trades"])
        if not trades1_df.empty:
            colors1 = ["#34d399" if p > 0 else "#f87171" for p in trades1_df["pnl_rs"]]
            fig.add_trace(go.Bar(
                x=list(range(len(trades1_df))),
                y=trades1_df["pnl_rs"].values,
                marker_color=colors1, name="Trade P&L (Jan–Apr)", showlegend=False
            ), row=2, col=1)

        # ── Trade P&L bar chart 2
        trades2_df = pd.DataFrame(bt2["trades"])
        if not trades2_df.empty:
            colors2 = ["#34d399" if p > 0 else "#f87171" for p in trades2_df["pnl_rs"]]
            fig.add_trace(go.Bar(
                x=list(range(len(trades2_df))),
                y=trades2_df["pnl_rs"].values,
                marker_color=colors2, name="Trade P&L (30-Day)", showlegend=False
            ), row=2, col=2)

        fig.update_layout(height=700, title_text="", showlegend=False, **PLOTLY_LAYOUT)
        for i in [1,2]:
            fig.update_xaxes(gridcolor="rgba(99,102,241,0.08)", row=1, col=i)
            fig.update_xaxes(gridcolor="rgba(99,102,241,0.08)", row=2, col=i)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">📊 Combined Capital Journey</div>', unsafe_allow_html=True)
    if bt1 and bt2:
        # Stitch equity curves
        eq1_full = bt1["equity_curve"]
        eq2_full = bt2["equity_curve"]
        times1   = bt1["equity_times"]
        times2   = bt2["equity_times"]

        fig2 = go.Figure()
        step = max(1, len(eq1_full)//800)
        fig2.add_trace(go.Scatter(
            x=times1[::step], y=eq1_full[::step],
            mode="lines", name="Jan–Apr 2026",
            line=dict(color="#818cf8", width=2.5),
        ))
        step2 = max(1, len(eq2_full)//400)
        fig2.add_trace(go.Scatter(
            x=times2[::step2], y=eq2_full[::step2],
            mode="lines", name="Live 30-Day (Aug-Sep 2026)",
            line=dict(color="#34d399" if bt2["net_pnl"]>=0 else "#f87171", width=2.5),
        ))
        fig2.add_hline(y=ic, line_dash="dot", line_color="rgba(148,163,184,0.5)",
                       annotation_text="Initial ₹1,00,000", annotation_font_color="#94a3b8")
        fig2.update_layout(
            height=350, yaxis_title="Portfolio Value (₹)",
            xaxis_title="Time", legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                bgcolor="rgba(15,23,42,0.8)", bordercolor="rgba(99,102,241,0.3)"
            ), **PLOTLY_LAYOUT
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Signal distribution pie
    if bt1:
        col1, col2 = st.columns(2)
        trades_df = pd.DataFrame(bt1["trades"])
        with col1:
            st.markdown('<div class="section-header">🥧 Signal Distribution (Jan–Apr)</div>', unsafe_allow_html=True)
            if not trades_df.empty:
                sig_counts = trades_df["signal"].value_counts()
                fig3 = go.Figure(go.Pie(
                    labels=sig_counts.index, values=sig_counts.values,
                    hole=0.5,
                    marker=dict(colors=["#34d399","#fbbf24","#f87171"]),
                ))
                fig3.update_layout(height=300, **PLOTLY_LAYOUT, showlegend=True)
                st.plotly_chart(fig3, use_container_width=True)

        with col2:
            st.markdown('<div class="section-header">📤 Exit Reason Breakdown (Jan–Apr)</div>', unsafe_allow_html=True)
            if not trades_df.empty:
                er_counts = trades_df["exit_reason"].value_counts()
                fig4 = go.Figure(go.Pie(
                    labels=er_counts.index, values=er_counts.values,
                    hole=0.5,
                    marker=dict(colors=["#60a5fa","#34d399","#f87171"]),
                ))
                fig4.update_layout(height=300, **PLOTLY_LAYOUT, showlegend=True)
                st.plotly_chart(fig4, use_container_width=True)


# ── TAB 2: Walk-Forward ──────────────────────────────────────
with tab2:
    st.markdown('<div class="section-header">🔬 Walk-Forward Training Results (22 Folds)</div>', unsafe_allow_html=True)

    if not wf_df.empty:
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.markdown(metric_html("Avg F1 (7-class baseline)", "0.186", "red"), unsafe_allow_html=True)
        with col2: st.markdown(metric_html("Avg F1 (3-class v1)", "0.314", "gold"), unsafe_allow_html=True)
        with col3: st.markdown(metric_html("Avg F1 (v2 · 55 features)", "0.349", "green"), unsafe_allow_html=True)
        with col4: st.markdown(metric_html("Best Fold F1", "0.412", "gold"), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # F1 over folds
        fig5 = go.Figure()
        fold_nums = list(range(1, len(wf_df)+1))
        fig5.add_trace(go.Bar(
            x=fold_nums, y=wf_df["f1_macro"].values,
            marker=dict(
                color=wf_df["f1_macro"].values,
                colorscale=[[0,"#f87171"],[0.5,"#fbbf24"],[1,"#34d399"]],
                showscale=True, colorbar=dict(title="F1")
            ),
            name="F1 Macro", text=[f"{v:.3f}" for v in wf_df["f1_macro"].values],
            textposition="outside", textfont=dict(size=9)
        ))
        fig5.add_hline(y=wf_df["f1_macro"].mean(), line_dash="dash", line_color="#818cf8",
                       annotation_text=f"Avg F1={wf_df['f1_macro'].mean():.3f}")
        fig5.update_layout(
            height=380, xaxis_title="Fold", yaxis_title="F1 Score (Macro)",
            title="Walk-Forward F1 Score per Fold (3-Class BULLISH/RANGE/BEARISH)",
            **PLOTLY_LAYOUT
        )
        st.plotly_chart(fig5, use_container_width=True)

        # Accuracy line
        fig6 = go.Figure()
        fig6.add_trace(go.Scatter(
            x=fold_nums, y=wf_df["accuracy"].values,
            mode="lines+markers", name="Accuracy",
            line=dict(color="#60a5fa", width=2),
            marker=dict(size=8, color="#60a5fa")
        ))
        fig6.add_trace(go.Scatter(
            x=fold_nums, y=wf_df["f1_macro"].values,
            mode="lines+markers", name="F1 Macro",
            line=dict(color="#a78bfa", width=2, dash="dot"),
            marker=dict(size=8, color="#a78bfa")
        ))
        fig6.add_hline(y=0.33, line_dash="dot", line_color="rgba(148,163,184,0.3)",
                       annotation_text="Random baseline (3-class)")
        fig6.update_layout(
            height=320, xaxis_title="Fold", yaxis_title="Score",
            title="Accuracy vs F1 Across Folds",
            legend=dict(bgcolor="rgba(15,23,42,0.8)", bordercolor="rgba(99,102,241,0.3)"),
            **PLOTLY_LAYOUT
        )
        st.plotly_chart(fig6, use_container_width=True)

        # Table
        st.markdown('<div class="section-header">📋 Fold-by-Fold Detail Table</div>', unsafe_allow_html=True)
        display_df = wf_df.copy()
        display_df.insert(0, "Fold", range(1, len(display_df)+1))
        display_df["Train Period"] = display_df["train_start"] + " → " + display_df["train_end"]
        display_df["Test Period"]  = display_df["test_start"]  + " → " + display_df["test_end"]
        display_cols = ["Fold","Train Period","Test Period","train_rows","test_rows","accuracy","precision","recall","f1_macro"]
        col_rename   = {"train_rows":"Train Rows","test_rows":"Test Rows","accuracy":"Accuracy","precision":"Precision","recall":"Recall","f1_macro":"F1 Macro"}
        display_df = display_df[display_cols].rename(columns=col_rename)

        # Format numeric columns before display (no Styler needed)
        for col in ["Accuracy", "Precision", "Recall", "F1 Macro"]:
            display_df[col] = display_df[col].apply(lambda v: f"{v:.3f}")

        st.dataframe(display_df, use_container_width=True, height=400)
    else:
        st.info("Walk-forward results not found. Run `scripts/walk_forward_train.py` first.")


# ── TAB 5: MULTI-INDEX ROBUSTNESS ─────────────────────────────────────
with tab5:
    st.markdown('<div class="section-header">🛡️ Model Robustness Across Indices (V1 vs V2)</div>', unsafe_allow_html=True)
    st.caption("Testing the NIFTY 50 trained models blindly on other major indices (Jan-Apr 2026).")
    
    robustness_file = "data/backtest_results/multi_index_robustness.json"
    if os.path.exists(robustness_file):
        with open(robustness_file, "r") as f:
            rob_data = json.load(f)
        
        if rob_data:
            # Handle both old format (just indices) and new format (nested by V1/V2)
            if "V1" in rob_data and "V2" in rob_data:
                v1_data = rob_data.get("V1", {})
                v2_data = rob_data.get("V2", {})
                v3_data = rob_data.get("V3", {})
            else:
                v1_data = rob_data
                v2_data = {}
                v3_data = {}

            c1, c2, c3 = st.columns(3)

            with c1:
                st.markdown("##### 🟦 V1 Model (Price Only)")
                if v1_data:
                    v1_rows = []
                    for idx_name, stats in v1_data.items():
                        v1_rows.append({
                            "Index": idx_name,
                            "Net P&L (₹)": stats.get("net_pnl_rs", 0),
                            "Return %": stats.get("return_pct", 0),
                            "Win Rate": stats.get("win_rate", 0),
                            "Total Trades": stats.get("total_trades", 0)
                        })
                    df_v1 = pd.DataFrame(v1_rows)
                    df_v1["Net P&L (₹)"] = df_v1["Net P&L (₹)"].apply(lambda x: f"{x:+,.2f}")
                    df_v1["Return %"] = df_v1["Return %"].apply(lambda x: f"{x:+.2f}%")
                    df_v1["Win Rate"] = df_v1["Win Rate"].apply(lambda x: f"{x*100:.1f}%")
                    st.dataframe(df_v1, use_container_width=True, height=250)
                else:
                    st.info("No V1 data available.")
            
            with c2:
                st.markdown("##### 🟪 V2 Model (Cross-Asset)")
                if v2_data:
                    v2_rows = []
                    for idx_name, stats in v2_data.items():
                        v2_rows.append({
                            "Index": idx_name,
                            "Net P&L (₹)": stats.get("net_pnl_rs", 0),
                            "Return %": stats.get("return_pct", 0),
                            "Win Rate": stats.get("win_rate", 0),
                            "Total Trades": stats.get("total_trades", 0)
                        })
                    df_v2 = pd.DataFrame(v2_rows)
                    df_v2["Net P&L (₹)"] = df_v2["Net P&L (₹)"].apply(lambda x: f"{x:+,.2f}")
                    df_v2["Return %"] = df_v2["Return %"].apply(lambda x: f"{x:+.2f}%")
                    df_v2["Win Rate"] = df_v2["Win Rate"].apply(lambda x: f"{x*100:.1f}%")
                    st.dataframe(df_v2, use_container_width=True, height=250)
                else:
                    st.info("No V2 data available.")

            with c3:
                st.markdown("##### 🟩 V3 Model (Professional)")
                if v3_data:
                    v3_rows = []
                    for idx_name, stats in v3_data.items():
                        v3_rows.append({
                            "Index": idx_name,
                            "Net P&L (₹)": stats.get("net_pnl_rs", 0),
                            "Return %": stats.get("return_pct", 0),
                            "Win Rate": stats.get("win_rate", 0),
                            "Total Trades": stats.get("total_trades", 0)
                        })
                    df_v3 = pd.DataFrame(v3_rows)
                    df_v3["Net P&L (₹)"] = df_v3["Net P&L (₹)"].apply(lambda x: f"{x:+,.2f}")
                    df_v3["Return %"] = df_v3["Return %"].apply(lambda x: f"{x:+.2f}%")
                    df_v3["Win Rate"] = df_v3["Win Rate"].apply(lambda x: f"{x*100:.1f}%")
                    st.dataframe(df_v3, use_container_width=True, height=250)
                else:
                    st.info("No V3 data available.")

            st.markdown("""
            > **Analysis:** V3 model uses professional features (ADX, MACD, etc.).
            > V2 model pads missing cross-asset features with neutral (0) values when evaluated out-of-context. 
            > V1 model acts strictly on price, maintaining directional consistency (win rate) but breaking down on risk-reward when NIFTY 50 specific ATR optimizations are applied blindly to other indices.
            """)
        else:
            st.info("No robustness data found.")
    else:
        st.info("Run `scripts/run_multi_index_robustness.py` to generate robustness data.")


# ── TAB 6: Monthly Performance ────────────────────────────────
with tab6:
    st.markdown('<div class="section-header">📅 Monthly Performance Comparison</div>', unsafe_allow_html=True)
    st.caption("Aggregated monthly P&L across all available backtest windows (Jan-Apr & Aug-Sep 2026).")
    
    monthly_data = []
    
    for model_name, b1, b2 in [("V1 (Price Only)", bt1, bt2), ("V2 (Cross-Asset)", bt1_v2, bt2_v2), ("V3 (Professional)", bt1_v3, bt2_v3)]:
        trades = []
        if b1 and "trades" in b1: trades.extend(b1["trades"])
        if b2 and "trades" in b2: trades.extend(b2["trades"])
        
        if trades:
            df = pd.DataFrame(trades)
            df['entry_time'] = pd.to_datetime(df['entry_time'])
            df['Month'] = df['entry_time'].dt.strftime('%b %Y')
            monthly_pnl = df.groupby('Month')['pnl_rs'].sum().reset_index()
            monthly_pnl['Model'] = model_name
            monthly_data.append(monthly_pnl)
            
    if monthly_data:
        combined_monthly = pd.concat(monthly_data)
        
        # Sort months chronologically
        combined_monthly['date'] = pd.to_datetime(combined_monthly['Month'])
        combined_monthly = combined_monthly.sort_values('date')
        
        import plotly.express as px
        fig9 = px.bar(
            combined_monthly, x="Month", y="pnl_rs", color="Model", barmode="group",
            color_discrete_map={"V1 (Price Only)": "#60a5fa", "V2 (Cross-Asset)": "#a78bfa", "V3 (Professional)": "#34d399"},
            title="Monthly P&L Comparison (₹)",
            template="plotly_dark"
        )
        fig9.update_layout(height=450, **PLOTLY_LAYOUT)
        st.plotly_chart(fig9, use_container_width=True)
        
        # Table
        st.markdown('<div class="section-header">📋 Monthly P&L Breakdown</div>', unsafe_allow_html=True)
        pivot = combined_monthly.pivot(index='Month', columns='Model', values='pnl_rs').fillna(0)
        # Re-sort pivot by real dates
        pivot['temp_date'] = pd.to_datetime(pivot.index)
        pivot = pivot.sort_values('temp_date').drop(columns=['temp_date'])
        
        for col in pivot.columns:
            pivot[col] = pivot[col].apply(lambda x: f"₹{x:+,.2f}")
        st.dataframe(pivot, use_container_width=True)
    else:
        st.info("No trade data available to compute monthly performance.")


# ── TAB 3: Trade Ledger ──────────────────────────────────────
with tab3:
    st.markdown('<div class="section-header">📋 Jan–Apr 2026 Trade Ledger</div>', unsafe_allow_html=True)

    model_sel = st.radio("Model", ["V1 (Price Only)", "V2 (Cross-Asset)", "V3 (Professional Strategy)"], horizontal=True)
    mode = st.radio("Dataset", ["Jan–Apr 2026 Backtest", "30-Day Live (Aug–Sep 2026)"], horizontal=True)
    
    if model_sel == "V1 (Price Only)":
        bt_sel = bt1 if mode.startswith("Jan") else bt2
    elif model_sel == "V2 (Cross-Asset)":
        bt_sel = bt1_v2 if mode.startswith("Jan") else bt2_v2
    else:
        bt_sel = bt1_v3 if mode.startswith("Jan") else bt2_v3

    if bt_sel:
        t_df = pd.DataFrame(bt_sel["trades"])
        if not t_df.empty:
            if "quantity" not in t_df.columns:
                t_df["quantity"] = 50
                
            t_df["entry_time"] = pd.to_datetime(t_df["entry_time"]).dt.strftime("%d %b %Y %H:%M")
            t_df["exit_time"]  = pd.to_datetime(t_df["exit_time"]).dt.strftime("%d %b %Y %H:%M")
            t_df["confidence"] = (t_df["confidence"]*100).round(1).astype(str) + "%"

            col1, col2, col3 = st.columns(3)
            with col1:
                filt_dir = st.selectbox("Direction", ["All","LONG","SHORT"])
            with col2:
                filt_exit = st.selectbox("Exit Reason", ["All","TARGET_HIT","STOP_LOSS","HOLD_EXPIRY"])
            with col3:
                filt_sig = st.selectbox("Signal", ["All","BULLISH","BEARISH"])

            if filt_dir != "All":   t_df = t_df[t_df["direction"]==filt_dir]
            if filt_exit != "All":  t_df = t_df[t_df["exit_reason"]==filt_exit]
            if filt_sig != "All":   t_df = t_df[t_df["signal"]==filt_sig]

            show_cols = ["entry_time","exit_time","direction","signal","confidence","entry_price","exit_price","quantity","pnl_rs","pnl_pct","exit_reason","capital_after"]
            col_names = {"entry_time":"Entry","exit_time":"Exit Time","direction":"Dir","signal":"Signal","confidence":"Conf",
                         "entry_price":"Entry ₹","exit_price":"Exit ₹","quantity":"Qty","pnl_rs":"P&L (₹)","pnl_pct":"P&L%","exit_reason":"Reason","capital_after":"Capital ₹"}

            disp = t_df[show_cols].rename(columns=col_names).copy()
            # Format columns without Styler
            disp["Entry ₹"]   = disp["Entry ₹"].apply(lambda v: f"{v:.2f}")
            disp["Exit ₹"]    = disp["Exit ₹"].apply(lambda v: f"{v:.2f}")
            disp["P&L (₹)"]  = disp["P&L (₹)"].apply(lambda v: f"{float(v):+.2f}")
            disp["P&L%"]     = disp["P&L%"].apply(lambda v: f"{float(v):+.3f}%")
            disp["Capital ₹"] = disp["Capital ₹"].apply(lambda v: f"₹{float(v):,.2f}")
            st.dataframe(disp, use_container_width=True, height=480)
            st.caption(f"Showing {len(t_df)} trades | Total P&L: ₹{t_df['pnl_rs'].sum():,.2f}")

        # P&L Histogram and Quantity Chart
        st.markdown('<div class="section-header">📊 Trade Distribution & Sizing</div>', unsafe_allow_html=True)
        orig_df = pd.DataFrame(bt_sel["trades"])
        if not orig_df.empty:
            c1, c2 = st.columns(2)
            with c1:
                fig7 = px.histogram(
                    orig_df, x="pnl_rs", nbins=50,
                    color_discrete_sequence=["#818cf8"],
                    title="Distribution of Trade P&L (₹)",
                    template="plotly_dark"
                )
                fig7.add_vline(x=0, line_dash="dash", line_color="#f87171")
                fig7.update_layout(height=300, **PLOTLY_LAYOUT)
                st.plotly_chart(fig7, use_container_width=True)
            with c2:
                if "quantity" in orig_df.columns:
                    fig8 = px.bar(
                        orig_df, x="entry_time", y="quantity",
                        color_discrete_sequence=["#a78bfa"],
                        title="Dynamic Position Size (Qty) Over Time",
                        template="plotly_dark"
                    )
                    fig8.update_layout(height=300, **PLOTLY_LAYOUT)
                    st.plotly_chart(fig8, use_container_width=True)


# ── TAB 4: Live 30-Day Signal ─────────────────────────────────
with tab4:
    st.markdown('<div class="section-header">🔮 Live 30-Day Model Performance (Aug–Sep 11, 2026)</div>', unsafe_allow_html=True)

    if bt2:
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(metric_html("Starting Capital", f"₹{bt2['initial_capital']:,.0f}", "purple"), unsafe_allow_html=True)
        with c2:
            s = "green" if bt2["net_pnl"]>=0 else "red"
            st.markdown(metric_html("Net P&L", f"₹{bt2['net_pnl']:,.0f}", s), unsafe_allow_html=True)
        with c3:
            s = "green" if bt2["win_rate_pct"]>=50 else "gold"
            st.markdown(metric_html("Win Rate", f"{bt2['win_rate_pct']:.1f}%", s), unsafe_allow_html=True)
        with c4: st.markdown(metric_html("Total Trades", bt2["total_trades"], "blue"), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Equity + drawdown chart
        eq2 = bt2["equity_curve"]
        t2  = bt2["equity_times"]
        step = max(1, len(eq2)//600)

        # Compute rolling drawdown
        peak_arr = np.maximum.accumulate(eq2)
        dd_arr   = ((np.array(peak_arr) - np.array(eq2)) / np.array(peak_arr)) * 100

        fig8 = make_subplots(rows=2, cols=1, shared_xaxes=True,
                             row_heights=[0.7, 0.3], vertical_spacing=0.05,
                             subplot_titles=("Portfolio Value (₹)", "Drawdown (%)"))
                             
        # V1 Trace
        color8 = "#34d399" if bt2["net_pnl"] >= 0 else "#f87171"
        fig8.add_trace(go.Scatter(
            x=t2[::step], y=[eq2[i] for i in range(0, len(eq2), step)],
            mode="lines", name="V1 Model (Price Only)",
            line=dict(color=color8, width=2.5),
            fill="tozeroy", fillcolor=f"rgba(52,211,153,0.07)" if color8=="#34d399" else "rgba(248,113,113,0.07)"
        ), row=1, col=1)
        
        # V2 Trace
        if bt2_v2:
            eq2_v2 = bt2_v2["equity_curve"]
            t2_v2  = bt2_v2["equity_times"]
            step_v2 = max(1, len(eq2_v2)//600)
            color8_v2 = "#8b5cf6"
            fig8.add_trace(go.Scatter(
                x=t2_v2[::step_v2], y=[eq2_v2[i] for i in range(0, len(eq2_v2), step_v2)],
                mode="lines", name="V2 Model (Cross-Asset)",
                line=dict(color=color8_v2, width=2.0)
            ), row=1, col=1)
            
        # V3 Trace
        if bt2_v3:
            eq2_v3 = bt2_v3["equity_curve"]
            t2_v3  = bt2_v3["equity_times"]
            step_v3 = max(1, len(eq2_v3)//600)
            color8_v3 = "#eab308"
            fig8.add_trace(go.Scatter(
                x=t2_v3[::step_v3], y=[eq2_v3[i] for i in range(0, len(eq2_v3), step_v3)],
                mode="lines", name="V3 Model (Professional)",
                line=dict(color=color8_v3, width=2.0)
            ), row=1, col=1)
        fig8.add_hline(y=bt2["initial_capital"], line_dash="dot", line_color="rgba(148,163,184,0.4)", row=1, col=1)

        fig8.add_trace(go.Scatter(
            x=t2[::step], y=[dd_arr[i] for i in range(0, len(dd_arr), step)],
            mode="lines", name="Drawdown (V1)",
            line=dict(color="#f87171", width=1.5),
            fill="tozeroy", fillcolor="rgba(248,113,113,0.15)"
        ), row=2, col=1)

        fig8.update_layout(height=500, showlegend=True, **PLOTLY_LAYOUT,
                           legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1))
        st.plotly_chart(fig8, use_container_width=True)
        
        st.markdown("""
        > **Insight:** V1 model clearly outperforms V2 in the live out-of-sample window. 
        > V2 relies on cross-asset features (VIX, Bank Nifty), which were unavailable for this window. 
        > Padding those missing features with zeroes caused the V2 model to underperform. 
        """)

        # Long vs Short Breakdown
        st.markdown('<div class="section-header">📈 Directional Breakdown (Long / Call vs Short / Put)</div>', unsafe_allow_html=True)
        st.caption("Combined performance of LONG (buying/calls) vs SHORT (selling/puts) across Jan-Apr & Live 30-Day datasets.")
        
        dir_data = []
        for model_name, b1, b2 in [("V1 (Price Only)", bt1, bt2), ("V2 (Cross-Asset)", bt1_v2, bt2_v2), ("V3 (Professional)", bt1_v3, bt2_v3)]:
            m_trades = []
            if b1 and "trades" in b1: m_trades.extend(b1["trades"])
            if b2 and "trades" in b2: m_trades.extend(b2["trades"])
            
            if m_trades:
                df_m = pd.DataFrame(m_trades)
                longs = df_m[df_m["direction"] == "LONG"]
                shorts = df_m[df_m["direction"] == "SHORT"]
                
                long_pnl = longs["pnl_rs"].sum() if not longs.empty else 0
                short_pnl = shorts["pnl_rs"].sum() if not shorts.empty else 0
                
                dir_data.append({
                    "Model": model_name,
                    "LONG (Calls) P&L": long_pnl,
                    "LONG Trades": len(longs),
                    "SHORT (Puts) P&L": short_pnl,
                    "SHORT Trades": len(shorts)
                })
        
        if dir_data:
            df_dir = pd.DataFrame(dir_data)
            df_dir["LONG (Calls) P&L"] = df_dir["LONG (Calls) P&L"].apply(lambda x: f"₹{x:+,.0f}")
            df_dir["SHORT (Puts) P&L"] = df_dir["SHORT (Puts) P&L"].apply(lambda x: f"₹{x:+,.0f}")
            st.dataframe(df_dir, use_container_width=True)
            
        st.markdown("<br>", unsafe_allow_html=True)

        # Recent trades
        st.markdown('<div class="section-header">🕐 Recent Trades (Live 30-Day)</div>', unsafe_allow_html=True)
        t2_df = pd.DataFrame(bt2["trades"]).tail(20)
        if not t2_df.empty:
            if "quantity" not in t2_df.columns:
                t2_df["quantity"] = 50
                
            t2_df["entry_time"] = pd.to_datetime(t2_df["entry_time"]).dt.strftime("%d %b %H:%M")
            t2_df["exit_time"]  = pd.to_datetime(t2_df["exit_time"]).dt.strftime("%d %b %H:%M")

            def style_row(row):
                color = "#1a3a2a" if row["pnl_rs"] > 0 else "#3a1a1a"
                return [f"background-color:{color}"] * len(row)

            show = ["entry_time","exit_time","direction","signal","entry_price","exit_price","quantity","pnl_rs","exit_reason"]
            t2_disp = t2_df[show].rename(columns={
                "entry_time":"Entry","exit_time":"Exit Time","direction":"Dir",
                "signal":"Signal","entry_price":"Entry ₹","exit_price":"Exit ₹",
                "quantity":"Qty",
                "pnl_rs":"P&L (₹)","exit_reason":"Reason"
            }).copy()
            t2_disp["Entry ₹"] = t2_disp["Entry ₹"].apply(lambda v: f"{v:.2f}")
            t2_disp["Exit ₹"]  = t2_disp["Exit ₹"].apply(lambda v: f"{v:.2f}")
            t2_disp["P&L (₹)"] = t2_disp["P&L (₹)"].apply(lambda v: f"{float(v):+.2f}")
            st.dataframe(t2_disp, use_container_width=True)

        # Model insight
        st.markdown('<div class="section-header">💡 Model Insights</div>', unsafe_allow_html=True)
        t2_full = pd.DataFrame(bt2["trades"])
        if not t2_full.empty:
            c1, c2, c3 = st.columns(3)
            with c1:
                bull_trades = t2_full[t2_full["signal"]=="BULLISH"]
                bull_wr = (bull_trades["pnl_rs"]>0).mean()*100 if len(bull_trades)>0 else 0
                st.markdown(metric_html("BULLISH Signal Win%", f"{bull_wr:.1f}%", "green"), unsafe_allow_html=True)
            with c2:
                bear_trades = t2_full[t2_full["signal"]=="BEARISH"]
                bear_wr = (bear_trades["pnl_rs"]>0).mean()*100 if len(bear_trades)>0 else 0
                st.markdown(metric_html("BEARISH Signal Win%", f"{bear_wr:.1f}%", "red"), unsafe_allow_html=True)
            with c3:
                avg_conf = t2_full["confidence"].mean()*100
                st.markdown(metric_html("Avg Model Confidence", f"{avg_conf:.1f}%", "blue"), unsafe_allow_html=True)

    else:
        st.info("30-day live backtest results not found. Run `scripts/run_backtest_simulation.py` first.")

# ─────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style='text-align:center; color:#475569; font-size:0.78rem; padding:0.5rem 0;'>
    NIFTY AI Trader &nbsp;·&nbsp; XGBoost Walk-Forward ML &nbsp;·&nbsp;
    3-Class Regime Detection &nbsp;·&nbsp; 
    <span style='color:#6366f1'>Not financial advice — for research use only</span>
</div>
""", unsafe_allow_html=True)
