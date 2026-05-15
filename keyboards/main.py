from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from utils.i18n import t


def main_menu(i18n: dict[str, str]) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text=t(i18n, "menu.create"))
    kb.button(text=t(i18n, "menu.edit"))
    kb.button(text=t(i18n, "menu.settings"))
    kb.button(text=t(i18n, "menu.balance"))
    kb.button(text=t(i18n, "menu.history"))
    kb.button(text=t(i18n, "menu.favorites"))
    kb.button(text=t(i18n, "menu.help"))
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup(resize_keyboard=True)
