"""
WebSocket Route Handlers.

Defines WebSocket endpoint handlers for:
- /ws/simulation/{session_id} — Real-time candle streaming
- /ws/community/{channel} — Community chat
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

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "trade":
                # Process trade within simulation
                await ws_manager.send_to_user(user_id, {
                    "type": "trade_ack",
                    "status": "received",
                    "data": data,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            elif msg_type == "speed_change":
                speed = data.get("speed", 1.0)
                await ws_manager.send_to_user(user_id, {
                    "type": "speed_updated",
                    "speed": speed,
                })

            elif msg_type == "pause":
                await ws_manager.send_to_user(user_id, {"type": "session_paused"})

            elif msg_type == "resume":
                await ws_manager.send_to_user(user_id, {"type": "session_resumed"})

            elif msg_type == "ping":
                await ws_manager.send_to_user(user_id, {"type": "pong"})

    except WebSocketDisconnect:
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
    """
    user_id = await get_ws_user_id(websocket, token)
    channel = f"chat:{channel_name}"

    await ws_manager.connect(websocket, user_id, channel)

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
                broadcast = {
                    "type": "chat_message",
                    "user_id": user_id,
                    "content": data.get("content", ""),
                    "channel": channel_name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                await ws_manager.broadcast_to_channel(channel, broadcast)

            elif msg_type == "typing_start":
                await ws_manager.broadcast_to_channel(channel, {
                    "type": "user_typing",
                    "user_id": user_id,
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
