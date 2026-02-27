"""
Learning Paths Endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import get_current_user_id
from backend.schemas.learning import (
    LearningPathResponse,
    LearningModuleResponse,
    ModuleCompletionRequest,
    ModuleCompletionResponse,
    UserProgressResponse,
)
from backend.services.learning_service import LearningService

router = APIRouter()


@router.get("/paths", response_model=list[LearningPathResponse])
async def list_learning_paths(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all learning paths with user's progress."""
    service = LearningService(db)
    return await service.list_paths(user_id)


@router.get("/paths/{path_slug}", response_model=LearningPathResponse)
async def get_learning_path(
    path_slug: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific learning path with modules and progress."""
    service = LearningService(db)
    try:
        return await service.get_path(user_id, path_slug)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/modules/{module_id}", response_model=LearningModuleResponse)
async def get_module(
    module_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific learning module content."""
    service = LearningService(db)
    try:
        return await service.get_module(user_id, module_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/modules/{module_id}/complete", response_model=ModuleCompletionResponse)
async def complete_module(
    module_id: str,
    request: ModuleCompletionRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Mark a module as completed and award XP.
    
    If the module is a quiz/simulation, validates answers.
    If completing a path, checks for feature unlocks.
    """
    service = LearningService(db)
    try:
        return await service.complete_module(user_id, module_id, request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/progress", response_model=UserProgressResponse)
async def get_user_progress(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get user's overall learning progress across all paths."""
    service = LearningService(db)
    return await service.get_progress(user_id)
