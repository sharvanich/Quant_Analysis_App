# backend/main.py
import os
import asyncio
import json
import uvicorn
import redis.asyncio as aioredis
from fastapi import FastAPI

# Internal imports
from backend.database import create_tables  # replaces old init_db()
from backend.api.historical_data import router as hist_router
from backend.api.real_time import router as rt_router
from backend.core.websocket_manager import ws_manager 
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------
# Redis Config
# ---------------------------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_CHANNEL = os.getenv("REDIS_CHANNEL", "live_analytics")

# ---------------------------------------------------------------------
# FastAPI App Setup
# ---------------------------------------------------------------------
app = FastAPI(title="Quant Analytics API", version="1.0.0")

origins = [
    "http://localhost:8501",
    "http://127.0.0.1:8501",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(hist_router)
app.include_router(rt_router)

# ---------------------------------------------------------------------
# Startup and Shutdown Events
# ---------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    """Runs when FastAPI starts."""
    # ✅ Ensure DB tables exist
    create_tables()

    # ✅ Connect to Redis and start the subscriber task
    app.state.redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    app.state._redis_task = asyncio.create_task(_redis_listener(app.state.redis))
    print(f"🚀 FastAPI started with Redis listener on {REDIS_CHANNEL}")

@app.on_event("shutdown")
async def shutdown_event():
    """Graceful shutdown: stop Redis listener and close connections."""
    task = getattr(app.state, "_redis_task", None)
    if task:
        task.cancel()

    redis_client = getattr(app.state, "redis", None)
    if redis_client:
        await redis_client.close()
        print("🧹 Redis connection closed.")

# ---------------------------------------------------------------------
# Redis Pub/Sub Listener
# ---------------------------------------------------------------------
async def _redis_listener(redis_client):
    """
    Listen for JSON messages on REDIS_CHANNEL and broadcast them
    to all connected WebSocket clients.
    """
    pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
    await pubsub.subscribe(REDIS_CHANNEL)
    print(f"📡 Subscribed to Redis channel: {REDIS_CHANNEL}")

    try:
        async for message in pubsub.listen():
            # Example: {'type':'message','pattern':None,'channel':'live_analytics','data':'{"symbol":"BTCUSDT",...}'}
            if message is None or message.get("type") != "message":
                continue

            data = message.get("data")
            if not data:
                continue

            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                print("⚠️ Invalid JSON in Redis message.")
                continue

            # Broadcast to all active WebSocket clients
            await ws_manager.broadcast_json(payload)

    except asyncio.CancelledError:
        await pubsub.unsubscribe(REDIS_CHANNEL)
        print("🛑 Redis listener task cancelled.")
    except Exception as e:
        print(f"❌ Redis listener error: {e}")
        try:
            await pubsub.unsubscribe(REDIS_CHANNEL)
        except Exception:
            pass

# ---------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True
    )