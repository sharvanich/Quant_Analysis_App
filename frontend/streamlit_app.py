import streamlit as st
import pandas as pd
import numpy as np
import time
import random
import datetime
import plotly.graph_objs as go

st.set_page_config(page_title="Quant Analytics App", layout="wide")

# --- Sidebar Controls ---
st.sidebar.header("Controls")
symbol = st.sidebar.text_input("Symbol (lowercase)", "btcusdt")
timeframe = st.sidebar.selectbox("Timeframe (resample)", ["1m", "5m", "15m"])
rolling_window = st.sidebar.number_input("Rolling window (bars) for z-score", value=60, step=1)
st.sidebar.button("Load Historical Data")

# --- Header ---
st.markdown("## Quant Analytics App — Live Dashboard")
st.markdown(f"### {symbol.upper()} — Combined Chart ({timeframe})")

# --- Placeholders ---
chart_placeholder = st.empty()
metric_cols = st.columns(4)

# --- Initialize dummy data lists ---
timestamps, prices, spreads, zscores, corrs = [], [], [], [], []

# --- Dummy live update loop ---
for i in range(50):
    # Generate dummy live data
    now = datetime.datetime.now()
    price = 60000 + random.uniform(-500, 500)
    spread = random.uniform(-10, 10)
    zscore = random.uniform(-2, 2)
    corr = random.uniform(0.7, 1.0)

    timestamps.append(now)
    prices.append(price)
    spreads.append(spread)
    zscores.append(zscore)
    corrs.append(corr)

    # --- Update metrics compactly in one row ---
    metric_cols[0].metric("Live Z-score", f"{zscore:.2f}")
    metric_cols[1].metric("Spread", f"{spread:.2f}")
    metric_cols[2].metric("Last Price", f"{price:.2f}")
    metric_cols[3].metric("Rolling Corr", f"{corr:.2f}")

    # --- Create one combined chart ---
    fig = go.Figure()

    # Price (primary y-axis)
    fig.add_trace(go.Scatter(
        x=timestamps, y=prices, mode="lines+markers", name="Price",
        line=dict(color="#00BFFF", width=2)
    ))

    # Spread (secondary y-axis)
    fig.add_trace(go.Scatter(
        x=timestamps, y=spreads, mode="lines", name="Spread",
        line=dict(color="#FFA500", width=1.5, dash="dot"), yaxis="y2"
    ))

    # Z-score (secondary y-axis)
    fig.add_trace(go.Scatter(
        x=timestamps, y=zscores, mode="lines", name="Z-score",
        line=dict(color="#FF4B4B", width=1.5), yaxis="y2"
    ))

    fig.update_layout(
        height=500,
        margin=dict(l=40, r=40, t=40, b=40),
        template="plotly_dark",
        xaxis=dict(title="Time", showgrid=False),
        yaxis=dict(title="Price", side="left", showgrid=False),
        yaxis2=dict(title="Spread / Z-score", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )

    chart_placeholder.plotly_chart(fig, use_container_width=True)
    time.sleep(1)
