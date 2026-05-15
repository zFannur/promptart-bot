import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger

from config import settings
from handlers import balance, edit, errors, generation, history, settings as settings_h, start
from middlewares.i18n import I18nMiddleware
from middlewares.ratelimit import RateLimitMiddleware
from services.database import init_db
from services.pollinations import pollinations


def setup_logging() -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
    )


async def main() -> None:
    setup_logging()
    await init_db()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    i18n_mw = I18nMiddleware()
    dp.message.middleware(i18n_mw)
    dp.callback_query.middleware(i18n_mw)
    dp.message.middleware(RateLimitMiddleware(
        limit=settings.rate_limit_per_minute,
        window=60,
    ))

    dp.include_router(start.router)
    dp.include_router(settings_h.router)
    dp.include_router(history.router)
    dp.include_router(balance.router)
    # edit goes BEFORE generation: generation has an F.text fallback that
    # would swallow any text typed while in EditStates.collecting.
    dp.include_router(edit.router)
    dp.include_router(generation.router)
    dp.include_router(errors.router)

    me = await bot.get_me()
    logger.info("Bot @{} started", me.username)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await pollinations.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
