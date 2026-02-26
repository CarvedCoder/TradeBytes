"""FastAPI wiring for alert history, detail, and realtime websocket."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, FastAPI, Query, WebSocket, WebSocketDisconnect

from .websocket_broadcast import AlertWebSocketHub

router = APIRouter(prefix="/api/alerts", tags=["alerts"])
ws_hub = AlertWebSocketHub()


async def get_db_pool() -> Any:  # pragma: no cover - app-specific dependency injection
    raise NotImplementedError


@router.get("/history")
async def get_alert_history(limit: int = Query(default=100, le=500), db_pool: Any = Depends(get_db_pool)):
    query = """
    SELECT alert_id, ts, type, severity, affected_assets, summary, confidence_score, event_score
    FROM alerts
    ORDER BY ts DESC
    LIMIT $1
    """
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(query, limit)
    return [dict(r) for r in rows]


@router.get("/{alert_id}")
async def get_alert_by_id(alert_id: str, db_pool: Any = Depends(get_db_pool)):
    query = """
    SELECT alert_id, ts, type, severity, affected_assets, summary, confidence_score, event_score, raw_payload
    FROM alerts WHERE alert_id = $1
    """
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(query, alert_id)
    return dict(row) if row else {"error": "not_found"}


async def alerts_ws_endpoint(websocket: WebSocket) -> None:
    await ws_hub.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_hub.disconnect(websocket)


def register_alert_routes(app: FastAPI) -> None:
    app.include_router(router)
    app.add_api_websocket_route("/ws/alerts", alerts_ws_endpoint)
