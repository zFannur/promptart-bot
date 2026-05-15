from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from loguru import logger

from keyboards.settings import models_kb, ratios_kb, settings_menu, styles_kb
from services.database import get_user, update_user_setting
from services.pollinations import BalanceUnavailable, ModelInfo, pollinations
from utils.aspect_ratios import RATIOS_BY_KEY
from utils.i18n import t
from utils.menu import SETTINGS_LABELS
from utils.models import format_price
from utils.styles import STYLES_BY_KEY

router = Router(name=__name__)


def _format_settings(user, model_by_key: dict[str, ModelInfo], i18n: dict[str, str]) -> str:
    model_info = model_by_key.get(user.model)
    model_label = (
        f"{user.model} · {format_price(model_info.price_pollen)}"
        if model_info else user.model
    )
    ratio_label = RATIOS_BY_KEY[user.aspect_ratio].label if user.aspect_ratio in RATIOS_BY_KEY else user.aspect_ratio
    if user.style and user.style in STYLES_BY_KEY:
        s = STYLES_BY_KEY[user.style]
        style_label = f"{s.emoji} {t(i18n, s.label_key)}"
    else:
        style_label = t(i18n, "settings.style_none")
    return t(i18n, "settings.title", model=model_label, ratio=ratio_label, style=style_label)


async def _balance_line(i18n: dict[str, str]) -> str:
    bal = await pollinations.get_balance()
    if isinstance(bal, BalanceUnavailable):
        if bal.reason == "missing_permission":
            return t(i18n, "balance.unavailable_permission")
        return t(i18n, "balance.unavailable_generic")
    return t(i18n, "balance.line", balance=format_price(bal))


async def _models_index() -> tuple[list[ModelInfo], dict[str, ModelInfo]]:
    models = await pollinations.list_image_models()
    return models, {m.name: m for m in models}


@router.message(Command("settings"))
@router.message(F.text.in_(SETTINGS_LABELS))
async def open_settings(message: Message, i18n: dict[str, str]) -> None:
    if message.from_user is None:
        return
    user = await get_user(message.from_user.id)
    if user is None:
        return
    _, by_key = await _models_index()
    await message.answer(_format_settings(user, by_key, i18n), reply_markup=settings_menu(i18n))


@router.callback_query(F.data == "set:back")
async def cb_back(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.from_user is None or cb.message is None:
        return
    user = await get_user(cb.from_user.id)
    if user is None:
        return
    _, by_key = await _models_index()
    await cb.message.edit_text(_format_settings(user, by_key, i18n), reply_markup=settings_menu(i18n))


@router.callback_query(F.data == "set:model")
async def cb_pick_model(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.from_user is None or cb.message is None:
        return
    user = await get_user(cb.from_user.id)
    if user is None:
        return
    models, _ = await _models_index()
    balance_line = await _balance_line(i18n)
    header = t(i18n, "settings.choose_model_header", balance=balance_line)
    await cb.message.edit_text(header, reply_markup=models_kb(user.model, models, i18n))


@router.callback_query(F.data == "set:ratio")
async def cb_pick_ratio(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.from_user is None or cb.message is None:
        return
    user = await get_user(cb.from_user.id)
    if user is None:
        return
    await cb.message.edit_text(t(i18n, "settings.choose_ratio"), reply_markup=ratios_kb(user.aspect_ratio, i18n))


@router.callback_query(F.data == "set:style")
async def cb_pick_style(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.from_user is None or cb.message is None:
        return
    user = await get_user(cb.from_user.id)
    if user is None:
        return
    await cb.message.edit_text(t(i18n, "settings.choose_style"), reply_markup=styles_kb(user.style, i18n))


@router.callback_query(F.data.startswith("setval:"))
async def cb_set_value(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    if cb.from_user is None or cb.message is None or cb.data is None:
        await cb.answer()
        return
    _, field, value = cb.data.split(":", 2)

    if field == "model":
        _, by_key = await _models_index()
        if value not in by_key:
            await cb.answer()
            return
    elif field == "ratio" and value not in RATIOS_BY_KEY:
        await cb.answer()
        return
    elif field == "style" and value != "none" and value not in STYLES_BY_KEY:
        await cb.answer()
        return

    db_field = "aspect_ratio" if field == "ratio" else field
    db_value = None if (field == "style" and value == "none") else value
    try:
        await update_user_setting(cb.from_user.id, db_field, db_value)
    except ValueError as e:
        logger.warning("invalid setting update: {}", e)
        await cb.answer()
        return

    await cb.answer(t(i18n, "settings.saved"))
    user = await get_user(cb.from_user.id)
    if user is None:
        return
    _, by_key = await _models_index()
    await cb.message.edit_text(_format_settings(user, by_key, i18n), reply_markup=settings_menu(i18n))
