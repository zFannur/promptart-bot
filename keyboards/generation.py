from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.i18n import t


def post_gen_kb(gen_id: int, is_fav: bool, i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return post_media_kb(gen_id, is_fav, i18n, "image")


def post_media_kb(gen_id: int, is_fav: bool, i18n: dict[str, str], kind: str = "image") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t(i18n, "buttons.again"), callback_data=f"regen:{gen_id}")
    if kind == "image":
        kb.button(text=t(i18n, "buttons.enhance"), callback_data=f"enh:{gen_id}")
        kb.button(text=t(i18n, "buttons.edit_this"), callback_data=f"edit_gen:{gen_id}")
    fav_label = "✅ " + t(i18n, "buttons.favorite") if is_fav else t(i18n, "buttons.favorite")
    kb.button(text=fav_label, callback_data=f"fav:{gen_id}")
    if kind == "image":
        kb.button(text=t(i18n, "buttons.save_prompt"), callback_data=f"save_pr:{gen_id}")
        kb.adjust(2, 2, 1)
    else:
        kb.adjust(2)
    return kb.as_markup()


def confirm_enhance_kb(gen_id: int, i18n: dict[str, str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t(i18n, "buttons.apply"), callback_data=f"enh_apply:{gen_id}")
    kb.button(text=t(i18n, "buttons.cancel"), callback_data="enh_cancel")
    kb.adjust(2)
    return kb.as_markup()


def history_item_kb(gen_id: int, i18n: dict[str, str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t(i18n, "buttons.again"), callback_data=f"regen:{gen_id}")
    kb.button(text=t(i18n, "buttons.edit_this"), callback_data=f"edit_gen:{gen_id}")
    kb.adjust(2)
    return kb.as_markup()


def prompt_options_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t(i18n, "buttons.saved_prompts"), callback_data="prompt_menu:saved")
    kb.button(text=t(i18n, "buttons.trending"), callback_data="prompt_menu:trending")
    kb.button(text=t(i18n, "buttons.prompt_builder"), callback_data="prompt_menu:builder")
    kb.adjust(1)
    return kb.as_markup()
