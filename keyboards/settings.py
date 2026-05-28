from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.pollinations import ModelInfo
from utils.aspect_ratios import RATIOS
from utils.i18n import t
from utils.models import format_price
from utils.styles import STYLES


def settings_menu(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎨 Image Settings", callback_data="set:image_menu")
    kb.button(text="🎥 Video Settings", callback_data="set:video_menu")
    kb.button(text="🔊 Audio Settings", callback_data="set:audio_menu")
    kb.button(text="💬 Chat Settings", callback_data="set:text_menu")
    kb.adjust(2, 2)
    return kb.as_markup()


def image_settings_menu(i18n: dict[str, str], model_name: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🤖 Image Model", callback_data="set:model")
    kb.button(text="📐 Aspect Ratio", callback_data="set:ratio")
    kb.button(text="🎨 Style", callback_data="set:style")
    kb.button(text="🛠 Edit Model", callback_data="set:edit_model")
    
    if model_name.startswith("gptimage") or model_name.startswith("gpt-image"):
        kb.button(text=t(i18n, "settings.image_quality"), callback_data="set:image_quality")
        kb.button(text=t(i18n, "settings.image_transparent"), callback_data="set:image_transparent")
        
    kb.button(text=t(i18n, "buttons.back"), callback_data="set:back")
    
    if model_name.startswith("gptimage") or model_name.startswith("gpt-image"):
        kb.adjust(2, 2, 2, 1)
    else:
        kb.adjust(2, 2, 1)
    return kb.as_markup()


def video_settings_menu(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🤖 Video Model", callback_data="set:video_model")
    kb.button(text="📐 Aspect Ratio", callback_data="set:video_ratio")
    kb.button(text="⏱ Duration", callback_data="set:video_duration")
    kb.button(text=t(i18n, "buttons.back"), callback_data="set:back")
    kb.adjust(1)
    return kb.as_markup()


def audio_settings_menu(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🤖 Audio Model", callback_data="set:audio_model")
    kb.button(text="🗣 Voice", callback_data="set:audio_voice")
    kb.button(text=t(i18n, "buttons.back"), callback_data="set:back")
    kb.adjust(1)
    return kb.as_markup()


def text_settings_menu(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🤖 Chat Model", callback_data="set:text_model")
    kb.button(text=t(i18n, "buttons.back"), callback_data="set:back")
    kb.adjust(1)
    return kb.as_markup()


def models_kb(
    current: str,
    models: list[ModelInfo],
    i18n: dict[str, str],
    *,
    field: str = "model",
    back_route: str = "set:image_menu",
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for m in models:
        mark = "✅ " if m.name == current else ""
        paid_tag = " [paid]" if getattr(m, "paid_only", False) else ""
        
        # Format the price based on modality / unit
        if "video" in field:
            price_str = f"{format_price(m.price_pollen)}/s"
        elif "audio" in field:
            price_str = f"{format_price(m.price_pollen)}/s"
        elif "text" in field:
            price_str = f"{format_price(m.price_pollen)}/1K"
        else:
            price_str = format_price(m.price_pollen)
            
        kb.button(
            text=f"{mark}{m.name}{paid_tag} · {price_str}",
            callback_data=f"setval:{field}:{m.name}",
        )
    kb.button(text=t(i18n, "buttons.back"), callback_data=back_route)
    kb.adjust(1)
    return kb.as_markup()


def ratios_kb(current: str, i18n: dict[str, str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for r in RATIOS:
        mark = "✅ " if r.key == current else ""
        kb.button(text=f"{mark}{r.label}", callback_data=f"setval:ratio:{r.key}")
    kb.button(text=t(i18n, "buttons.back"), callback_data="set:image_menu")
    kb.adjust(3, 2, 1)
    return kb.as_markup()


def styles_kb(current: str | None, i18n: dict[str, str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    none_mark = "✅ " if not current else ""
    kb.button(text=f"{none_mark}{t(i18n, 'style.none')}", callback_data="setval:style:none")
    for s in STYLES:
        mark = "✅ " if s.key == current else ""
        kb.button(text=f"{mark}{s.emoji} {t(i18n, s.label_key)}", callback_data=f"setval:style:{s.key}")
    kb.button(text=t(i18n, "buttons.back"), callback_data="set:image_menu")
    kb.adjust(1)
    return kb.as_markup()


def video_ratios_kb(current: str, i18n: dict[str, str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for r in ["16:9", "9:16", "1:1"]:
        mark = "✅ " if r == current else ""
        kb.button(text=f"{mark}{r}", callback_data=f"setval:video_aspect_ratio:{r}")
    kb.button(text=t(i18n, "buttons.back"), callback_data="set:video_menu")
    kb.adjust(3, 1)
    return kb.as_markup()


def video_durations_kb(current: int, i18n: dict[str, str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for d in [3, 5, 8, 10]:
        mark = "✅ " if d == current else ""
        kb.button(text=f"{mark}{d}s", callback_data=f"setval:video_duration:{d}")
    kb.button(text=t(i18n, "buttons.back"), callback_data="set:video_menu")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def audio_voices_kb(current: str, i18n: dict[str, str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for v in ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]:
        mark = "✅ " if v == current else ""
        kb.button(text=f"{mark}{v}", callback_data=f"setval:audio_voice:{v}")
    kb.button(text=t(i18n, "buttons.back"), callback_data="set:audio_menu")
    kb.adjust(3, 3, 1)
    return kb.as_markup()


def image_quality_kb(current: str, i18n: dict[str, str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for q in ["medium", "high", "hd"]:
        mark = "✅ " if q == current else ""
        kb.button(text=f"{mark}{q.capitalize()}", callback_data=f"setval:image_quality:{q}")
    kb.button(text=t(i18n, "buttons.back"), callback_data="set:image_menu")
    kb.adjust(3, 1)
    return kb.as_markup()


def image_transparent_kb(current: int, i18n: dict[str, str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    # On (1)
    on_mark = "✅ " if current == 1 else ""
    kb.button(text=f"{on_mark}{t(i18n, 'settings.transparency_on')}", callback_data=f"setval:image_transparent:1")
    # Off (0)
    off_mark = "✅ " if current == 0 else ""
    kb.button(text=f"{off_mark}{t(i18n, 'settings.transparency_off')}", callback_data=f"setval:image_transparent:0")
    kb.button(text=t(i18n, "buttons.back"), callback_data="set:image_menu")
    kb.adjust(2, 1)
    return kb.as_markup()
