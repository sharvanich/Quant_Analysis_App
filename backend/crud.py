# backend/crud.py
from datetime import datetime, timedelta
from sqlalchemy import func
import pandas as pd

from backend.database import SessionLocal
from backend.models import TickData, OHLCV1m, AnalyticsCache


# ---------------------------------------------------------------------
# 📥 Insert OHLCV Data (Bulk)
# ---------------------------------------------------------------------
def insert_ohlcv_bulk(df: pd.DataFrame, symbol: str):
    """
    Insert multiple OHLCV rows for a given symbol.
    df must contain columns: ['ts', 'open', 'high', 'low', 'close', 'volume']
    """
    if df.empty:
        return

    session = SessionLocal()
    try:
        objs = []
        for _, row in df.iterrows():
            ts_val = (
                row["ts"].to_pydatetime()
                if hasattr(row["ts"], "to_pydatetime")
                else row["ts"]
            )
            objs.append(
                OHLCV1m(
                    symbol=symbol,
                    ts=ts_val,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                )
            )

        session.bulk_save_objects(objs)
        session.commit()
        print(f"✅ Inserted {len(objs)} OHLCV rows for {symbol}")
    except Exception as e:
        session.rollback()
        print(f"❌ insert_ohlcv_bulk error: {e}")
    finally:
        session.close()


# ---------------------------------------------------------------------
# 📊 Fetch Recent OHLCV Data
# ---------------------------------------------------------------------
def get_recent_ohlcv(symbol: str, minutes: int = 120):
    """
    Fetch OHLCV candles for the last 'minutes' minutes.
    Returns a list of dicts [{ts, open, high, low, close, volume}, ...]
    """
    session = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        rows = (
            session.query(OHLCV1m)
            .filter(OHLCV1m.symbol == symbol, OHLCV1m.ts >= cutoff)
            .order_by(OHLCV1m.ts)
            .all()
        )
        return [
            {
                "ts": r.ts,
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "volume": r.volume,
            }
            for r in rows
        ]
    finally:
        session.close()


# ---------------------------------------------------------------------
# 📈 Fetch Last N Candles
# ---------------------------------------------------------------------
def fetch_latest_n_candles(symbol: str, n: int = 500):
    """
    Fetch the most recent N candles for a given symbol.
    Returns a list of OHLCV1m ORM objects.
    """
    session = SessionLocal()
    try:
        rows = (
            session.query(OHLCV1m)
            .filter(OHLCV1m.symbol == symbol)
            .order_by(OHLCV1m.ts.desc())
            .limit(n)
            .all()
        )
        return list(reversed(rows))  # Oldest → Newest
    finally:
        session.close()


# ---------------------------------------------------------------------
# 💾 Upsert Analytics Cache
# ---------------------------------------------------------------------
def upsert_analytics_cache(symbol: str, payload_json: str):
    """
    Insert or update the analytics cache for a symbol.
    Uses the AnalyticsCache table (key/value pattern).
    """
    session = SessionLocal()
    try:
        key_name = f"analytics:{symbol}"
        existing = session.query(AnalyticsCache).filter(AnalyticsCache.key == key_name).first()

        if existing:
            existing.value = payload_json
            existing.ts = datetime.utcnow()
        else:
            new_entry = AnalyticsCache(key=key_name, value=payload_json, ts=datetime.utcnow())
            session.add(new_entry)

        session.commit()
        print(f"🧠 Cache updated for {symbol}")
    except Exception as e:
        session.rollback()
        print(f"❌ upsert_analytics_cache error: {e}")
    finally:
        session.close()