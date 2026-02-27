"""Community Chat Service."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.news import ChatMessage
from backend.models.user import User
from backend.schemas.community import (
    ChatMessageResponse,
    ChannelListResponse,
    ChannelInfo,
)

logger = structlog.get_logger()

DEFAULT_CHANNELS = [
    ChannelInfo(name="general", display_name="General", description="General trading discussion"),
    ChannelInfo(name="trading", display_name="Trading", description="Trade ideas & execution"),
    ChannelInfo(name="technical-analysis", display_name="Technical Analysis", description="Charts & technical analysis"),
    ChannelInfo(name="news", display_name="News", description="Breaking news & discussion"),
    ChannelInfo(name="beginners", display_name="Beginners", description="Questions from new traders"),
]


class CommunityService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_channels(self) -> ChannelListResponse:
        return ChannelListResponse(channels=DEFAULT_CHANNELS)

    async def get_messages(
        self, channel: str, limit: int, before: str | None
    ) -> list[ChatMessageResponse]:
        query = (
            select(ChatMessage, User)
            .outerjoin(User, ChatMessage.user_id == User.id)
            .where(ChatMessage.channel == channel)
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
        )
        if before:
            try:
                before_dt = datetime.fromisoformat(before)
                query = query.where(ChatMessage.created_at < before_dt)
            except ValueError:
                pass

        result = await self.db.execute(query)
        rows = result.all()

        # Return oldest-first so the frontend can append naturally
        rows = list(reversed(rows))

        return [
            ChatMessageResponse(
                id=str(msg.id),
                user_id=str(msg.user_id),
                username=user.username if user else "unknown",
                display_name=user.display_name if user else "Unknown",
                avatar_url=user.avatar_url if user else None,
                channel=msg.channel,
                content=msg.content,
                message_type=msg.message_type or "text",
                created_at=msg.created_at,
            )
            for msg, user in rows
        ]

    async def save_message(
        self,
        user_id: str,
        channel: str,
        content: str,
        message_type: str = "text",
    ) -> ChatMessage:
        """Persist a chat message and return the ORM object."""
        msg = ChatMessage(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            channel=channel,
            content=content,
            message_type=message_type,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(msg)
        await self.db.flush()
        logger.info("chat.message_saved", channel=channel, user_id=user_id)
        return msg

    async def get_user_display(self, user_id: str) -> dict:
        """Fetch username + display_name for a user_id."""
        result = await self.db.execute(
            select(User.username, User.display_name, User.avatar_url)
            .where(User.id == uuid.UUID(user_id))
        )
        row = result.one_or_none()
        if row:
            return {
                "username": row.username,
                "display_name": row.display_name,
                "avatar_url": row.avatar_url,
            }
        return {"username": "unknown", "display_name": "Unknown", "avatar_url": None}
