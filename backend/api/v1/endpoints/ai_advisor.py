"""
AI Financial Strategy Advisor Endpoints - RAG Pipeline.

Conversational AI that uses user portfolio, trade history,
news sentiment, prediction data, and learning progress.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import get_current_user_id
from backend.schemas.advisor import (
    AdvisorQueryRequest,
    AdvisorQueryResponse,
    ConversationHistoryResponse,
)
from backend.services.advisor_service import AdvisorService

router = APIRouter()


@router.post("/query", response_model=AdvisorQueryResponse)
async def query_advisor(
    request: AdvisorQueryRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Ask the AI financial advisor a question.
    
    The advisor uses RAG to retrieve relevant context:
    - User's portfolio state
    - Trade history
    - Current news sentiment
    - LSTM predictions
    - Learning progress
    
    Then generates a personalized response.
    """
    service = AdvisorService(db)
    return await service.query(user_id, request)


@router.get("/conversations", response_model=ConversationHistoryResponse)
@router.get("/history", response_model=ConversationHistoryResponse, include_in_schema=False)
async def get_conversation_history(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
):
    """Get recent advisor conversation history."""
    service = AdvisorService(db)
    return await service.get_history(user_id, limit)


@router.delete("/history")
async def clear_conversation_history(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Clear advisor conversation history."""
    service = AdvisorService(db)
    await service.clear_history(user_id)
    return {"status": "cleared"}
