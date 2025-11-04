# data_worker/live_cacher.py
import os
import json
import time
import redis
import pandas as pd
from backend.crud import fetch_latest_n_candles
from backend.core.analytics import hedge_ratio_ols, compute_spread, compute_zscore, rolling_corr
from datetime import datetime

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_CHANNEL = os.getenv("REDIS_CHANNEL", "live_analytics")
PUBLISH_INTERVAL = float(os.getenv("PUBLISH_INTERVAL", "1.0"))  # seconds
ROLLING_WINDOW = int(os.getenv("ROLLING_WINDOW", "60"))

# sync redis client (simple)
r = redis.from_url(REDIS_URL)

def rows_to_series(rows):
    # rows: list of OHLCV1m ORM rows from crud.fetch_latest_n_candles
    if not rows:
        return pd.Series(dtype=float)
    idx = [r.ts for r in rows]
    close = [r.close for r in rows]
    return pd.Series(close, index=pd.to_datetime(idx))

def build_payload(symbol_y, symbol_x):
    # fetch last N candles for both symbols
    rows_y = fetch_latest_n_candles(symbol_y, n=ROLLING_WINDOW+10)
    rows_x = fetch_latest_n_candles(symbol_x, n=ROLLING_WINDOW+10)
    s_y = rows_to_series(rows_y)
    s_x = rows_to_series(rows_x)
    payload = {"symbol_y": symbol_y, "symbol_x": symbol_x, "ts": datetime.utcnow().isoformat()}
    if len(s_y) < 10 or len(s_x) < 10:
        payload.update({"status": "insufficient_data"})
        return payload
    # align
    df = pd.concat([s_y.rename("y"), s_x.rename("x")], axis=1).dropna()
    if df.empty:
        payload.update({"status": "insufficient_align"})
        return payload
    # compute hedge ratio on last ROLLING_WINDOW
    y = df['y'].iloc[-ROLLING_WINDOW:]
    x = df['x'].iloc[-ROLLING_WINDOW:]
    hr = hedge_ratio_ols(y, x)
    spread = compute_spread(df['y'], df['x'], hr)
    z = compute_zscore(spread, window=min(ROLLING_WINDOW, max(5, int(len(spread)/2))))
    z_latest = None
    try:
        z_latest = None if z.dropna().empty else float(z.iloc[-1])
    except Exception:
        z_latest = None
    corr_series = rolling_corr(df['y'], df['x'], window=min(ROLLING_WINDOW, len(df)))
    corr_latest = None if corr_series.dropna().empty else float(corr_series.iloc[-1])
    payload.update({
        "hedge_ratio": None if hr is None else float(hr),
        "zscore": z_latest,
        "spread": None if spread.empty else float(spread.iloc[-1]),
        "rolling_corr": corr_latest,
        "status": "ok",
    })
    return payload

def publisher_loop(pairs):
    """pairs: list of (symbol_y, symbol_x) e.g. [('btcusdt','ethusdt')]"""
    while True:
        for (y, x) in pairs:
            try:
                p = build_payload(y, x)
                r.publish(REDIS_CHANNEL, json.dumps(p))
            except Exception as e:
                print("publish error", e)
        time.sleep(PUBLISH_INTERVAL)

if __name__ == "__main__":
    # example: environment variable PAIRS="btcusdt:ethusdt,linkusdt:ethusdt"
    pairs_env = os.getenv("PAIRS", "btcusdt:ethusdt")
    pairs = []
    for part in pairs_env.split(","):
        if ":" in part:
            a,b = part.split(":")
            pairs.append((a.strip().lower(), b.strip().lower()))
    print("starting live_cacher for pairs:", pairs)
    publisher_loop(pairs)
