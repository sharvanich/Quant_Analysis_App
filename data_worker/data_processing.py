# data_worker/data_processing.py
"""
Handles tick-to-OHLCV resampling and persistence logic.
Now uses new Pandas frequency codes ('min', 's') to avoid deprecation warnings.
"""

from backend.database import SessionLocal, TickData, OHLCV1m
import pandas as pd
from datetime import datetime, timedelta


def ticks_to_ohlcv(symbol: str, freq: str = '1min', minutes: int = 60):
    """
    Convert raw tick data from MySQL into OHLCV format for a given symbol.
    
    Args:
        symbol (str): trading pair, e.g. 'btcusdt'
        freq (str): resampling frequency ('1min', '5min', '1s', etc.)
        minutes (int): how many minutes of recent data to pull
    
    Returns:
        pd.DataFrame: OHLCV dataframe
    """
    session = SessionLocal()
    try:
        since = datetime.utcnow() - timedelta(minutes=minutes)
        rows = (
            session.query(TickData)
            .filter(TickData.symbol == symbol.lower(), TickData.ts >= since)
            .order_by(TickData.ts)
            .all()
        )
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame([{"ts": r.ts, "price": r.price, "size": r.size} for r in rows])
        df.set_index(pd.DatetimeIndex(df['ts']), inplace=True)

        # Ensure backward-compatible frequency naming
        # Replace deprecated aliases: 'T' → 'min', 'S' → 's'
        freq = freq.replace('T', 'min').replace('S', 's')

        # Resample into OHLCV
        ohlc = df['price'].resample(freq).ohlc()
        vol = df['size'].resample(freq).sum().rename('volume')
        out = ohlc.join(vol)
        out = out.dropna(subset=['open'])
        out.reset_index(inplace=True)
        return out

    finally:
        session.close()


def persist_1m_ohlcv(symbol: str, minutes: int = 60):
    """
    Compute 1-minute OHLCV candles and persist them into MySQL.
    Skips duplicates if candles already exist.
    
    Args:
        symbol (str): e.g. 'btcusdt'
        minutes (int): how far back to aggregate
    Returns:
        int: number of new rows inserted
    """
    df = ticks_to_ohlcv(symbol, freq='1min', minutes=minutes)
    if df.empty:
        return 0

    session = SessionLocal()
    count = 0
    try:
        for _, row in df.iterrows():
            ts = row['ts'].to_pydatetime()
            exists = (
                session.query(OHLCV1m)
                .filter(OHLCV1m.symbol == symbol, OHLCV1m.ts == ts)
                .first()
            )
            if exists:
                continue

            rec = OHLCV1m(
                symbol=symbol,
                ts=ts,
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=float(row['volume']) if not pd.isna(row['volume']) else 0.0,
            )
            session.add(rec)
            count += 1

        session.commit()
        return count

    except Exception as e:
        session.rollback()
        print(f"[persist_1m_ohlcv] Error: {e}")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    # Quick test run (optional)
    df_test = ticks_to_ohlcv("btcusdt", freq="1min", minutes=5)
    print(df_test.tail())
