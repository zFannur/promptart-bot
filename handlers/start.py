from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from keyboards.main import main_menu
from services.database import upsert_user
from utils.i18n import detect_lang, t
from utils.menu import HELP_LABELS

router = Router(name=__name__)


@router.message(CommandStart())
async def cmd_start(message: Message, i18n: dict[str, str]) -> None:
    if message.from_user is None:
        return
    lang = detect_lang(message.from_user.language_code)
    await upsert_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        language=lang,
    )
    await message.answer(
        t(i18n, "start.welcome", name=message.from_user.first_name or "👋"),
        reply_markup=main_menu(i18n),
    )


@router.message(Command("help"))
@router.message(F.text.in_(HELP_LABELS))
async def cmd_help(message: Message, i18n: dict[str, str]) -> None:
    bot = await message.bot.get_me() if message.bot else None
    username = bot.username if bot else "bot"
    await message.answer(
        t(i18n, "start.help", bot_username=username),
        reply_markup=main_menu(i18n),
    )
