"""
Database Connection Management.

Provides async SQLAlchemy engine, session factory, and dependency-injectable session getter.
Supports both PostgreSQL (core) and TimescaleDB (time-series) connections.
"""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from backend.core.config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


class DatabaseSessionManager:
    """Manages async database engine and session lifecycle."""

    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
        self._ts_engine: AsyncEngine | None = None
        self._ts_session_factory: async_sessionmaker[AsyncSession] | None = None

    async def init(self) -> None:
        """Initialize primary and TimescaleDB engines."""
        self._engine = create_async_engine(
            settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,
            echo=settings.debug,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # TimescaleDB for time-series data
        self._ts_engine = create_async_engine(
            settings.timescale_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,
            echo=settings.debug,
        )
        self._ts_session_factory = async_sessionmaker(
            bind=self._ts_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def close(self) -> None:
        """Dispose all database engines."""
        if self._engine:
            await self._engine.dispose()
        if self._ts_engine:
            await self._ts_engine.dispose()

    @property
    def engine(self) -> AsyncEngine:
        assert self._engine is not None, "Database not initialized"
        return self._engine

    @property
    def ts_engine(self) -> AsyncEngine:
        assert self._ts_engine is not None, "TimescaleDB not initialized"
        return self._ts_engine

    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        assert self._session_factory is not None
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def ts_session(self) -> AsyncGenerator[AsyncSession, None]:
        assert self._ts_session_factory is not None
        async with self._ts_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise


sessionmanager = DatabaseSessionManager()
engine = None  # Set during startup


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields a database session."""
    async for session in sessionmanager.session():
        yield session


async def get_ts_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields a TimescaleDB session."""
    async for session in sessionmanager.ts_session():
        yield session
