from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from utils.i18n import t

# Where users actually create a Pollinations key. NOTE: auth.pollinations.ai
# (used here before) has no DNS record at all — every "get your key" link was
# dead, which is why nobody figured out they needed one.
KEY_PORTAL_URL = "https://enter.pollinations.ai"


def main_menu(i18n: dict[str, str]) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text=t(i18n, "menu.create_image"))
    kb.button(text=t(i18n, "menu.create_video"))
    kb.button(text=t(i18n, "menu.create_audio"))
    kb.button(text=t(i18n, "menu.chat"))
    kb.button(text=t(i18n, "menu.edit"))
    kb.button(text=t(i18n, "menu.settings"))
    kb.button(text=t(i18n, "menu.balance"))
    kb.button(text=t(i18n, "menu.history"))
    kb.button(text=t(i18n, "menu.favorites"))
    kb.button(text=t(i18n, "menu.help"))
    kb.adjust(2, 2, 2, 2, 2)
    return kb.as_markup(resize_keyboard=True)


def get_key_button(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    """One-tap link to the key portal, attached to every "you need a key" reply."""
    kb = InlineKeyboardBuilder()
    kb.button(text=t(i18n, "token.get_key_button"), url=KEY_PORTAL_URL)
    return kb.as_markup()


def chat_keyboard(i18n: dict[str, str]) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text=t(i18n, "menu.clear_context"))
    kb.button(text=t(i18n, "menu.back_to_menu"))
    kb.adjust(1, 1)
    return kb.as_markup(resize_keyboard=True)
