"""Community Chat Schemas."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ChatMessageResponse(BaseModel):
    id: str
    user_id: str
    username: str
    display_name: str
    avatar_url: str | None = None
    channel: str
    content: str
    message_type: str = "text"
    created_at: datetime

    model_config = {"from_attributes": True}


class ChannelInfo(BaseModel):
    name: str
    display_name: str
    description: str
    member_count: int = 0
    last_message_at: datetime | None = None


class ChannelListResponse(BaseModel):
    channels: List[ChannelInfo]


class SendMessageRequest(BaseModel):
    content: str
    message_type: str = "text"
