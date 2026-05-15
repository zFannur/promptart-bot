from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.i18n import t


def edit_cancel_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t(i18n, "buttons.cancel"), callback_data="edit:cancel")
    kb.adjust(1)
    return kb.as_markup()
