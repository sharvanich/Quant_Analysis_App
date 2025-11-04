# frontend/streamlit_app.py
import streamlit as st
import requests
import pandas as pd
import threading
import time
import json
import queue
from datetime import datetime
from websocket import WebSocketApp
import plotly.graph_objects as go
import plotly.express as px
import io

# CONFIG
API_BASE = st.secrets.get("API_BASE", "http://127.0.0.1:8000")
WS_BASE = st.secrets.get("WS_BASE", "ws://127.0.0.1:8000/api/v1/ws/live")
DEFAULT_SYMBOL = "btcusdt"

# session state initialization
if "live_queue" not in st.session_state:
    st.session_state.live_queue = queue.Queue()
if "ws_thread_started" not in st.session_state:
    st.session_state.ws_thread_started = False
if "live_metrics" not in st.session_state:
    st.session_state.live_metrics = {}
if "historical_df" not in st.session_state:
    st.session_state.historical_df = None
if "ws" not in st.session_state:
    st.session_state.ws = None

st.set_page_config(page_title="Quant Analytics — Live", layout="wide")

st.title("Quant Analytics App — Live Dashboard")

# --- Sidebar controls ---
with st.sidebar:
    st.header("Controls")
    symbol = st.text_input("Symbol (lowercase)", value=DEFAULT_SYMBOL)
    timeframe = st.selectbox("Timeframe (resample)", ["1m", "5m", "1s"], index=0)
    rolling_window = st.number_input("Rolling window (bars) for z-score", min_value=5, max_value=1000, value=60)
    fetch_hist = st.button("Load Historical Data")

# Helper: fetch historical data from backend
def fetch_historical(symbol: str, timeframe: str, limit: int = 500):
    url = f"{API_BASE}/api/v1/data/history/{symbol}/{timeframe}?limit={limit}"
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        data = r.json()
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        # assume ts is ISO timestamp or unix; try to parse
        if 'ts' in df.columns:
            df['ts'] = pd.to_datetime(df['ts'])
        elif 'timestamp' in df.columns:
            df['ts'] = pd.to_datetime(df['timestamp'])
        else:
            # try index->time
            df['ts'] = pd.to_datetime(df.get('time', pd.Series()))
        # ensure numeric types
        for c in ['open', 'high', 'low', 'close', 'volume']:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.sort_values('ts').reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"Failed to load historical data: {e}")
        return pd.DataFrame()

# Plotting helpers
def plot_ohlcv(df: pd.DataFrame):
    if df.empty:
        st.write("No historical OHLCV to display.")
        return None
    fig = go.Figure(data=[go.Candlestick(x=df['ts'],
                                         open=df['open'],
                                         high=df['high'],
                                         low=df['low'],
                                         close=df['close'],
                                         name="Price")])
    fig.update_layout(margin=dict(l=10, r=10, t=30, b=20), height=450, showlegend=False)
    return fig

def plot_spread_zscore(df: pd.DataFrame, spread_col='spread', z_col='zscore'):
    fig = go.Figure()
    if spread_col in df.columns:
        fig.add_trace(go.Scatter(x=df['ts'], y=df[spread_col], name='Spread', mode='lines'))
    if z_col in df.columns:
        fig.add_trace(go.Scatter(x=df['ts'], y=df[z_col], name='Z-score', mode='lines', yaxis='y2'))
        # add second y axis
        fig.update_layout(
            yaxis=dict(title="Spread"),
            yaxis2=dict(title="Z-score", overlaying='y', side='right', showgrid=False),
            height=350,
            margin=dict(l=10, r=10, t=20, b=20)
        )
    else:
        fig.update_layout(height=350, margin=dict(l=10, r=10, t=20, b=20))
    return fig

# Download helper
def df_to_csv_bytes(df: pd.DataFrame):
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode('utf-8')

# WebSocket receiver thread
def start_ws_thread(ws_url, live_q: queue.Queue, symbol_sub=None):
    def on_message(ws, message):
        try:
            obj = json.loads(message)
            # optionally filter by symbol
            if symbol_sub and obj.get("symbol") != symbol_sub:
                return
            live_q.put(obj)
        except Exception as e:
            # push a small error object — handled client-side
            live_q.put({"_error": str(e), "raw": message})

    def on_error(ws, error):
        live_q.put({"_error": f"ws_error: {error}"})

    def on_close(ws, close_status_code, close_msg):
        live_q.put({"_info": f"ws_closed code={close_status_code} msg={close_msg}"})

    def on_open(ws):
        live_q.put({"_info": "ws_opened"})

    # create WebSocketApp (websocket-client)
    ws_app = WebSocketApp(ws_url,
                          on_open=on_open,
                          on_message=on_message,
                          on_error=on_error,
                          on_close=on_close)

    # run in thread
    def run():
        # Reconnect loop
        while True:
            try:
                ws_app.run_forever()
            except Exception as e:
                live_q.put({"_error": f"run_forever_failed: {e}"})
            time.sleep(2)  # backoff before reconnect

    t = threading.Thread(target=run, daemon=True, name="ws_thread")
    t.start()
    return ws_app, t

