"""Challenge Service."""

from __future__ import annotations

import uuid
from datetime import date

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.gamification import DailyChallenge, DailyChallengeAttempt
from backend.schemas.challenges import (
    DailyChallengeResponse,
    TheoryQuestion,
    SimulationConfig,
    PredictionConfig,
    ChallengeAttemptRequest,
    ChallengeAttemptResponse,
    ChallengeHistoryResponse,
)
from backend.services.gamification_service import GamificationService

logger = structlog.get_logger()


class ChallengeService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.gamification = GamificationService(db)

    async def get_today(self, user_id: str) -> DailyChallengeResponse:
        today = date.today()
        result = await self.db.execute(
            select(DailyChallenge).where(DailyChallenge.challenge_date == today)
        )
        challenge = result.scalar_one_or_none()
        if not challenge:
            raise ValueError("No challenge available for today")

        # Check if already attempted
        attempt_result = await self.db.execute(
            select(DailyChallengeAttempt).where(
                DailyChallengeAttempt.user_id == uuid.UUID(user_id),
                DailyChallengeAttempt.challenge_id == challenge.id,
            )
        )
        already_attempted = attempt_result.scalar_one_or_none() is not None

        return DailyChallengeResponse(
            challenge_id=str(challenge.id),
            challenge_date=challenge.challenge_date,
            title=challenge.title,
            difficulty=challenge.difficulty,
            theory_question=TheoryQuestion(
                question=challenge.theory_question["question"],
                options=challenge.theory_question["options"],
            ),
            simulation_config=SimulationConfig(**challenge.simulation_config),
            prediction_config=PredictionConfig(**challenge.prediction_config),
            xp_reward=challenge.xp_reward,
            bonus_xp=challenge.bonus_xp,
            already_attempted=already_attempted,
        )

    async def submit_attempt(
        self, user_id: str, request: ChallengeAttemptRequest
    ) -> ChallengeAttemptResponse:
        uid = uuid.UUID(user_id)
        challenge = await self.db.get(DailyChallenge, uuid.UUID(request.challenge_id))
        if not challenge:
            raise ValueError("Challenge not found")

        # Evaluate theory
        correct_answer = challenge.theory_question.get("correct", 0)
        theory_correct = request.theory_answer == correct_answer
        theory_explanation = challenge.theory_question.get("explanation", "")

        # Evaluate simulation PnL (from session if provided)
        simulation_pnl = 0.0  # TODO: fetch from simulation session

        # Evaluate prediction
        prediction_accuracy = 0.0  # TODO: compare with actual data

        # Calculate XP
        perfect = theory_correct and simulation_pnl > 0
        total_xp = await self.gamification.record_challenge_complete(user_id, perfect=perfect)

        # Record attempt
        attempt = DailyChallengeAttempt(
            user_id=uid,
            challenge_id=challenge.id,
            theory_correct=theory_correct,
            simulation_pnl=simulation_pnl,
            prediction_accuracy=prediction_accuracy,
            total_xp_earned=total_xp,
        )
        self.db.add(attempt)
        await self.db.flush()

        gam_state = await self.gamification.get_state(user_id)

        return ChallengeAttemptResponse(
            theory_correct=theory_correct,
            theory_explanation=theory_explanation,
            simulation_pnl=simulation_pnl,
            prediction_accuracy=prediction_accuracy,
            total_xp_earned=total_xp,
            streak_bonus=gam_state.current_streak > 1,
            new_streak=gam_state.current_streak,
            ai_explanation="Great job completing today's challenge!",
        )

    async def get_history(self, user_id: str, limit: int) -> list[ChallengeHistoryResponse]:
        result = await self.db.execute(
            select(DailyChallengeAttempt, DailyChallenge)
            .join(DailyChallenge)
            .where(DailyChallengeAttempt.user_id == uuid.UUID(user_id))
            .order_by(DailyChallenge.challenge_date.desc())
            .limit(limit)
        )
        rows = result.all()
        return [
            ChallengeHistoryResponse(
                challenge_id=str(attempt.challenge_id),
                challenge_date=challenge.challenge_date,
                title=challenge.title,
                total_xp_earned=attempt.total_xp_earned,
                theory_correct=attempt.theory_correct,
                simulation_pnl=attempt.simulation_pnl,
                prediction_accuracy=attempt.prediction_accuracy,
                completed_at=attempt.completed_at,
            )
            for attempt, challenge in rows
        ]
