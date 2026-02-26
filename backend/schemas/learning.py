"""
Learning Schemas.
"""

from __future__ import annotations

from pydantic import BaseModel


class LearningPathResponse(BaseModel):
    id: str
    slug: str
    title: str
    description: str
    category: str
    xp_reward: int
    unlocks_feature: str | None
    modules: list[ModuleSummary]
    user_progress: float  # 0.0 to 1.0
    is_locked: bool
    prerequisite_completed: bool


class ModuleSummary(BaseModel):
    id: str
    title: str
    module_type: str
    xp_reward: int
    status: str  # not_started, in_progress, completed
    score: float | None = None


class LearningModuleResponse(BaseModel):
    id: str
    title: str
    module_type: str
    content: dict  # lesson text, quiz questions, simulation config
    xp_reward: int
    status: str
    attempts: int
    best_score: float | None


class ModuleCompletionRequest(BaseModel):
    answers: dict | None = None  # quiz answers
    simulation_session_id: str | None = None


class ModuleCompletionResponse(BaseModel):
    status: str
    score: float | None
    xp_earned: int
    path_completed: bool
    feature_unlocked: str | None
    ai_explanation: str | None


class UserProgressResponse(BaseModel):
    total_paths: int
    completed_paths: int
    total_modules: int
    completed_modules: int
    overall_progress: float
    paths: list[PathProgressSummary]


class PathProgressSummary(BaseModel):
    path_id: str
    title: str
    progress: float
    modules_completed: int
    total_modules: int
