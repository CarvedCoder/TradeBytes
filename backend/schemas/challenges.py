"""
Challenge Schemas.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class DailyChallengeResponse(BaseModel):
    challenge_id: str
    challenge_date: date
    title: str
    difficulty: str
    theory_question: TheoryQuestion
    simulation_config: SimulationConfig
    prediction_config: PredictionConfig
    xp_reward: int
    bonus_xp: int
    already_attempted: bool


class TheoryQuestion(BaseModel):
    question: str
    options: list[str]
    # correct answer NOT sent to client


class SimulationConfig(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    capital: float


class PredictionConfig(BaseModel):
    ticker: str
    target_date: str
    metric: str  # "direction", "close_price"


class ChallengeAttemptRequest(BaseModel):
    challenge_id: str
    theory_answer: int  # option index
    simulation_session_id: str | None = None
    prediction_value: float | str | None = None


class ChallengeAttemptResponse(BaseModel):
    theory_correct: bool
    theory_explanation: str
    simulation_pnl: float | None
    prediction_accuracy: float | None
    total_xp_earned: int
    streak_bonus: bool
    new_streak: int
    ai_explanation: str


class ChallengeHistoryResponse(BaseModel):
    challenge_id: str
    challenge_date: date
    title: str
    total_xp_earned: int
    theory_correct: bool | None
    simulation_pnl: float | None
    prediction_accuracy: float | None
    completed_at: datetime | None