# Start WS thread only once
if not st.session_state.ws_thread_started:
    st.session_state.ws_app, st.session_state.ws_thread = start_ws_thread(WS_BASE, st.session_state.live_queue, symbol_sub=None)
    st.session_state.ws_thread_started = True
    st.success("WebSocket listener started (background)")

# If user clicked to fetch historical data
if fetch_hist or st.session_state.historical_df is None:
    with st.spinner("Loading historical data..."):
        df_hist = fetch_historical(symbol, timeframe, limit=1000)
        st.session_state.historical_df = df_hist

# Layout: top metrics + charts
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"{symbol.upper()} — Price Chart ({timeframe})")
    fig_candle = plot_ohlcv(st.session_state.historical_df if st.session_state.historical_df is not None else pd.DataFrame())
    if fig_candle:
        st.plotly_chart(fig_candle, use_container_width=True)

    st.markdown("### Spread & Z-score")
    # try to compute spread & zscore locally if not provided in historical df
    df_local = st.session_state.historical_df.copy() if st.session_state.historical_df is not None else pd.DataFrame()
    # if no spread column, try to compute a naive spread using close-close diff (placeholder)
    if not df_local.empty and 'spread' not in df_local.columns:
        df_local['spread'] = df_local['close'].diff().fillna(0)
    if not df_local.empty and 'zscore' not in df_local.columns:
        df_local['zscore'] = (df_local['spread'] - df_local['spread'].rolling(rolling_window).mean()) / (df_local['spread'].rolling(rolling_window).std().replace(0, 1))
    fig_spread = plot_spread_zscore(df_local, spread_col='spread', z_col='zscore')
    if fig_spread:
        st.plotly_chart(fig_spread, use_container_width=True)

    # CSV download
    if not df_local.empty:
        csv_bytes = df_to_csv_bytes(df_local)
        st.download_button("Download displayed data (CSV)", data=csv_bytes, file_name=f"{symbol}_{timeframe}_data.csv", mime="text/csv")

with col2:
    st.subheader("Live Metrics")
    # placeholders for live metrics
    zcard = st.empty()
    spread_card = st.empty()
    price_card = st.empty()
    corr_card = st.empty()
    last_update = st.empty()

    # process items from live queue
    # drain queue
    processed = 0
    while not st.session_state.live_queue.empty():
        try:
            obj = st.session_state.live_queue.get_nowait()
        except queue.Empty:
            break
        processed += 1
        # handle meta messages
        if '_error' in obj:
            st.error(f"WS Error: {obj.get('_error')}")
            continue
        if '_info' in obj:
            # show small info
            last_update.info(obj.get('_info'))
            continue

        # expected structure: {"symbol":"btcusdt","zscore":-0.43,"spread":12.8,"corr":0.91,"price":123.45,"ts":"2025-11-03T08:35:11Z"}
        # update session_state live metrics
        sym = obj.get("symbol")
        st.session_state.live_metrics = obj
        st.session_state.live_metrics["_received_at"] = datetime.utcnow().isoformat()

    # display live metrics
    lm = st.session_state.live_metrics or {}
    price_card.metric("Last Price", value=f"{lm.get('price','-')}", delta=None)
    zcard.metric("Live Z-score", value=f"{lm.get('zscore','-')}", delta=None)
    spread_card.metric("Spread", value=f"{lm.get('spread','-')}", delta=None)
    corr_card.metric("Rolling Corr", value=f"{lm.get('corr','-')}", delta=None)
    if lm.get("_received_at"):
        last_update.write(f"Last tick: {lm.get('_received_at')}")
    else:
        last_update.write("No live ticks received yet.")

st.markdown("---")
st.caption("Note: This Streamlit frontend connects to the FastAPI backend for historical data and a WebSocket endpoint for live analytics. Make sure the FastAPI server is running (uvicorn backend.main:app --reload).")
