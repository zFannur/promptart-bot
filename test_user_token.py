"""Self-check: nothing calls Pollinations without the *user's* own key.

Run: python test_user_token.py
"""
import asyncio
import os
import tempfile

os.environ.setdefault("BOT_TOKEN", "0" * 25)
os.environ.setdefault("ADMIN_ID", "1")
os.environ["POLLINATIONS_API_KEY"] = ""
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "t.db")

import bot as _bot  # noqa: F401,E402  - import-time wiring must not explode
from config import settings  # noqa: E402
from services import database as db  # noqa: E402
from services.pollinations import TokenRequired, current_token, pollinations  # noqa: E402


async def main() -> None:
    assert settings.pollinations_api_key == "", "owner key must default to empty"

    # No token bound -> every API call refuses instead of billing the owner.
    current_token.set(None)
    try:
        _ = pollinations._headers
        raise AssertionError("expected TokenRequired")
    except TokenRequired:
        pass

    current_token.set("user-key-123")
    assert pollinations._headers == {"Authorization": "Bearer user-key-123"}

    # Round-trip through the DB, including the clear path.
    await db.init_db()
    await db.upsert_user(telegram_id=42, username="u", language="en")
    assert await db.get_user_token(42) is None
    await db.set_user_token(42, "abc")
    assert await db.get_user_token(42) == "abc"
    await db.set_user_token(42, None)
    assert await db.get_user_token(42) is None

    # Two users must never see each other's key.
    async def as_user(key):
        current_token.set(key)
        await asyncio.sleep(0)
        return pollinations._headers["Authorization"]

    a, b = await asyncio.gather(as_user("key-a"), as_user("key-b"))
    assert a == "Bearer key-a" and b == "Bearer key-b", (a, b)

    await pollinations.close()
    print("ok")


if __name__ == "__main__":
    asyncio.run(main())
