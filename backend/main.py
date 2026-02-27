"""
TradeBytes Main Application Entry Point.

Assembles the FastAPI application with all middleware, routers, startup/shutdown events,
and dependency injection wiring.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from backend.core.config import get_settings
from backend.core.database import engine, sessionmanager
from backend.core.redis import redis_manager
from backend.api.v1.router import api_router
from backend.websocket.manager import ws_manager

logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown hooks."""
    # ── Startup ──
    logger.info("Starting TradeBytes", env=settings.app_env, version=settings.app_version)

    # Initialize Redis
    await redis_manager.connect()
    logger.info("Redis connected")

    # Initialize database
    await sessionmanager.init()
    logger.info("Database initialized")

    logger.info("WebSocket manager ready", connections=ws_manager.total_connections)

    yield

    # ── Shutdown ──
    logger.info("Shutting down TradeBytes")
    await redis_manager.disconnect()
    await sessionmanager.close()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI-Powered Finance Education & Investment Intelligence Platform",
        lifespan=lifespan,
        docs_url=f"{settings.api_prefix}/docs" if settings.debug else None,
        redoc_url=f"{settings.api_prefix}/redoc" if settings.debug else None,
        openapi_url=f"{settings.api_prefix}/openapi.json" if settings.debug else None,
    )

    # ── Middleware ──
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if settings.is_production:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=["tradebytes.io", "*.tradebytes.io"])

    # ── API Routes ──
    app.include_router(api_router, prefix=settings.api_prefix)

    # ── WebSocket Routes ──
    from backend.websocket.handlers import router as ws_router
    app.include_router(ws_router)

    # ── Alert WebSocket ──
    from backend.api.v1.endpoints.alerts import alerts_ws_endpoint
    app.add_api_websocket_route("/ws/alerts", alerts_ws_endpoint)

    # ── Centralized Exception Handlers ──

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        """Map service-layer ValueError to proper HTTP 400/404 responses."""
        message = str(exc)
        # Determine if it's a "not found" or a validation error
        not_found_keywords = ["not found", "not exist", "no ", "expired"]
        status_code = 404 if any(kw in message.lower() for kw in not_found_keywords) else 400
        logger.warning(
            "Request error",
            path=request.url.path,
            method=request.method,
            detail=message,
            status_code=status_code,
        )
        return JSONResponse(
            status_code=status_code,
            content={"detail": message},
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        """Handle database integrity constraint violations."""
        logger.error(
            "Database integrity error",
            path=request.url.path,
            method=request.method,
            detail=str(exc.orig) if exc.orig else str(exc),
        )
        return JSONResponse(
            status_code=409,
            content={"detail": "Data conflict: a resource with the given identifiers already exists or a constraint was violated."},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Catch-all for unhandled exceptions — prevent raw 500 stacktraces from leaking."""
        logger.error(
            "Unhandled exception",
            path=request.url.path,
            method=request.method,
            exc_type=type(exc).__name__,
            detail=str(exc)[:500],
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred. Please try again later."},
        )

    # ── Health Check ──
    @app.get("/health")
    async def health():
        return {
            "status": "healthy",
            "version": settings.app_version,
            "environment": settings.app_env,
        }

    return app


app = create_app()
