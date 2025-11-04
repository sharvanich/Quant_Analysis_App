# backend/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, BigInteger, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class TickData(Base):
    __tablename__ = 'tickdata'
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(32), index=True, nullable=False)
    ts = Column(DateTime, index=True, nullable=False)  # timestamp
    price = Column(Float, nullable=False)
    size = Column(Float, nullable=True)

class OHLCV1m(Base):
    __tablename__ = 'ohlcv_1m'
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(32), index=True, nullable=False)
    ts = Column(DateTime, index=True, nullable=False)  # candle start time
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)

    __table_args__ = (Index('ix_ohlcv_symbol_ts', 'symbol', 'ts'),)

class AnalyticsCache(Base):
    __tablename__ = 'analytics_cache'
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(32), index=True, nullable=False)
    payload = Column(String(2048))  # JSON string of latest metrics
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
