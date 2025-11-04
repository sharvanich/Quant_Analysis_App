# backend/schemas.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# --------------------------
# TickData Response Schema
# --------------------------
class TickDataSchema(BaseModel):
    id: int
    symbol: str
    ts: datetime
    price: float
    size: Optional[float]

    class Config:
        orm_mode = True


# --------------------------
# OHLCV Response Schema
# --------------------------
class OHLCVSchema(BaseModel):
    id: int
    symbol: str
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    class Config:
        orm_mode = True


# --------------------------
# Analytics Cache Schema
# --------------------------
class AnalyticsCacheSchema(BaseModel):
    id: int
    symbol: str
    payload: str
    updated_at: datetime

    class Config:
        orm_mode = True


# --------------------------
# Live Analytics (WS payload)
# --------------------------
class LiveAnalytics(BaseModel):
    symbol: str
    price: Optional[float]
    zscore: Optional[float]
    spread: Optional[float]
    corr: Optional[float] = Field(None, alias="rolling_corr")
    ts: Optional[datetime] = None
