"""
WebSocket Route Handlers.

Defines WebSocket endpoint handlers for:
- /ws/simulation/{session_id} — Real-time candle streaming
- /ws/community/{channel} — Community chat (persists messages to DB)
- /ws/prices — Live price ticker updates
- /ws/notifications — User-specific notifications
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from jose import jwt

from backend.core.config import get_settings
from backend.core.database import sessionmanager
from backend.core.redis import get_redis, RedisManager
from backend.websocket.manager import ws_manager

logger = structlog.get_logger()
router = APIRouter()


async def get_ws_user_id(websocket: WebSocket, token: str = Query(...)) -> str:
    """Authenticate WebSocket connection via query param token."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            raise WebSocketDisconnect(code=4001)
        return user_id
    except Exception:
        await websocket.close(code=4001, reason="Authentication failed")
        raise WebSocketDisconnect(code=4001)


# ─── Simulation Streaming ────────────────────────────────────────────────────

@router.websocket("/ws/simulation/{session_id}")
async def simulation_stream(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(...),
):
    """Stream candle data for a simulation session.
    
    Messages:
    - Server → Client: candle data, session state updates, AI predictions
    - Client → Server: trade commands, speed changes, pause/resume
    """
    user_id = await get_ws_user_id(websocket, token)
    channel = f"sim:{session_id}"

    await ws_manager.connect(websocket, user_id, channel)

    # Simulation state
    sim_state = {
        "paused": False,
        "speed": 1.0,
        "candle_index": 0,
        "total_candles": 252,
    }

    async def stream_candles():
        """Background task: generate and stream candle data."""
        import random
        import math

        base_price = 150.0
        price = base_price
        trend = 0.0002  # slight uptrend

        while sim_state["candle_index"] < sim_state["total_candles"]:
            if sim_state["paused"]:
                await asyncio.sleep(0.2)
                continue

            # Generate realistic OHLCV candle
            volatility = 0.015
            drift = trend + random.gauss(0, volatility)
            open_price = price
            close_price = open_price * (1 + drift)
            high_price = max(open_price, close_price) * (1 + abs(random.gauss(0, 0.005)))
            low_price = min(open_price, close_price) * (1 - abs(random.gauss(0, 0.005)))
            volume = int(random.gauss(50_000_000, 15_000_000))

            # Advance date (skip weekends)
            from datetime import date, timedelta
            base_date = date(2023, 1, 3)  # first trading day
            trading_day = base_date + timedelta(days=int(sim_state["candle_index"] * 365 / 252))

            candle = {
                "time": trading_day.isoformat(),
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "volume": max(volume, 1_000_000),
            }

            price = close_price
            sim_state["candle_index"] += 1

            try:
                await ws_manager.send_to_user(user_id, {
                    "type": "candle",
                    "data": candle,
                })
            except Exception:
                return

            # AI prediction every 10 candles
            if sim_state["candle_index"] % 10 == 0:
                direction = "up" if drift > 0 else "down"
                confidence = min(0.95, 0.5 + abs(drift) * 20)
                try:
                    await ws_manager.send_to_user(user_id, {
                        "type": "ai_prediction",
                        "data": {
                            "direction": direction,
                            "confidence": round(confidence, 2),
                        },
                    })
                except Exception:
                    return

            # Delay based on speed (faster speed = shorter delay)
            delay = 1.0 / sim_state["speed"]
            await asyncio.sleep(delay)

        # Session complete
        try:
            await ws_manager.send_to_user(user_id, {"type": "session_completed"})
        except Exception:
            pass

    # Start candle streaming in background
    stream_task = asyncio.create_task(stream_candles())

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "trade":
                await ws_manager.send_to_user(user_id, {
                    "type": "trade_ack",
                    "status": "received",
                    "data": data,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            elif msg_type == "speed_change":
                speed = data.get("speed", 1.0)
                sim_state["speed"] = max(0.25, min(speed, 10.0))
                await ws_manager.send_to_user(user_id, {
                    "type": "speed_updated",
                    "speed": sim_state["speed"],
                })

            elif msg_type == "pause":
                sim_state["paused"] = True
                await ws_manager.send_to_user(user_id, {"type": "session_paused"})

            elif msg_type == "resume":
                sim_state["paused"] = False
                await ws_manager.send_to_user(user_id, {"type": "session_resumed"})

            elif msg_type == "ping":
                await ws_manager.send_to_user(user_id, {"type": "pong"})

    except WebSocketDisconnect:
        stream_task.cancel()
        await ws_manager.disconnect(websocket, user_id, channel)


# ─── Community Chat ──────────────────────────────────────────────────────────

@router.websocket("/ws/community/{channel_name}")
async def community_chat(
    websocket: WebSocket,
    channel_name: str,
    token: str = Query(...),
):
    """Real-time community chat channel.
    
    Messages:
    - Server → Client: chat messages, user join/leave, typing indicators
    - Client → Server: send message, typing start/stop
    
    Every incoming message is persisted to the chat_messages table.
    """
    user_id = await get_ws_user_id(websocket, token)
    channel = f"chat:{channel_name}"

    await ws_manager.connect(websocket, user_id, channel)

    # Resolve user display info once on connect
    user_info: dict = {"display_name": user_id[:8], "username": "unknown", "avatar_url": None}
    try:
        async for db in sessionmanager.session():
            from backend.services.community_service import CommunityService
            svc = CommunityService(db)
            user_info = await svc.get_user_display(user_id)
    except Exception:
        logger.warning("community_ws.user_lookup_failed", user_id=user_id)

    # Send current online users
    await ws_manager.send_to_user(user_id, {
        "type": "channel_state",
        "online_users": ws_manager.get_channel_users(channel),
    })

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "message":
                content = data.get("content", "").strip()
                if not content:
                    continue

                now = datetime.now(timezone.utc)

                # Persist to database
                saved_id: str | None = None
                try:
                    async for db in sessionmanager.session():
                        from backend.services.community_service import CommunityService
                        svc = CommunityService(db)
                        msg_obj = await svc.save_message(
                            user_id=user_id,
                            channel=channel_name,
                            content=content,
                            message_type=data.get("message_type", "text"),
                        )
                        saved_id = str(msg_obj.id)
                except Exception:
                    logger.exception("community_ws.save_failed", channel=channel_name)

                broadcast = {
                    "type": "chat_message",
                    "id": saved_id,
                    "user_id": user_id,
                    "display_name": user_info.get("display_name", user_id[:8]),
                    "username": user_info.get("username", "unknown"),
                    "avatar_url": user_info.get("avatar_url"),
                    "content": content,
                    "channel": channel_name,
                    "timestamp": now.isoformat(),
                }
                await ws_manager.broadcast_to_channel(channel, broadcast)

            elif msg_type == "typing_start":
                await ws_manager.broadcast_to_channel(channel, {
                    "type": "user_typing",
                    "user_id": user_id,
                    "display_name": user_info.get("display_name", user_id[:8]),
                }, exclude_user=user_id)

            elif msg_type == "typing_stop":
                await ws_manager.broadcast_to_channel(channel, {
                    "type": "user_stopped_typing",
                    "user_id": user_id,
                }, exclude_user=user_id)

            elif msg_type == "ping":
                await ws_manager.send_to_user(user_id, {"type": "pong"})

    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, user_id, channel)


# ─── Live Price Ticker ───────────────────────────────────────────────────────

@router.websocket("/ws/prices")
async def price_ticker(
    websocket: WebSocket,
    token: str = Query(...),
):
    """Stream live price updates for subscribed tickers.
    
    Client sends: {"type": "subscribe", "tickers": ["AAPL", "TSLA"]}
    Server sends: {"type": "price_update", "ticker": "AAPL", "price": 150.25, ...}
    """
    user_id = await get_ws_user_id(websocket, token)
    channel = "prices:global"

    await ws_manager.connect(websocket, user_id, channel)

    subscribed_tickers: set[str] = set()

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "subscribe":
                tickers = data.get("tickers", [])
                subscribed_tickers.update(tickers)
                await ws_manager.send_to_user(user_id, {
                    "type": "subscribed",
                    "tickers": list(subscribed_tickers),
                })

            elif msg_type == "unsubscribe":
                tickers = data.get("tickers", [])
                subscribed_tickers -= set(tickers)
                await ws_manager.send_to_user(user_id, {
                    "type": "unsubscribed",
                    "tickers": list(subscribed_tickers),
                })

            elif msg_type == "ping":
                await ws_manager.send_to_user(user_id, {"type": "pong"})

    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, user_id, channel)


# ─── User Notifications ─────────────────────────────────────────────────────

@router.websocket("/ws/notifications")
async def user_notifications(
    websocket: WebSocket,
    token: str = Query(...),
):
    """User-specific notification channel.
    
    Server pushes:
    - XP earned, level up, badge unlocked
    - Challenge results
    - Trade alerts
    - AI prediction updates
    """
    user_id = await get_ws_user_id(websocket, token)
    channel = f"notifications:{user_id}"

    await ws_manager.connect(websocket, user_id, channel)

    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await ws_manager.send_to_user(user_id, {"type": "pong"})
            elif data.get("type") == "ack":
                # Client acknowledges notification receipt
                pass

    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, user_id, channel)
