"""Community Chat Service."""
from __future__ import annotations
import structlog
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.news import ChatMessage
from backend.models.user import User
from backend.schemas.community import ChatMessageResponse, ChannelListResponse, ChannelInfo

logger = structlog.get_logger()

DEFAULT_CHANNELS = [
    ChannelInfo(name="general", display_name="General", description="General trading discussion", member_count=0),
    ChannelInfo(name="AAPL", display_name="Apple", description="Apple stock discussion", member_count=0),
    ChannelInfo(name="TSLA", display_name="Tesla", description="Tesla stock discussion", member_count=0),
    ChannelInfo(name="crypto", display_name="Crypto", description="Cryptocurrency discussion", member_count=0),
    ChannelInfo(name="strategies", display_name="Strategies", description="Trading strategy discussion", member_count=0),
]


class CommunityService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_channels(self) -> ChannelListResponse:
        return ChannelListResponse(channels=DEFAULT_CHANNELS)

    async def get_messages(self, channel: str, limit: int, before: str | None) -> list[ChatMessageResponse]:
        query = (
            select(ChatMessage, User)
            .join(User, ChatMessage.user_id == User.id)
            .where(ChatMessage.channel == channel)
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
        )
        result = await self.db.execute(query)
        return [
            ChatMessageResponse(
                id=str(msg.id), user_id=str(msg.user_id),
                username=user.username, display_name=user.display_name,
                avatar_url=user.avatar_url, channel=msg.channel,
                content=msg.content, message_type=msg.message_type,
                created_at=msg.created_at,
            )
            for msg, user in result.all()
        ]
