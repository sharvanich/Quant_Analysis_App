# backend/api/historical_data.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import OHLCV1m
from backend.schemas import OHLCVSchema
from pydantic import BaseModel
from datetime import datetime, timedelta
from backend.database import SessionLocal
import pandas as pd
from backend.models import TickData
from fastapi import HTTPException

router = APIRouter(prefix="/api/v1/data", tags=["Data"])

@router.get("/history/{symbol}/{timeframe}", response_model=list[OHLCVSchema])
def get_history(symbol: str, timeframe: str, db: Session = Depends(get_db)):
    return db.query(OHLCV1m).filter(OHLCV1m.symbol == symbol).all()


# ---------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------
class OHLCVResponse(BaseModel):
    ts: str
    open: float
    high: float
    low: float
    close: float
    volume: float

# ---------------------------------------------------------------------
# Utility: Query Raw Tick Data
# ---------------------------------------------------------------------
def query_ticks(session: Session, symbol: str, since: datetime):
    """Fetch tick data newer than `since` for a given symbol."""
    q = (
        session.query(TickData)
        .filter(TickData.symbol == symbol.lower(), TickData.ts >= since)
        .order_by(TickData.ts)
    )
    return q.all()

# ---------------------------------------------------------------------
# REST Endpoint: Dynamic Resampling from TickData
# ---------------------------------------------------------------------
@router.get("/history/{symbol}/{timeframe}", response_model=list[OHLCVResponse])
def get_history(symbol: str, timeframe: str = "1m", minutes: int = 60):
    """
    Returns OHLCV data built dynamically from tick data.

    Args:
        symbol: trading pair symbol (e.g., btcusdt)
        timeframe: '1s', '1m', or '5m'
        minutes: how many minutes of history to include
    """
    tf_map = {"1s": "S", "1m": "T", "5m": "5T"}
    if timeframe not in tf_map:
        raise HTTPException(status_code=400, detail="Invalid timeframe (must be 1s, 1m, or 5m)")
    freq = tf_map[timeframe]

    session = SessionLocal()
    try:
        since = datetime.utcnow() - timedelta(minutes=minutes)
        rows = query_ticks(session, symbol, since)
        if not rows:
            return []

        # Build DataFrame from tick data
        df = pd.DataFrame([{"ts": r.ts, "price": r.price, "size": r.size} for r in rows])
        df = df.set_index(pd.DatetimeIndex(df["ts"]))

        # Resample to OHLCV
        ohlc = df["price"].resample(freq).ohlc()
        vol = df["size"].resample(freq).sum().rename("volume")
        merged = ohlc.join(vol)
        merged = merged.dropna(subset=["open"])

        # Convert to list of dicts
        out = []
        for idx, row in merged.iterrows():
            out.append({
                "ts": idx.isoformat(),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"] if not pd.isna(row["volume"]) else 0.0)
            })
        return out
    finally:
        session.close()

# ---------------------------------------------------------------------
# REST Endpoint: Read from Precomputed OHLCV_1m Table (if needed)
# ---------------------------------------------------------------------
@router.get("/history_cached/{symbol}", response_model=list[OHLCVResponse])
def get_cached_history(symbol: str, minutes: int = 60):
    """
    Fetch OHLCV data directly from `ohlcv_1m` table for faster response.
    """
    session = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        rows = (
            session.query(OHLCV1m)
            .filter(OHLCV1m.symbol == symbol.lower(), OHLCV1m.ts >= cutoff)
            .order_by(OHLCV1m.ts)
            .all()
        )
        if not rows:
            return []
        return [
            {
                "ts": r.ts.isoformat(),
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
