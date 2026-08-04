from aiogram import Router
from aiogram.types import ErrorEvent
from loguru import logger

from services.database import get_user_lang
from services.pollinations import TokenRequired
from utils.i18n import detect_lang, load_locale, t

router = Router(name=__name__)


@router.errors()
async def error_handler(event: ErrorEvent) -> None:
    update_id = event.update.update_id if event.update else "?"
    no_token = isinstance(event.exception, TokenRequired)
    if no_token:
        logger.info("Update {} needs a user Pollinations token", update_id)
    else:
        logger.exception("Update {} caused error: {}", update_id, event.exception)

    upd = event.update
    msg = upd.message if upd else None
    if msg is None and upd is not None and upd.callback_query is not None:
        msg = upd.callback_query.message
    if msg is None:
        return
    from_user = (upd.callback_query.from_user if upd and upd.callback_query else None) or msg.from_user
    if from_user is None:
        return

    try:
        stored = await get_user_lang(from_user.id)
        lang = stored or detect_lang(from_user.language_code)
        i18n = load_locale(lang)
        await msg.answer(
            t(i18n, "token.required" if no_token else "errors.generic"),
            disable_web_page_preview=True,
        )
    except Exception:
        pass
