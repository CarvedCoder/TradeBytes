"""WebSocket fanout manager backed by Redis pub/sub."""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any, DefaultDict, Set

from fastapi import WebSocket


class AlertWebSocketHub:
    def __init__(self) -> None:
        self.clients: DefaultDict[str, Set[WebSocket]] = defaultdict(set)

    async def connect(self, websocket: WebSocket, room: str = "global") -> None:
        await websocket.accept()
        self.clients[room].add(websocket)

    def disconnect(self, websocket: WebSocket, room: str = "global") -> None:
        self.clients[room].discard(websocket)

    async def broadcast(self, message: dict[str, Any], room: str = "global") -> None:
        stale = []
        for client in self.clients[room]:
            try:
                await client.send_json(message)
            except Exception:
                stale.append(client)
        for client in stale:
            self.disconnect(client, room=room)


async def redis_to_websocket_loop(redis_client: Any, hub: AlertWebSocketHub, channel: str) -> None:
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)
    try:
        while True:
            event = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if event and "data" in event:
                payload = json.loads(event["data"])
                await hub.broadcast(payload)
            await asyncio.sleep(0.01)
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
