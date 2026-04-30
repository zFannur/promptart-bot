from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from services.database import get_user_lang
from utils.i18n import DEFAULT_LANG, detect_lang, load_locale


class I18nMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        lang = DEFAULT_LANG
        if user is not None:
            stored = await get_user_lang(user.id)
            lang = stored or detect_lang(user.language_code)
        data["lang"] = lang
        data["i18n"] = load_locale(lang)
        return await handler(event, data)
