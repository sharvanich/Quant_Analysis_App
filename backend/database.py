# backend/database.py
import os
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Index,
    JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------------------
load_dotenv()

MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "rootpass")
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DB = os.getenv("MYSQL_DB", "quantdb")

DB_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@"
    f"{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
)

# ---------------------------------------------------------------------
# SQLAlchemy Engine and Session
# ---------------------------------------------------------------------
engine = create_engine(
    DB_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    future=True
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()

# ---------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------
class TickData(Base):
    __tablename__ = "tickdata"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(64), index=True)
    ts = Column(DateTime, index=True)
    price = Column(Float)
    size = Column(Float)

    def __repr__(self):
        return f"<Tick {self.symbol} {self.ts} {self.price}>"

class OHLCV1m(Base):
    __tablename__ = "ohlcv_1m"
    id = Column(Integer, primary_key=True)
    symbol = Column(String(64), index=True)
    ts = Column(DateTime, index=True)  # minute timestamp (start)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)

    __table_args__ = (Index("ix_ohlcv_symbol_ts", "symbol", "ts"),)

class AnalyticsCache(Base):
    __tablename__ = "analytics_cache"
    id = Column(Integer, primary_key=True)
    key = Column(String(128), unique=True, index=True)
    value = Column(JSON)
    ts = Column(DateTime, default=datetime.utcnow)

# ---------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------
def create_tables():
    """Create all defined tables in MySQL database."""
    Base.metadata.create_all(bind=engine)
    print("✅ All database tables created successfully.")

def get_db():
    """FastAPI dependency: yield a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------
if __name__ == "__main__":
    create_tables()
