from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from services.database import get_user_lang, upsert_user
from utils.i18n import DEFAULT_LANG, detect_lang, load_locale


class I18nMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if user is not None:
            stored = await get_user_lang(user.id)
            if stored is None:
                await upsert_user(
                    telegram_id=user.id,
                    username=user.username,
                    language=detect_lang(user.language_code),
                )
        data["i18n"] = load_locale(DEFAULT_LANG)
        return await handler(event, data)
