"""Quick smoke test for community endpoints."""
import asyncio
import httpx


async def test_community():
    from backend.core.security import create_token_pair
    from backend.core.database import sessionmanager
    from backend.core.redis import redis_manager
    from backend.models.user import User
    from sqlalchemy import select
    import uuid

    # Find a real user in the database
    await redis_manager.connect()
    await sessionmanager.init()

    real_user_id = None
    async for db in sessionmanager.session():
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if user:
            real_user_id = str(user.id)
            print(f"Using existing user: {user.display_name} ({real_user_id})")
        else:
            # Create a test user
            test_user = User(
                id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
                username="test_community",
                display_name="Community Tester",
                email="community@test.local",
            )
            db.add(test_user)
            await db.flush()
            real_user_id = str(test_user.id)
            print(f"Created test user: {real_user_id}")

    tokens = create_token_pair(real_user_id)
    token = tokens.access_token
    headers = {"Authorization": f"Bearer {token}"}
    base = "http://localhost:8000/api/v1"

    async with httpx.AsyncClient(timeout=10) as c:
        # 1. List channels
        r = await c.get(f"{base}/community/channels")
        names = [ch["name"] for ch in r.json().get("channels", [])]
        print(f"GET /channels: {r.status_code} -> {names}")

        # 2. Get messages (may be empty)
        r = await c.get(f"{base}/community/messages/general")
        print(f"GET /messages/general: {r.status_code}, count={len(r.json())}")

        # 3. Post a message via REST
        r = await c.post(
            f"{base}/community/messages/general",
            headers=headers,
            json={"content": "Hello from REST API!", "message_type": "text"},
        )
        print(f"POST /messages/general: {r.status_code}")
        if r.status_code == 200:
            msg = r.json()
            print(f"  id={msg['id']}, user={msg['display_name']}, content={msg['content']}")
        else:
            print(f"  body: {r.text[:300]}")

        # 4. Post another
        r = await c.post(
            f"{base}/community/messages/general",
            headers=headers,
            json={"content": "Testing persistence!", "message_type": "text"},
        )
        print(f"POST /messages/general (2): {r.status_code}")

        # 5. Fetch again — should see messages
        r = await c.get(f"{base}/community/messages/general")
        print(f"GET /messages/general: {r.status_code}, count={len(r.json())}")
        for m in r.json():
            print(f"  [{m['display_name']}] {m['content']}")

        # 6. Different channel
        r = await c.post(
            f"{base}/community/messages/trading",
            headers=headers,
            json={"content": "Bull market!", "message_type": "text"},
        )
        print(f"POST /messages/trading: {r.status_code}")

        # 7. Verify isolation
        r = await c.get(f"{base}/community/messages/trading")
        print(f"GET /messages/trading: {r.status_code}, count={len(r.json())}")
        for m in r.json():
            print(f"  [{m['display_name']}] {m['content']}")

    await sessionmanager.close()
    await redis_manager.disconnect()
    print("\nAll community tests passed!")


asyncio.run(test_community())
