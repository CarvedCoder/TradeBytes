"""
Community Chat Endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import get_current_user_id
from backend.schemas.community import (
    ChatMessageResponse,
    ChannelListResponse,
)
from backend.services.community_service import CommunityService

router = APIRouter()


@router.get("/channels", response_model=ChannelListResponse)
async def list_channels(
    db: AsyncSession = Depends(get_db),
):
    """List available chat channels (general, ticker-specific)."""
    service = CommunityService(db)
    return await service.list_channels()


@router.get("/messages/{channel}", response_model=list[ChatMessageResponse])
async def get_channel_messages(
    channel: str,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, le=200),
    before: str | None = None,
):
    """Get recent messages from a chat channel."""
    service = CommunityService(db)
    return await service.get_messages(channel, limit, before)
