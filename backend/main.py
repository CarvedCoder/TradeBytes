"""
TradeBytes Main Application Entry Point.

Assembles the FastAPI application with all middleware, routers, startup/shutdown events,
and dependency injection wiring.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

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
