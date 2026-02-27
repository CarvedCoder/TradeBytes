"""Alert API endpoints – history, detail, manual shock evaluation, and WebSocket.

Routes:
  GET  /alerts/history       – paginated alert history
  GET  /alerts/{alert_id}    – single alert detail
  POST /alerts/evaluate      – manually run the shock detector
  GET  /alerts/risk-context   – portfolio exposure advisory
  WS   /ws/alerts            – real-time alert stream (registered in main.py)
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.redis import redis_manager
from backend.core.security import get_current_user_id
from backend.schemas.alerts import (
    AlertHistoryResponse,
    AlertResponse,
    RiskContextResponse,
    ShockEvaluateRequest,
    ShockEvaluateResponse,
)
from backend.services.alerts.alert_service import AlertService, risk_context_message
from backend.services.alerts.shock_detector import ShockDetector
from backend.services.alerts.websocket_broadcast import AlertWebSocketHub

router = APIRouter()

# Shared instances – created once at module level
ws_hub = AlertWebSocketHub()
_detector = ShockDetector()


# ── REST Endpoints ───────────────────────────────────────────────────────────


@router.get("/history", response_model=AlertHistoryResponse)
async def get_alert_history(
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
    _user_id: str = Depends(get_current_user_id),
):
    """Return recent alerts, newest first."""
    svc = AlertService(db, redis_manager)
    alerts = await svc.get_history(limit=limit)
    return AlertHistoryResponse(alerts=alerts, count=len(alerts))


@router.get("/risk-context", response_model=RiskContextResponse)
async def get_risk_context(
    ticker: str = Query(...),
    exposure_weight: float = Query(..., ge=0.0, le=1.0),
    _user_id: str = Depends(get_current_user_id),
):
    """Return a risk-context advisory for the given portfolio exposure."""
    msg = await risk_context_message(exposure_weight, ticker)
    return RiskContextResponse(**msg)


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert_by_id(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    _user_id: str = Depends(get_current_user_id),
):
    """Retrieve a single alert by its ID."""
    svc = AlertService(db, redis_manager)
    result = await svc.get_by_id(alert_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertResponse(**result)


@router.post("/evaluate", response_model=ShockEvaluateResponse)
async def evaluate_shock(
    body: ShockEvaluateRequest,
    db: AsyncSession = Depends(get_db),
    _user_id: str = Depends(get_current_user_id),
):
    """Manually run the shock detector against supplied market data.

    If thresholds are breached the alert is persisted, published, and
    broadcast over WebSocket.
    """
    record = _detector.evaluate(
        ticker=body.ticker,
        current_price=body.current_price,
        previous_close=body.previous_close,
        current_volume=body.current_volume,
        avg_volume=body.avg_volume,
        extra=body.extra,
    )
    if record is None:
        return ShockEvaluateResponse(triggered=False)

    svc = AlertService(db, redis_manager)
    trace_id = str(uuid.uuid4())
    await svc.process_alert(record, trace_id=trace_id, source_event_id="manual_evaluate")

    # Also push to connected WebSocket clients
    await ws_hub.broadcast(
        {
            "alert_id": record.alert_id,
            "type": record.type.value,
            "severity": record.severity,
            "summary": record.summary,
            "affected_assets": record.affected_assets,
            "confidence_score": record.confidence_score,
            "event_score": record.event_score,
        }
    )

    return ShockEvaluateResponse(
        triggered=True,
        alert=AlertResponse(
            alert_id=record.alert_id,
            ts=record.timestamp.isoformat(),
            type=record.type.value,
            severity=record.severity,
            affected_assets=record.affected_assets,
            summary=record.summary,
            confidence_score=record.confidence_score,
            event_score=record.event_score,
        ),
    )


# ── WebSocket Endpoint (registered by main.py) ──────────────────────────────


async def alerts_ws_endpoint(websocket: WebSocket) -> None:
    """Real-time alert stream. Clients receive JSON messages whenever an alert fires."""
    await ws_hub.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive
    except WebSocketDisconnect:
        ws_hub.disconnect(websocket)
