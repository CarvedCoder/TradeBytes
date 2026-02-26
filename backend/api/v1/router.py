"""
API v1 Router Aggregator.

Collects all domain routers into a single APIRouter mounted at /api/v1.
"""

from fastapi import APIRouter

from backend.api.v1.endpoints.auth import router as auth_router
from backend.api.v1.endpoints.users import router as users_router
from backend.api.v1.endpoints.gamification import router as gamification_router
from backend.api.v1.endpoints.trading import router as trading_router
from backend.api.v1.endpoints.simulation import router as simulation_router
from backend.api.v1.endpoints.portfolio import router as portfolio_router
from backend.api.v1.endpoints.news import router as news_router
from backend.api.v1.endpoints.challenges import router as challenges_router
from backend.api.v1.endpoints.learning import router as learning_router
from backend.api.v1.endpoints.leaderboard import router as leaderboard_router
from backend.api.v1.endpoints.ai_advisor import router as advisor_router
from backend.api.v1.endpoints.ai_prediction import router as prediction_router
from backend.api.v1.endpoints.community import router as community_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(gamification_router, prefix="/gamification", tags=["Gamification"])
api_router.include_router(trading_router, prefix="/trading", tags=["Trading"])
api_router.include_router(simulation_router, prefix="/simulation", tags=["Simulation"])
api_router.include_router(portfolio_router, prefix="/portfolio", tags=["Portfolio"])
api_router.include_router(news_router, prefix="/news", tags=["News Intelligence"])
api_router.include_router(challenges_router, prefix="/challenges", tags=["Daily Challenges"])
api_router.include_router(learning_router, prefix="/learning", tags=["Learning Paths"])
api_router.include_router(leaderboard_router, prefix="/leaderboard", tags=["Leaderboard"])
api_router.include_router(advisor_router, prefix="/advisor", tags=["AI Advisor"])
api_router.include_router(prediction_router, prefix="/prediction", tags=["AI Prediction"])
api_router.include_router(community_router, prefix="/community", tags=["Community"])
