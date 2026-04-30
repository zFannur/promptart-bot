from aiogram import Router
from aiogram.types import ErrorEvent
from loguru import logger

from services.database import get_user_lang
from utils.i18n import detect_lang, load_locale, t

router = Router(name=__name__)


@router.errors()
async def error_handler(event: ErrorEvent) -> None:
    update_id = event.update.update_id if event.update else "?"
    logger.exception("Update {} caused error: {}", update_id, event.exception)

    msg = event.update.message if event.update else None
    if msg is None or msg.from_user is None:
        return

    try:
        stored = await get_user_lang(msg.from_user.id)
        lang = stored or detect_lang(msg.from_user.language_code)
        i18n = load_locale(lang)
        await msg.answer(t(i18n, "errors.generic"))
    except Exception:
        pass
