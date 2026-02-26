"""
Community Chat Schemas.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ChatMessageResponse(BaseModel):
    id: str
    user_id: str
    username: str
    display_name: str
    avatar_url: str | None
    channel: str
    content: str
    message_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChannelListResponse(BaseModel):
    channels: list[ChannelInfo]


class ChannelInfo(BaseModel):
    name: str
    display_name: str
    description: str
    member_count: int
    last_message_at: datetime | None = None
