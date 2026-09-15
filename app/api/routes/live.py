import asyncio
import json
import os
import traceback
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger
from app.broker.angel_one import AngelOneBroker
from datetime import datetime

router = APIRouter()
broker = AngelOneBroker()
broker.login()

# Per-client queues for tick fan-out
connected_clients = set()
is_ws_initialized = False
is_subscribed = False

LIVE_STATE_PATH = "data/live_paper_trading.json"


# Store the main event loop so the WebSocket thread can schedule tasks on it
main_loop = None

def on_tick(msg):
    """Called from the broker's WebSocket thread whenever a tick arrives.
    SmartWebSocketV2 sends a dict (not a list) with prices in paise (divide by 100).
    """
    # Handle both dict (normal) and list (edge case) formats
    items = [msg] if isinstance(msg, dict) else (msg if isinstance(msg, list) else [])
    for item in items:
        if 'last_traded_price' in item and str(item.get('token', '')).strip() == '26000':
            # Convert paise to rupees
            normalized = dict(item)
            normalized['last_traded_price'] = item['last_traded_price'] / 100.0
            try:
                if main_loop and not main_loop.is_closed():
                    for q in list(connected_clients):
                        main_loop.call_soon_threadsafe(q.put_nowait, normalized)
            except Exception as e:
                logger.error(f"Tick broadcast error: {e}")


def ensure_broker_ws():
    """Initialize the Angel One SmartWebSocketV2 exactly once."""
    global is_ws_initialized, main_loop
    if not is_ws_initialized:
        main_loop = asyncio.get_event_loop()
        logger.info("Initializing Angel One WebSocket for Frontend Streaming...")
        broker.init_websocket(on_tick_callback=on_tick)
        is_ws_initialized = True


def ensure_subscribed():
    """Subscribe to Nifty 50 exactly once, not per-client."""
    global is_subscribed
    if not is_subscribed:
        broker.subscribe_websocket("FRONTEND_STREAM", 1, [{"exchangeType": 1, "tokens": ["26000"]}])
        is_subscribed = True


def load_history_from_file():
    """
    Load candle history from the JSON file that run_paper_trading.py saves.
    This completely avoids any REST API calls and their rate limits.
    """
    if not os.path.exists(LIVE_STATE_PATH):
        return None
    try:
        with open(LIVE_STATE_PATH, "r") as f:
            state = json.load(f)
        md = state.get("market_data", {})
        timestamps = md.get("timestamp", [])
        opens = md.get("open", [])
        highs = md.get("high", [])
        lows = md.get("low", [])
        closes = md.get("close", [])
        if not timestamps:
            return None
        # Return as list of [timestamp, open, high, low, close] matching the format
        # the frontend already expects from the HISTORY message
        candles = []
        for i in range(len(timestamps)):
            candles.append([timestamps[i], opens[i], highs[i], lows[i], closes[i]])
        return candles
    except Exception as e:
        logger.error(f"Failed to load history from {LIVE_STATE_PATH}: {e}")
        return None


@router.websocket("/stream")
async def stream_live_data(websocket: WebSocket):
    await websocket.accept()
    logger.info("Frontend connected to live stream.")

    # Create a unique queue for this client
    client_queue = asyncio.Queue()
    connected_clients.add(client_queue)

    ensure_broker_ws()

    # Give a moment for the WS thread to connect, then subscribe once
    await asyncio.sleep(1)
    ensure_subscribed()

    # Send historical candle context from the local JSON file (zero API calls)
    try:
        history = load_history_from_file()
        if history:
            await websocket.send_json({"type": "HISTORY", "data": history})
            logger.info(f"Sent {len(history)} historical candles from local file.")
        else:
            logger.warning("No local history file found. Chart will start empty.")
    except Exception as e:
        logger.error(f"Failed to send history to frontend: {e}")

    # Stream live ticks to this client
    try:
        while True:
            # Non-blocking check for client disconnect
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
            except asyncio.TimeoutError:
                pass

            # Forward ticks from the broker WS → this client's browser
            try:
                tick = await asyncio.wait_for(client_queue.get(), timeout=1.0)
                ltp = float(tick.get('last_traded_price', 0))
                await websocket.send_json({
                    "type": "TICK",
                    "timestamp": datetime.now().isoformat(),
                    "price": ltp
                })
            except asyncio.TimeoutError:
                pass

    except WebSocketDisconnect:
        logger.info("Frontend disconnected from live stream.")
    except Exception as e:
        logger.error(f"WebSocket stream error: {e}")
        traceback.print_exc()
    finally:
        connected_clients.discard(client_queue)
