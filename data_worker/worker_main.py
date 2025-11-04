# data_worker/worker_main.py
import asyncio
from data_worker.ingestion_stream import subscribe_symbols
from dotenv import load_dotenv
import os

load_dotenv()

def main():
    # symbols to collect - change as desired
    symbols = os.getenv("SYMBOLS", "BTCUSDT,ETHUSDT").split(",")
    symbols = [s.strip() for s in symbols if s.strip()]
    loop = asyncio.get_event_loop()
    loop.run_until_complete(subscribe_symbols(symbols))

if __name__ == "__main__":
    main()