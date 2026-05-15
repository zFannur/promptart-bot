import asyncio
import os
import sys
from pathlib import Path

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


def warn_if_db_ephemeral() -> None:
    """Loudly warn at startup if the configured DB path will not survive a
    container redeploy. Railway / Render / Fly etc. wipe the working tree
    on every deploy unless an explicit persistent Volume is mounted.

    Heuristic: any RELATIVE path on Linux is suspicious. Also a path under
    /tmp or /app (the Railway working tree). A path under /data, /var/lib,
    or any user-set absolute path outside those traps is assumed persistent.
    """
    db_path = Path(settings.db_path).resolve()
    on_container = sys.platform.startswith("linux") and (
        os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("PORT") or os.path.exists("/.dockerenv")
    )
    suspicious_prefixes = ("/app/", "/tmp/", "/workspace/")
    raw = settings.db_path
    is_relative = not os.path.isabs(raw)
    is_ephemeral_dir = any(str(db_path).startswith(p) for p in suspicious_prefixes)

    if on_container and (is_relative or is_ephemeral_dir):
        logger.warning("=" * 60)
        logger.warning("⚠️  DB_PATH={} looks EPHEMERAL", db_path)
        logger.warning("    Container filesystems are wiped on redeploy.")
        logger.warning("    Mount a persistent Railway Volume and set")
        logger.warning("    DB_PATH=/data/bot.db (or similar absolute path)")
        logger.warning("    See README.md → 'Railway deployment' for steps.")
        logger.warning("=" * 60)


async def main() -> None:
    setup_logging()
    warn_if_db_ephemeral()
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
