from collections import defaultdict
from time import monotonic
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from utils.i18n import t


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, limit: int = 5, window: int = 60) -> None:
        self.limit = limit
        self.window = window
        self._buckets: dict[int, list[float]] = defaultdict(list)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or not event.text:
            return await handler(event, data)

        if not event.text.startswith("🎨") and not event.text.startswith("/"):
            return await handler(event, data)

        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        now = monotonic()
        bucket = self._buckets[user.id]
        bucket[:] = [ts for ts in bucket if now - ts < self.window]

        if len(bucket) >= self.limit:
            wait = max(1, int(self.window - (now - bucket[0])))
            i18n = data.get("i18n", {})
            await event.answer(t(i18n, "generation.rate_limit", sec=wait))
            return None

        bucket.append(now)
        return await handler(event, data)
