from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from services.pollinations import BalanceUnavailable, pollinations
from utils.i18n import t
from utils.menu import BALANCE_LABELS
from utils.models import format_price

router = Router(name=__name__)


@router.message(Command("balance"))
@router.message(F.text.in_(BALANCE_LABELS))
async def cmd_balance(message: Message, i18n: dict[str, str]) -> None:
    if message.from_user is None:
        return

    bal = await pollinations.get_balance()
    if isinstance(bal, BalanceUnavailable):
        if bal.reason == "missing_permission":
            await message.answer(t(i18n, "balance.help_permission"))
        else:
            await message.answer(t(i18n, "balance.unavailable_generic"))
        return

    usage_count = await pollinations.get_usage_count_24h()

    lines = [t(i18n, "balance.current", balance=format_price(bal))]
    if usage_count is not None:
        lines.append(t(i18n, "balance.usage_24h", count=usage_count))
    await message.answer("\n".join(lines), disable_web_page_preview=True)
