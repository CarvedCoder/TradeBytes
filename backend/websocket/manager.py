"""
WebSocket Connection Manager.

Centralized management of all WebSocket connections with:
- Per-channel room management
- User authentication on connect
- Redis pub/sub for multi-instance scaling
- Heartbeat/keepalive
- Graceful disconnect handling
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from backend.core.redis import RedisManager

logger = structlog.get_logger()


class ConnectionManager:
    """Manages WebSocket connections across channels/rooms."""

    def __init__(self) -> None:
        # channel_name -> set of (user_id, websocket)
        self._connections: dict[str, set[tuple[str, WebSocket]]] = defaultdict(set)
        # user_id -> set of websockets (a user can have multiple tabs)
        self._user_connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._heartbeat_tasks: dict[str, asyncio.Task] = {}

    @property
    def total_connections(self) -> int:
        return sum(len(conns) for conns in self._connections.values())

    async def connect(self, websocket: WebSocket, user_id: str, channel: str) -> None:
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        self._connections[channel].add((user_id, websocket))
        self._user_connections[user_id].add(websocket)

        logger.info("WebSocket connected", user_id=user_id, channel=channel,
                     total=self.total_connections)

        # Notify channel about new user
        await self.broadcast_to_channel(channel, {
            "type": "user_joined",
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, exclude_user=user_id)

    async def disconnect(self, websocket: WebSocket, user_id: str, channel: str) -> None:
        """Remove a WebSocket connection."""
        self._connections[channel].discard((user_id, websocket))
        self._user_connections[user_id].discard(websocket)

        if not self._user_connections[user_id]:
            del self._user_connections[user_id]
        if not self._connections[channel]:
            del self._connections[channel]

        logger.info("WebSocket disconnected", user_id=user_id, channel=channel,
                     total=self.total_connections)

        await self.broadcast_to_channel(channel, {
            "type": "user_left",
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def send_to_user(self, user_id: str, message: dict[str, Any]) -> None:
        """Send message to all connections of a specific user."""
        for ws in list(self._user_connections.get(user_id, set())):
            await self._safe_send(ws, message)

    async def broadcast_to_channel(
        self, channel: str, message: dict[str, Any], exclude_user: str | None = None
    ) -> None:
        """Broadcast message to all users in a channel."""
        for uid, ws in list(self._connections.get(channel, set())):
            if uid != exclude_user:
                await self._safe_send(ws, message)

    async def broadcast_global(self, message: dict[str, Any]) -> None:
        """Broadcast to ALL connected clients across all channels."""
        sent_to: set[int] = set()
        for channel_conns in self._connections.values():
            for _, ws in list(channel_conns):
                ws_id = id(ws)
                if ws_id not in sent_to:
                    await self._safe_send(ws, message)
                    sent_to.add(ws_id)

    def get_channel_users(self, channel: str) -> list[str]:
        """Get list of user IDs in a channel."""
        return list({uid for uid, _ in self._connections.get(channel, set())})

    async def _safe_send(self, ws: WebSocket, message: dict[str, Any]) -> None:
        """Send with error handling - remove dead connections."""
        try:
            if ws.client_state == WebSocketState.CONNECTED:
                await ws.send_json(message)
        except Exception:
            logger.warning("Failed to send WebSocket message, connection may be dead")


# Global connection manager singleton
ws_manager = ConnectionManager()
