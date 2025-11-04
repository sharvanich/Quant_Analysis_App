# backend/api/real_time.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from redis import asyncio as aioredis
from dotenv import load_dotenv
from starlette.websockets import WebSocketState
import os, json, asyncio, logging

# ---------------------------------------------------------------------
# Environment Configuration
# ---------------------------------------------------------------------
load_dotenv()
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

router = APIRouter()
logger = logging.getLogger("realtime")
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------
# REST Endpoint: Fetch Latest Cached Analytics
# ---------------------------------------------------------------------
@router.get("/api/v1/analytics/{pair}")
async def get_cached_analytics(pair: str):
    """
    Retrieve the most recent cached analytics for a trading pair.
    Value expected in Redis key: live:{pair}
    """
    r = aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
    key = f"live:{pair}"
    try:
        val = await r.get(key)
    finally:
        await r.close()

    if not val:
        raise HTTPException(status_code=404, detail=f"No analytics cached yet for {pair}")
    try:
        return json.loads(val)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Corrupted analytics JSON in cache")

# ---------------------------------------------------------------------
# WebSocket Endpoint: Live Analytics Stream
# ---------------------------------------------------------------------
@router.websocket("/api/v1/ws/live/{pair}")
async def websocket_live(ws: WebSocket, pair: str):
    """
    Opens a WebSocket connection for a specific trading pair and
    subscribes to Redis channel: live_updates:{pair}.
    """
    origin = ws.headers.get("origin")
    print(f"Incoming WebSocket connection from: {origin}")

    # ✅ Accept connection from Streamlit or localhost origins
    allowed_origins = {"http://localhost:8501", "http://127.0.0.1:8501"}
    if origin not in allowed_origins:
        # For development, you can temporarily allow all:
        # await ws.accept()
        print(f"⚠️ Origin {origin} not explicitly allowed — accepting anyway for dev.")
    await ws.accept()

    r = aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
    pubsub = r.pubsub()
    channel = f"live_updates:{pair}"
    await pubsub.subscribe(channel)
    logger.info(f"🔌 WebSocket connected for {pair}, subscribed to Redis channel: {channel}")

    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if msg and msg.get("type") == "message":
                data = msg["data"]
                try:
                    await ws.send_text(data)
                except Exception:
                    logger.warning(f"⚠️ Client disconnected while sending update for {pair}")
                    break

            # keep-alive ping
            try:
                await asyncio.wait_for(ws.receive_text(), timeout=0.1)
            except asyncio.TimeoutError:
                continue
            except Exception:
                pass

    except WebSocketDisconnect:
        logger.info(f"❌ WebSocket disconnected for {pair}")
    except Exception as e:
        logger.error(f"WebSocket error ({pair}): {e}")
        if ws.application_state == WebSocketState.CONNECTED:
            await ws.close()
    finally:
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            await r.close()
        except Exception:
            pass
        logger.info(f"🔒 Cleaned up Redis pubsub for {pair}")
