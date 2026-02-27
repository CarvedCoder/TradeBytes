"""WebSocket hub for broadcasting alerts to connected clients."""

from __future__ import annotations

import json
from typing import Any, Dict, Set

import structlog
from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = structlog.get_logger()


class AlertWebSocketHub:
    """Lightweight fan-out hub for alert WebSocket connections.

    Usage inside a FastAPI websocket endpoint::

        hub = AlertWebSocketHub()

        async def ws_handler(ws: WebSocket):
            await hub.connect(ws)
            try:
                while True:
                    await ws.receive_text()   # keep-alive
            except WebSocketDisconnect:
                hub.disconnect(ws)
    """

    def __init__(self) -> None:
        self._clients: Set[WebSocket] = set()

    @property
    def client_count(self) -> int:
        return len(self._clients)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._clients.add(websocket)
        logger.info("alert_ws.connected", total=self.client_count)

    def disconnect(self, websocket: WebSocket) -> None:
        self._clients.discard(websocket)
        logger.info("alert_ws.disconnected", total=self.client_count)

    async def broadcast(self, payload: Dict[str, Any]) -> None:
        """Send *payload* to every connected client, dropping broken sockets."""
        message = json.dumps(payload, default=str)
        dead: list[WebSocket] = []

        for ws in list(self._clients):
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(message)
                else:
                    dead.append(ws)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self._clients.discard(ws)
