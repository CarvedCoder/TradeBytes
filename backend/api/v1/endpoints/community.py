"""
Community Chat Endpoints.

REST routes for channel listing, message history, and posting.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import get_current_user_id
from backend.schemas.community import (
    ChatMessageResponse,
    ChannelListResponse,
    SendMessageRequest,
)
from backend.services.community_service import CommunityService

router = APIRouter()


@router.get("/channels", response_model=ChannelListResponse)
async def list_channels(
    db: AsyncSession = Depends(get_db),
):
    """List available chat channels."""
    service = CommunityService(db)
    return await service.list_channels()


@router.get("/messages/{channel}", response_model=list[ChatMessageResponse])
async def get_channel_messages(
    channel: str,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, le=200),
    before: str | None = None,
):
    """Get recent messages from a chat channel (oldest-first)."""
    service = CommunityService(db)
    return await service.get_messages(channel, limit, before)


@router.post("/messages/{channel}", response_model=ChatMessageResponse)
async def post_message(
    channel: str,
    body: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Post a message to a channel (REST fallback – WebSocket preferred)."""
    service = CommunityService(db)
    msg = await service.save_message(
        user_id=user_id,
        channel=channel,
        content=body.content,
        message_type=body.message_type,
    )
    info = await service.get_user_display(user_id)
    return ChatMessageResponse(
        id=str(msg.id),
        user_id=user_id,
        username=info["username"],
        display_name=info["display_name"],
        avatar_url=info["avatar_url"],
        channel=msg.channel,
        content=msg.content,
        message_type=msg.message_type,
        created_at=msg.created_at,
    )
