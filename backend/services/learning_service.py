"""Learning Service."""
from __future__ import annotations
import uuid
import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.gamification import LearningPath, LearningModule, UserLearningProgress, UserGamification
from backend.schemas.learning import *
from backend.services.gamification_service import GamificationService, XP_REWARDS

logger = structlog.get_logger()


class LearningService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.gamification = GamificationService(db)

    async def list_paths(self, user_id: str) -> list[LearningPathResponse]:
        result = await self.db.execute(select(LearningPath).order_by(LearningPath.order))
        paths = result.scalars().all()
        return [await self._path_to_response(p, user_id) for p in paths]

    async def get_path(self, user_id: str, path_slug: str) -> LearningPathResponse:
        result = await self.db.execute(select(LearningPath).where(LearningPath.slug == path_slug))
        path = result.scalar_one_or_none()
        if not path:
            raise ValueError("Learning path not found")
        return await self._path_to_response(path, user_id)

    async def get_module(self, user_id: str, module_id: str) -> LearningModuleResponse:
        module = await self.db.get(LearningModule, uuid.UUID(module_id))
        if not module:
            raise ValueError("Module not found")
        progress = await self._get_module_progress(user_id, module_id)
        return LearningModuleResponse(
            id=str(module.id), title=module.title, module_type=module.module_type,
            content=module.content, xp_reward=module.xp_reward,
            status=progress.status if progress else "not_started",
            attempts=progress.attempts if progress else 0,
            best_score=progress.score if progress else None,
        )

    async def complete_module(self, user_id: str, module_id: str, request: ModuleCompletionRequest) -> ModuleCompletionResponse:
        module = await self.db.get(LearningModule, uuid.UUID(module_id))
        if not module:
            raise ValueError("Module not found")

        progress = await self._get_or_create_progress(user_id, module)
        progress.status = "completed"
        progress.attempts += 1

        xp = await self.gamification.award_xp(user_id, module.xp_reward, "module_complete", "learning")
        await self.gamification.update_streak(user_id)

        # Check if path is now complete
        path_completed, feature_unlocked = await self._check_path_completion(user_id, module.path_id)

        await self.db.flush()
        return ModuleCompletionResponse(
            status="completed", score=progress.score, xp_earned=xp,
            path_completed=path_completed, feature_unlocked=feature_unlocked,
            ai_explanation="Great progress! You've completed this module.",
        )

    async def get_progress(self, user_id: str) -> UserProgressResponse:
        paths = (await self.db.execute(select(LearningPath))).scalars().all()
        path_summaries = []
        total_modules = 0
        completed_modules = 0
        completed_paths = 0
        for path in paths:
            modules = (await self.db.execute(select(LearningModule).where(LearningModule.path_id == path.id))).scalars().all()
            completed = 0
            for m in modules:
                total_modules += 1
                prog = await self._get_module_progress(user_id, str(m.id))
                if prog and prog.status == "completed":
                    completed += 1
                    completed_modules += 1
            if completed == len(modules) and len(modules) > 0:
                completed_paths += 1
            path_summaries.append(PathProgressSummary(
                path_id=str(path.id), title=path.title,
                progress=completed / len(modules) if modules else 0,
                modules_completed=completed, total_modules=len(modules),
            ))
        return UserProgressResponse(
            total_paths=len(paths), completed_paths=completed_paths,
            total_modules=total_modules, completed_modules=completed_modules,
            overall_progress=completed_modules / total_modules if total_modules else 0,
            paths=path_summaries,
        )

    async def _path_to_response(self, path: LearningPath, user_id: str) -> LearningPathResponse:
        modules = (await self.db.execute(
            select(LearningModule).where(LearningModule.path_id == path.id).order_by(LearningModule.order)
        )).scalars().all()
        module_summaries = []
        completed = 0
        for m in modules:
            prog = await self._get_module_progress(user_id, str(m.id))
            status = prog.status if prog else "not_started"
            if status == "completed":
                completed += 1
            module_summaries.append(ModuleSummary(
                id=str(m.id), title=m.title, module_type=m.module_type,
                xp_reward=m.xp_reward, status=status,
                score=prog.score if prog else None,
            ))
        progress = completed / len(modules) if modules else 0
        return LearningPathResponse(
            id=str(path.id), slug=path.slug, title=path.title,
            description=path.description, category=path.category,
            xp_reward=path.xp_reward, unlocks_feature=path.unlocks_feature,
            modules=module_summaries, user_progress=progress,
            is_locked=False, prerequisite_completed=True,
        )

    async def _get_module_progress(self, user_id: str, module_id: str) -> UserLearningProgress | None:
        result = await self.db.execute(
            select(UserLearningProgress).where(
                UserLearningProgress.user_id == uuid.UUID(user_id),
                UserLearningProgress.module_id == uuid.UUID(module_id),
            )
        )
        return result.scalar_one_or_none()

    async def _get_or_create_progress(self, user_id: str, module: LearningModule) -> UserLearningProgress:
        prog = await self._get_module_progress(user_id, str(module.id))
        if not prog:
            prog = UserLearningProgress(
                user_id=uuid.UUID(user_id), path_id=module.path_id, module_id=module.id
            )
            self.db.add(prog)
            await self.db.flush()
        return prog

    async def _check_path_completion(self, user_id: str, path_id: uuid.UUID) -> tuple[bool, str | None]:
        modules = (await self.db.execute(
            select(LearningModule).where(LearningModule.path_id == path_id)
        )).scalars().all()
        all_complete = True
        for m in modules:
            prog = await self._get_module_progress(user_id, str(m.id))
            if not prog or prog.status != "completed":
                all_complete = False
                break
        if all_complete:
            path = await self.db.get(LearningPath, path_id)
            if path and path.unlocks_feature:
                gam_result = await self.db.execute(
                    select(UserGamification).where(UserGamification.user_id == uuid.UUID(user_id))
                )
                gam = gam_result.scalar_one_or_none()
                if gam and path.unlocks_feature not in (gam.unlocked_features or []):
                    gam.unlocked_features = (gam.unlocked_features or []) + [path.unlocks_feature]
                return True, path.unlocks_feature
            return True, None
        return False, None
