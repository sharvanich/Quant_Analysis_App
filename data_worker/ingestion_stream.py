import asyncio
import json
import datetime
import logging
import websockets
import pymysql
from backend.config import get_settings

# ---------------------------------------------------------------------
# Load configuration
# ---------------------------------------------------------------------
settings = get_settings()

# ---------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# ---------------------------------------------------------------------
# Database connection helper
# ---------------------------------------------------------------------
def get_db_connection():
    """Create a new MySQL connection using settings from .env"""
    return pymysql.connect(
        host=settings.MYSQL_HOST,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        database=settings.MYSQL_DB,
        autocommit=True
    )

# ---------------------------------------------------------------------
# Normalize Binance trade message
# ---------------------------------------------------------------------
def normalize_trade(trade: dict) -> dict:
    """Convert Binance trade JSON to normalized dictionary."""
    ts = datetime.datetime.utcfromtimestamp(trade["T"] / 1000.0)
    return {
        "symbol": trade["s"].lower(),
        "ts": ts,
        "price": float(trade["p"]),
        "size": float(trade["q"]),
    }

# ---------------------------------------------------------------------
# Insert tick data into DB
# ---------------------------------------------------------------------
def insert_tick(conn, data: dict):
    """Insert tick into tickdata table."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tickdata (symbol, ts, price, size) VALUES (%s, %s, %s, %s)",
                (data["symbol"], data["ts"], data["price"], data["size"])
            )
    except Exception as e:
        logging.error(f"MySQL insert failed for {data['symbol']}: {e}")

# ---------------------------------------------------------------------
# Async listener for a single symbol
# ---------------------------------------------------------------------
async def collect_symbol(symbol: str):
    """Connect to Binance WebSocket and continuously insert ticks for a symbol."""
    url = f"wss://fstream.binance.com/ws/{symbol}@trade"
    logging.info(f"Connecting WebSocket for {symbol} -> {url}")

    while True:
        try:
            async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
                conn = get_db_connection()
                logging.info(f"Connected: {symbol}")
                async for msg in ws:
                    try:
                        j = json.loads(msg)
                        if j.get("e") == "trade":
                            tick = normalize_trade(j)
                            insert_tick(conn, tick)
                    except Exception as ex:
                        logging.error(f"Error parsing message for {symbol}: {ex}")
        except Exception as e:
            logging.warning(f"{symbol}: WebSocket disconnected -> {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)
            continue

# ---------------------------------------------------------------------
# Main entry point for multiple symbols
# ---------------------------------------------------------------------
def subscribe_symbols(symbols: list[str]):
    """Subscribe to multiple Binance symbols concurrently."""
    async def runner():
        tasks = [asyncio.create_task(collect_symbol(sym)) for sym in symbols]
        await asyncio.gather(*tasks)

    logging.info(f"Launching collectors for: {', '.join(symbols)}")
    asyncio.run(runner())

# ---------------------------------------------------------------------
# Standalone test mode
# ---------------------------------------------------------------------
if __name__ == "__main__":
    test_symbols = ["btcusdt", "ethusdt"]
    subscribe_symbols(test_symbols)
