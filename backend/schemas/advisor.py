"""
AI Advisor Schemas.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AdvisorQueryRequest(BaseModel):
    message: str = Field(..., alias="query")
    conversation_id: str | None = None
    include_portfolio: bool = True
    include_news: bool = True
    include_predictions: bool = True

    model_config = {"populate_by_name": True}


class AdvisorQueryResponse(BaseModel):
    response: str
    conversation_id: str
    sources: list[AdvisorSource]
    suggested_actions: list[SuggestedAction]


class AdvisorSource(BaseModel):
    type: str  # "portfolio", "news", "prediction", "learning", "market_data"
    reference: str
    relevance: float


class SuggestedAction(BaseModel):
    action_type: str  # "trade", "learn", "analyze"
    description: str
    link: str | None = None


class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    messages: list[ConversationMessage]


class ConversationMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    sources: list[AdvisorSource] | None = None
