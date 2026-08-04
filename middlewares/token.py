from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from services.database import get_user_token
from services.pollinations import current_token


class TokenMiddleware(BaseMiddleware):
    """Bind the user's own Pollinations key to this update.

    Nothing here runs on the owner's balance: no key -> the client raises
    TokenRequired and errors.py tells the user to run /token.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        token = await get_user_token(user.id) if user is not None else None
        current_token.set(token)
        data["pollinations_token"] = token
        return await handler(event, data)
