from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from loguru import logger

from keyboards.main import get_key_button
from services.database import get_user_token, set_user_token
from services.pollinations import BalanceUnavailable, current_token, pollinations
from utils.i18n import t

router = Router(name=__name__)


@router.message(Command("token"))
async def cmd_token(message: Message, command: CommandObject, i18n: dict[str, str]) -> None:
    if message.from_user is None:
        return
    arg = (command.args or "").strip()

    if not arg:
        stored = await get_user_token(message.from_user.id)
        key = "token.status_set" if stored else "token.status_none"
        await message.answer(
            t(i18n, key, masked=_mask(stored)),
            disable_web_page_preview=True,
            reply_markup=None if stored else get_key_button(i18n),
        )
        return

    if arg.lower() in ("delete", "remove", "clear", "off"):
        await set_user_token(message.from_user.id, None)
        current_token.set(None)
        await message.answer(t(i18n, "token.deleted"))
        return

    # The key travels through Telegram in plaintext; drop it from the chat as
    # soon as it is stored. Silently ignored if the bot lacks delete rights.
    try:
        await message.delete()
    except Exception as exc:  # noqa: BLE001 - deletion is best-effort
        logger.debug("could not delete /token message: {}", exc)

    # The key ends up in an HTTP header, and headers are ASCII-only. Sending
    # e.g. a Cyrillic word blew up inside httpx with UnicodeEncodeError, which
    # surfaced to the user as a generic "something went wrong". Catch it here
    # and say what is actually wrong instead of making a doomed API call.
    if not _looks_like_key(arg):
        await message.answer(
            t(i18n, "token.malformed"),
            disable_web_page_preview=True,
            reply_markup=get_key_button(i18n),
        )
        return

    current_token.set(arg)
    bal = await pollinations.get_balance()
    if isinstance(bal, BalanceUnavailable) and bal.reason == "unauthorized":
        current_token.set(None)
        await message.answer(
            t(i18n, "token.invalid"),
            disable_web_page_preview=True,
            reply_markup=get_key_button(i18n),
        )
        return

    await set_user_token(message.from_user.id, arg)
    await message.answer(t(i18n, "token.saved", masked=_mask(arg)), disable_web_page_preview=True)


def _looks_like_key(value: str) -> bool:
    """A Pollinations key is a plain ASCII token with no whitespace."""
    return value.isascii() and value.isprintable() and not any(c.isspace() for c in value)


def _mask(token: str | None) -> str:
    if not token:
        return "—"
    return f"{token[:4]}…{token[-4:]}" if len(token) > 10 else "…"
