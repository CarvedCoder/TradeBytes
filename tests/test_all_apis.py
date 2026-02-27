"""
TradeBytes — Comprehensive API Test Suite
==========================================

Tests all 50+ API endpoints across 13 router modules.
Covers: public endpoints, auth protection, authenticated CRUD, schema validation,
error handling, and edge cases.

Usage — standalone (recommended):
    python tests/test_all_apis.py

Usage — pytest:
    pytest tests/test_all_apis.py -v

Prerequisites:
    pip install httpx
    uvicorn backend.main:app --reload --port 8000   (must be running)
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from dataclasses import dataclass, field

import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = "http://localhost:8000"
API = f"{BASE_URL}/api/v1"
TIMEOUT = 15.0

TEST_USER_ID = "22222222-2222-2222-2222-222222222222"
TEST_USERNAME = "api_test_runner"
TEST_DISPLAY_NAME = "API Test Runner"
TEST_EMAIL = "api_test@tradebytes.test"


# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------


@dataclass
class TestResult:
    name: str
    passed: bool
    status_code: int | None = None
    detail: str = ""


@dataclass
class TestSuite:
    results: list[TestResult] = field(default_factory=list)

    def record(self, name: str, passed: bool, status_code: int | None = None, detail: str = ""):
        self.results.append(TestResult(name, passed, status_code, detail))

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    def print_report(self):
        sep = "=" * 90
        print(f"\n{sep}")
        print("  TRADEBYTES API TEST RESULTS")
        print(sep)
        for r in self.results:
            icon = "PASS" if r.passed else "FAIL"
            code = f" [{r.status_code}]" if r.status_code else ""
            detail = f"  -- {r.detail}" if r.detail else ""
            print(f"  {icon}  {r.name:<55}{code}{detail}")
        print(sep)
        total = len(self.results)
        print(f"  Total: {total}  |  Passed: {self.passed}  |  Failed: {self.failed}")
        if self.failed == 0:
            print("  ALL TESTS PASSED")
        else:
            print(f"  {self.failed} TEST(S) FAILED")
        print(sep)


suite = TestSuite()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def ok(resp: httpx.Response, expected: int = 200) -> bool:
    return resp.status_code == expected


def has_keys(resp: httpx.Response, keys: list[str]) -> bool:
    try:
        data = resp.json()
        return all(k in data for k in keys)
    except Exception:
        return False


def check(
    name: str,
    resp: httpx.Response,
    expected: int | list[int] = 200,
    keys: list[str] | None = None,
    detail: str = "",
) -> bool:
    """Record a test result and return True if passed."""
    if isinstance(expected, int):
        expected = [expected]
    status_ok = resp.status_code in expected
    keys_ok = has_keys(resp, keys) if keys and status_ok else True
    passed = status_ok and keys_ok
    msg = detail
    if not status_ok:
        msg = f"expected {expected}, got {resp.status_code}: {resp.text[:80]}"
    elif not keys_ok:
        msg = f"missing keys in response: {resp.text[:80]}"
    suite.record(name, passed, resp.status_code, msg)
    return passed


# ---------------------------------------------------------------------------
# DB Setup / Teardown
# ---------------------------------------------------------------------------


async def create_test_user():
    """Create a test user directly in the DB."""
    from backend.core.database import sessionmanager
    from backend.core.redis import redis_manager
    from backend.models.user import User
    from backend.models.gamification import UserGamification
    from backend.models.trading import Portfolio

    await redis_manager.connect()
    await sessionmanager.init()

    uid = uuid.UUID(TEST_USER_ID)
    async for db in sessionmanager.session():
        existing = await db.get(User, uid)
        if not existing:
            db.add(User(id=uid, username=TEST_USERNAME, display_name=TEST_DISPLAY_NAME, email=TEST_EMAIL))
            db.add(UserGamification(user_id=uid))
            db.add(Portfolio(user_id=uid))
            await db.flush()

    await sessionmanager.close()
    await redis_manager.disconnect()


async def destroy_test_user():
    """Remove test user and all related records."""
    from backend.core.database import sessionmanager
    from backend.core.redis import redis_manager
    from backend.models.user import User
    from backend.models.gamification import UserGamification
    from backend.models.trading import Portfolio, Position, Trade, SimulationSession
    from sqlalchemy import delete, select

    await redis_manager.connect()
    await sessionmanager.init()

    uid = uuid.UUID(TEST_USER_ID)
    async for db in sessionmanager.session():
        await db.execute(delete(SimulationSession).where(SimulationSession.user_id == uid))
        res = await db.execute(select(Portfolio).where(Portfolio.user_id == uid))
        port = res.scalar_one_or_none()
        if port:
            await db.execute(delete(Position).where(Position.portfolio_id == port.id))
        await db.execute(delete(Trade).where(Trade.user_id == uid))
        await db.execute(delete(Portfolio).where(Portfolio.user_id == uid))
        await db.execute(delete(UserGamification).where(UserGamification.user_id == uid))
        await db.execute(delete(User).where(User.id == uid))

    await sessionmanager.close()
    await redis_manager.disconnect()


def get_auth_token() -> str:
    """Generate a JWT for the test user (no async needed)."""
    from backend.core.security import create_token_pair

    return create_token_pair(TEST_USER_ID).access_token


# ===================================================================
#  Test Functions
# ===================================================================


async def test_health(c: httpx.AsyncClient):
    """Health & docs endpoints."""
    r = await c.get("/health")
    check("GET /health", r, 200, ["status", "version"])

    r = await c.get(f"{API}/docs")
    check("GET /api/v1/docs", r, [200, 404], detail="docs page (200=served, 404=disabled)")


async def test_auth(c: httpx.AsyncClient):
    """Auth flow endpoints (WebAuthn begin + refresh)."""
    # Register begin - new user
    r = await c.post(f"{API}/auth/register/begin", json={
        "username": f"reg_{uuid.uuid4().hex[:8]}",
        "display_name": "Reg Test",
        "email": "reg@test.com",
    })
    check("POST /auth/register/begin (new)", r, 200, ["options"])

    # Register begin - duplicate
    r = await c.post(f"{API}/auth/register/begin", json={
        "username": TEST_USERNAME,
        "display_name": "Dup",
        "email": "dup@test.com",
    })
    check("POST /auth/register/begin (dup)", r, 409)

    # Register begin - bad username (schema validation)
    r = await c.post(f"{API}/auth/register/begin", json={
        "username": "x",
        "display_name": "Short",
        "email": "s@t.com",
    })
    check("POST /auth/register/begin (short username)", r, 422)

    # Login begin - non-existent
    r = await c.post(f"{API}/auth/login/begin", json={"username": "ghost_user_999"})
    check("POST /auth/login/begin (404)", r, 404)

    # Login begin - existing (may fail with 400/404 if no passkey registered)
    r = await c.post(f"{API}/auth/login/begin", json={"username": TEST_USERNAME})
    check("POST /auth/login/begin (exists)", r, [200, 400, 404])

    # Refresh - invalid token
    r = await c.post(f"{API}/auth/refresh", json={"refresh_token": "bad.jwt.token"})
    check("POST /auth/refresh (bad token)", r, 401)

    # Refresh - missing body
    r = await c.post(f"{API}/auth/refresh")
    check("POST /auth/refresh (no body)", r, 422)


async def test_users(c: httpx.AsyncClient, h: dict):
    """User profile endpoints."""
    r = await c.get(f"{API}/users/me", headers=h)
    check("GET /users/me", r, 200, ["user_id", "username", "display_name"])

    r = await c.patch(f"{API}/users/me", headers=h, json={"display_name": "Updated Name"})
    check("PATCH /users/me", r, 200)

    # Restore
    await c.patch(f"{API}/users/me", headers=h, json={"display_name": TEST_DISPLAY_NAME})

    r = await c.get(f"{API}/users/{TEST_USERNAME}")
    check("GET /users/{username} (public)", r, 200)

    r = await c.get(f"{API}/users/nonexistent_xyz_999")
    check("GET /users/{username} (404)", r, 404)

    r = await c.get(f"{API}/users/me")
    check("GET /users/me (no auth)", r, [401, 403])


async def test_gamification(c: httpx.AsyncClient, h: dict):
    """Gamification state, badges, unlocks."""
    r = await c.get(f"{API}/gamification/state", headers=h)
    check("GET /gamification/state", r, 200, ["user_id", "xp_total", "level"])

    r = await c.get(f"{API}/gamification/xp/history", headers=h)
    check("GET /gamification/xp/history", r, 200)

    r = await c.get(f"{API}/gamification/badges", headers=h)
    check("GET /gamification/badges", r, 200, ["earned", "in_progress", "locked"])

    r = await c.get(f"{API}/gamification/unlocks", headers=h)
    check("GET /gamification/unlocks", r, 200, ["unlocked", "locked"])

    r = await c.get(f"{API}/gamification/state")
    check("GET /gamification/state (no auth)", r, [401, 403])


async def test_portfolio(c: httpx.AsyncClient, h: dict):
    """Portfolio overview, risk, correlation, drawdown, suggestions."""
    r = await c.get(f"{API}/portfolio/overview", headers=h)
    check("GET /portfolio/overview", r, 200, ["total_value", "cash_balance"])

    r = await c.get(f"{API}/portfolio/allocation", headers=h)
    check("GET /portfolio/allocation (alias)", r, 200)

    r = await c.get(f"{API}/portfolio/risk-metrics", headers=h)
    check("GET /portfolio/risk-metrics", r, 200, ["portfolio_volatility", "sharpe_ratio"])

    r = await c.get(f"{API}/portfolio/risk", headers=h)
    check("GET /portfolio/risk (alias)", r, 200)

    r = await c.get(f"{API}/portfolio/correlation", headers=h)
    check("GET /portfolio/correlation", r, 200, ["tickers", "matrix"])

    r = await c.get(f"{API}/portfolio/drawdown", headers=h)
    check("GET /portfolio/drawdown", r, 200, ["current_drawdown", "max_drawdown"])

    r = await c.get(f"{API}/portfolio/ai-suggestions", headers=h)
    check("GET /portfolio/ai-suggestions", r, 200, ["overall_assessment", "suggestions"])

    r = await c.get(f"{API}/portfolio/suggestions", headers=h)
    check("GET /portfolio/suggestions (alias)", r, 200)

    r = await c.get(f"{API}/portfolio/overview")
    check("GET /portfolio/overview (no auth)", r, [401, 403])


async def test_trading(c: httpx.AsyncClient, h: dict):
    """Trade execution, history, detail, error cases."""
    # Buy
    r = await c.post(f"{API}/trading/execute", headers=h, json={
        "ticker": "AAPL", "side": "buy", "quantity": 5,
    })
    check("POST /trading/execute (buy)", r, 200, ["trade_id", "price", "xp_earned"])

    # Sell
    r = await c.post(f"{API}/trading/execute", headers=h, json={
        "ticker": "AAPL", "side": "sell", "quantity": 2,
    })
    check("POST /trading/execute (sell)", r, 200)

    # Insufficient funds
    r = await c.post(f"{API}/trading/execute", headers=h, json={
        "ticker": "AAPL", "side": "buy", "quantity": 99999999,
    })
    check("POST /trading/execute (no funds)", r, 400)

    # Insufficient shares
    r = await c.post(f"{API}/trading/execute", headers=h, json={
        "ticker": "MSFT", "side": "sell", "quantity": 100,
    })
    check("POST /trading/execute (no shares)", r, 400)

    # Invalid side (schema)
    r = await c.post(f"{API}/trading/execute", headers=h, json={
        "ticker": "AAPL", "side": "hodl", "quantity": 1,
    })
    check("POST /trading/execute (bad side)", r, 422)

    # Zero quantity (schema)
    r = await c.post(f"{API}/trading/execute", headers=h, json={
        "ticker": "AAPL", "side": "buy", "quantity": 0,
    })
    check("POST /trading/execute (qty=0)", r, 422)

    # Negative quantity (schema)
    r = await c.post(f"{API}/trading/execute", headers=h, json={
        "ticker": "AAPL", "side": "buy", "quantity": -5,
    })
    check("POST /trading/execute (qty<0)", r, 422)

    # History
    r = await c.get(f"{API}/trading/history", headers=h)
    check("GET /trading/history", r, 200)
    trades = r.json()

    # History filter by ticker
    r = await c.get(f"{API}/trading/history", headers=h, params={"ticker": "AAPL"})
    check("GET /trading/history?ticker=AAPL", r, 200)

    # Detail
    if trades:
        tid = trades[0]["trade_id"]
        r = await c.get(f"{API}/trading/history/{tid}", headers=h)
        check("GET /trading/history/:id", r, 200, ["trade_id", "ticker"])

    # Detail non-existent
    r = await c.get(f"{API}/trading/history/{uuid.uuid4()}", headers=h)
    check("GET /trading/history/:id (404)", r, 404)

    # No auth
    r = await c.post(f"{API}/trading/execute", json={"ticker": "X", "side": "buy", "quantity": 1})
    check("POST /trading/execute (no auth)", r, [401, 403])


async def test_simulation(c: httpx.AsyncClient, h: dict):
    """Simulation CRUD and control."""
    # Tickers (public)
    r = await c.get(f"{API}/simulation/tickers")
    check("GET /simulation/tickers", r, 200, ["tickers"])

    # Create session
    r = await c.post(f"{API}/simulation/sessions", headers=h, json={
        "ticker": "AAPL", "start_date": "2024-01-01", "end_date": "2024-06-01",
    })
    check("POST /simulation/sessions", r, 200, ["session_id", "ws_url"])
    sid = r.json().get("session_id") if r.status_code == 200 else None

    # Bad dates (schema)
    r = await c.post(f"{API}/simulation/sessions", headers=h, json={
        "ticker": "AAPL", "start_date": "bad", "end_date": "2024-06-01",
    })
    check("POST /simulation/sessions (bad dates)", r, 422)

    # Missing fields (schema)
    r = await c.post(f"{API}/simulation/sessions", headers=h, json={"ticker": "AAPL"})
    check("POST /simulation/sessions (missing)", r, 422)

    # Bad speed (schema)
    r = await c.post(f"{API}/simulation/sessions", headers=h, json={
        "ticker": "AAPL", "start_date": "2024-01-01", "end_date": "2024-06-01",
        "playback_speed": 999,
    })
    check("POST /simulation/sessions (bad speed)", r, 422)

    if sid:
        # State
        r = await c.get(f"{API}/simulation/{sid}/state", headers=h)
        check("GET /simulation/:id/state", r, 200, ["session_id", "status"])

        # Control
        r = await c.post(f"{API}/simulation/{sid}/control", headers=h, json={"action": "pause"})
        check("POST /simulation/:id/control (pause)", r, [200, 400])

        # Bad action (schema)
        r = await c.post(f"{API}/simulation/{sid}/control", headers=h, json={"action": "boom"})
        check("POST /simulation/:id/control (bad)", r, 422)

        # Result
        r = await c.get(f"{API}/simulation/{sid}/result", headers=h)
        check("GET /simulation/:id/result", r, [200, 400, 404])

    # Non-existent session
    r = await c.get(f"{API}/simulation/{uuid.uuid4()}/state", headers=h)
    check("GET /simulation/:id/state (404)", r, [400, 404])

    # No auth
    r = await c.post(f"{API}/simulation/sessions", json={
        "ticker": "AAPL", "start_date": "2024-01-01", "end_date": "2024-06-01",
    })
    check("POST /simulation/sessions (no auth)", r, [401, 403])


async def test_news(c: httpx.AsyncClient):
    """News feed, articles, sentiment - all public."""
    r = await c.get(f"{API}/news/feed")
    check("GET /news/feed", r, 200, ["articles", "total"])

    r = await c.get(f"{API}/news/feed", params={"ticker": "AAPL", "limit": 5})
    check("GET /news/feed?ticker&limit", r, 200)

    r = await c.get(f"{API}/news/article/{uuid.uuid4()}")
    check("GET /news/article/:id (404)", r, 404)

    r = await c.get(f"{API}/news/sentiment/AAPL")
    check("GET /news/sentiment/AAPL", r, 200, ["ticker", "data_points"])

    r = await c.get(f"{API}/news/ticker-sentiment", params={"ticker": "AAPL"})
    check("GET /news/ticker-sentiment", r, 200)


async def test_challenges(c: httpx.AsyncClient, h: dict):
    """Daily challenges + history."""
    r = await c.get(f"{API}/challenges/today", headers=h)
    check("GET /challenges/today", r, [200, 404], detail="200 if challenge exists, 404 if not")

    r = await c.post(f"{API}/challenges/attempt", headers=h, json={
        "challenge_id": str(uuid.uuid4()), "theory_answer": 0,
    })
    check("POST /challenges/attempt (fake)", r, [400, 404])

    r = await c.get(f"{API}/challenges/history", headers=h)
    check("GET /challenges/history", r, 200)

    # Schema validation
    r = await c.post(f"{API}/challenges/attempt", headers=h, json={})
    check("POST /challenges/attempt (no body)", r, 422)

    r = await c.get(f"{API}/challenges/today")
    check("GET /challenges/today (no auth)", r, [401, 403])


async def test_learning(c: httpx.AsyncClient, h: dict):
    """Learning paths, modules, progress."""
    r = await c.get(f"{API}/learning/paths", headers=h)
    check("GET /learning/paths", r, 200)

    r = await c.get(f"{API}/learning/paths/nonexistent-slug", headers=h)
    check("GET /learning/paths/:slug (404)", r, 404)

    r = await c.get(f"{API}/learning/modules/{uuid.uuid4()}", headers=h)
    check("GET /learning/modules/:id (404)", r, 404)

    r = await c.post(f"{API}/learning/modules/{uuid.uuid4()}/complete", headers=h, json={})
    check("POST /learning/modules/:id/complete (404)", r, 404)

    r = await c.get(f"{API}/learning/progress", headers=h)
    check("GET /learning/progress", r, 200, ["total_paths", "overall_progress"])

    r = await c.get(f"{API}/learning/paths")
    check("GET /learning/paths (no auth)", r, [401, 403])


async def test_leaderboard(c: httpx.AsyncClient, h: dict):
    """Leaderboard list + personal rank."""
    r = await c.get(f"{API}/leaderboard/", headers=h)
    check("GET /leaderboard/", r, 200, ["period", "entries", "total_participants"])

    r = await c.get(f"{API}/leaderboard/", headers=h, params={"period": "weekly"})
    check("GET /leaderboard/?period=weekly", r, 200)

    r = await c.get(f"{API}/leaderboard/me", headers=h)
    check("GET /leaderboard/me", r, 200, ["rank", "score"])


async def test_ai_advisor(c: httpx.AsyncClient, h: dict):
    """AI advisor query, conversations, history."""
    r = await c.post(f"{API}/ai-advisor/query", headers=h, json={
        "query": "What is dollar cost averaging?",
    })
    check("POST /ai-advisor/query", r, 200, ["response", "conversation_id"])

    r = await c.post(f"{API}/ai-advisor/query", headers=h, json={
        "query": "How is my portfolio?",
        "include_portfolio": True,
        "include_news": False,
    })
    check("POST /ai-advisor/query (flags)", r, 200)

    # Wrong field name -> 422
    r = await c.post(f"{API}/ai-advisor/query", headers=h, json={"question": "wrong"})
    check("POST /ai-advisor/query (bad field)", r, 422)

    # Empty body -> 422
    r = await c.post(f"{API}/ai-advisor/query", headers=h, json={})
    check("POST /ai-advisor/query (empty)", r, 422)

    r = await c.get(f"{API}/ai-advisor/conversations", headers=h)
    check("GET /ai-advisor/conversations", r, 200)

    r = await c.delete(f"{API}/ai-advisor/history", headers=h)
    check("DELETE /ai-advisor/history", r, 200)

    r = await c.post(f"{API}/ai-advisor/query", json={"query": "hi"})
    check("POST /ai-advisor/query (no auth)", r, [401, 403])


async def test_prediction(c: httpx.AsyncClient, h: dict):
    """AI prediction, explanation, performance."""
    r = await c.post(f"{API}/prediction/predict", headers=h, json={
        "ticker": "AAPL", "horizon": "7d",
    })
    check("POST /prediction/predict", r, 200, ["ticker", "direction", "confidence"])

    r = await c.post(f"{API}/prediction/predict", headers=h, json={"ticker": "TSLA"})
    check("POST /prediction/predict (default horizon)", r, 200)

    r = await c.get(f"{API}/prediction/explain/some-trade-id", headers=h)
    check("GET /prediction/explain/:id", r, 200, ["trade_id", "ai_reasoning"])

    r = await c.get(f"{API}/prediction/performance", headers=h)
    check("GET /prediction/performance", r, 200, ["model_version", "overall_accuracy"])


async def test_community(c: httpx.AsyncClient, h: dict):
    """Community channels and messages."""
    r = await c.get(f"{API}/community/channels", headers=h)
    check("GET /community/channels", r, 200, ["channels"])

    r = await c.get(f"{API}/community/messages/general", headers=h)
    check("GET /community/messages/general", r, 200)

    r = await c.get(f"{API}/community/messages/nonexistent_chan", headers=h)
    check("GET /community/messages/:chan (unknown)", r, [200, 404])


async def test_auth_protection(c: httpx.AsyncClient):
    """All protected routes must reject unauthenticated requests."""
    protected = [
        ("GET",    "/users/me"),
        ("PATCH",  "/users/me"),
        ("GET",    "/gamification/state"),
        ("GET",    "/gamification/xp/history"),
        ("GET",    "/gamification/badges"),
        ("GET",    "/gamification/unlocks"),
        ("GET",    "/portfolio/overview"),
        ("GET",    "/portfolio/risk-metrics"),
        ("GET",    "/portfolio/correlation"),
        ("GET",    "/portfolio/drawdown"),
        ("GET",    "/portfolio/ai-suggestions"),
        ("POST",   "/trading/execute"),
        ("GET",    "/trading/history"),
        ("POST",   "/simulation/sessions"),
        ("GET",    "/challenges/today"),
        ("GET",    "/challenges/history"),
        ("GET",    "/learning/paths"),
        ("GET",    "/learning/progress"),
        ("GET",    "/leaderboard/me"),
        ("POST",   "/ai-advisor/query"),
        ("GET",    "/ai-advisor/conversations"),
        ("DELETE", "/ai-advisor/history"),
        ("POST",   "/prediction/predict"),
    ]

    for method, path in protected:
        url = f"{API}{path}"
        if method == "GET":
            r = await c.get(url)
        elif method == "POST":
            r = await c.post(url, json={})
        elif method == "PATCH":
            r = await c.patch(url, json={})
        elif method == "DELETE":
            r = await c.delete(url)
        else:
            continue
        check(f"AUTH {method} {path}", r, [401, 403, 422])

    # Invalid bearer
    r = await c.get(f"{API}/users/me", headers={"Authorization": "Bearer invalid.jwt"})
    check("AUTH invalid bearer token", r, [401, 403])

    # Expired token
    try:
        import time
        from jose import jwt as jose_jwt
        from backend.core.config import get_settings
        s = get_settings()
        expired = jose_jwt.encode(
            {"sub": TEST_USER_ID, "type": "access", "exp": int(time.time()) - 3600},
            s.jwt_secret_key, algorithm=s.jwt_algorithm,
        )
        r = await c.get(f"{API}/users/me", headers={"Authorization": f"Bearer {expired}"})
        check("AUTH expired token", r, [401, 403])
    except Exception as e:
        suite.record("AUTH expired token", False, detail=f"setup error: {e}")


# ===================================================================
#  Main runner
# ===================================================================


async def run_all_tests():
    """Run every test group sequentially."""
    token = get_auth_token()
    h = {"Authorization": f"Bearer {token}"}

    # Verify server is reachable
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as c:
        try:
            r = await c.get("/health")
            if r.status_code != 200:
                print(f"ERROR: Server returned {r.status_code} on /health")
                return False
        except httpx.ConnectError:
            print("ERROR: Cannot connect to server. Is it running on port 8000?")
            print("  Start with:  uvicorn backend.main:app --reload --port 8000")
            return False

    print("Server is running. Creating test user...")
    await create_test_user()
    print(f"Test user '{TEST_USERNAME}' ready.\n")

    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as c:
            print("Running tests...\n")
            await test_health(c)
            await test_auth(c)
            await test_users(c, h)
            await test_gamification(c, h)
            await test_portfolio(c, h)
            await test_trading(c, h)
            await test_simulation(c, h)
            await test_news(c)
            await test_challenges(c, h)
            await test_learning(c, h)
            await test_leaderboard(c, h)
            await test_ai_advisor(c, h)
            await test_prediction(c, h)
            await test_community(c, h)
            await test_auth_protection(c)
    finally:
        print("\nCleaning up test user...")
        await destroy_test_user()
        print("Cleanup complete.")

    suite.print_report()
    return suite.failed == 0


# ===================================================================
#  Pytest compatibility  (run with: pytest tests/test_all_apis.py -v)
# ===================================================================


try:
    import pytest

    @pytest.fixture(scope="module")
    def _run_suite():
        """Run the full suite once per module and cache the result."""
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        loop = asyncio.new_event_loop()
        try:
            all_passed = loop.run_until_complete(run_all_tests())
        finally:
            loop.close()
        return all_passed

    def test_all_apis(_run_suite):
        """Single pytest entry point that runs the full async suite."""
        assert _run_suite, f"{suite.failed} API test(s) failed - see output above"

except ImportError:
    pass  # pytest not installed; standalone mode only


# ===================================================================
#  Standalone entry point  (run with: python tests/test_all_apis.py)
# ===================================================================

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    all_passed = asyncio.run(run_all_tests())
    sys.exit(0 if all_passed else 1)
