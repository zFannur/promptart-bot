from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.pollinations import ModelInfo
from utils.aspect_ratios import RATIOS
from utils.i18n import t
from utils.models import format_price
from utils.styles import STYLES


def settings_menu(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t(i18n, "settings.model"), callback_data="set:model")
    kb.button(text=t(i18n, "settings.ratio"), callback_data="set:ratio")
    kb.button(text=t(i18n, "settings.style"), callback_data="set:style")
    kb.adjust(1)
    return kb.as_markup()


def models_kb(
    current: str,
    models: list[ModelInfo],
    i18n: dict[str, str],
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for m in models:
        mark = "✅ " if m.name == current else ""
        kb.button(
            text=f"{mark}{m.name} · {format_price(m.price_pollen)}",
            callback_data=f"setval:model:{m.name}",
        )
    kb.button(text=t(i18n, "buttons.back"), callback_data="set:back")
    kb.adjust(1)
    return kb.as_markup()


def ratios_kb(current: str, i18n: dict[str, str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for r in RATIOS:
        mark = "✅ " if r.key == current else ""
        kb.button(text=f"{mark}{r.label}", callback_data=f"setval:ratio:{r.key}")
    kb.button(text=t(i18n, "buttons.back"), callback_data="set:back")
    kb.adjust(3, 2, 1)
    return kb.as_markup()


def styles_kb(current: str | None, i18n: dict[str, str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    none_mark = "✅ " if not current else ""
    kb.button(text=f"{none_mark}{t(i18n, 'style.none')}", callback_data="setval:style:none")
    for s in STYLES:
        mark = "✅ " if s.key == current else ""
        kb.button(text=f"{mark}{s.emoji} {t(i18n, s.label_key)}", callback_data=f"setval:style:{s.key}")
    kb.button(text=t(i18n, "buttons.back"), callback_data="set:back")
    kb.adjust(1)
    return kb.as_markup()
