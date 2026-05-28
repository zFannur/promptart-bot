from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from loguru import logger

from keyboards.settings import (
    settings_menu,
    image_settings_menu,
    video_settings_menu,
    audio_settings_menu,
    text_settings_menu,
    models_kb,
    ratios_kb,
    styles_kb,
    video_ratios_kb,
    video_durations_kb,
    audio_voices_kb,
)
from services.database import get_user, update_user_setting
from services.pollinations import BalanceUnavailable, ModelInfo, pollinations
from utils.aspect_ratios import RATIOS_BY_KEY
from utils.i18n import t
from utils.menu import SETTINGS_LABELS
from utils.models import format_price
from utils.styles import STYLES_BY_KEY

router = Router(name=__name__)


def _format_settings(user, model_by_key: dict[str, ModelInfo], i18n: dict[str, str], mode: str = "main") -> str:
    def fmt_model(m_key):
        info = model_by_key.get(m_key)
        return f"{m_key} · {format_price(info.price_pollen)}" if info else m_key

    if mode == "main":
        return t(
            i18n,
            "settings.main_title",
            model=fmt_model(user.model),
            ratio=user.aspect_ratio,
            style=user.style or t(i18n, "settings.style_none"),
            video_model=fmt_model(user.video_model),
            video_ratio=user.video_aspect_ratio,
            video_duration=user.video_duration,
            audio_model=fmt_model(user.audio_model),
            audio_voice=user.audio_voice,
            text_model=fmt_model(user.text_model),
        )
    elif mode == "image":
        model_info = model_by_key.get(user.model)
        model_label = f"{user.model} · {format_price(model_info.price_pollen)}" if model_info else user.model
        edit_info = model_by_key.get(user.edit_model)
        edit_label = f"{user.edit_model} · {format_price(edit_info.price_pollen)}" if edit_info else user.edit_model
        ratio_label = RATIOS_BY_KEY[user.aspect_ratio].label if user.aspect_ratio in RATIOS_BY_KEY else user.aspect_ratio
        if user.style and user.style in STYLES_BY_KEY:
            s = STYLES_BY_KEY[user.style]
            style_label = f"{s.emoji} {t(i18n, s.label_key)}"
        else:
            style_label = t(i18n, "settings.style_none")
        return t(
            i18n,
            "settings.image_title",
            model=model_label,
            edit_model=edit_label,
            ratio=ratio_label,
            style=style_label,
        )
    elif mode == "video":
        return t(
            i18n,
            "settings.video_title",
            video_model=fmt_model(user.video_model),
            video_ratio=user.video_aspect_ratio,
            video_duration=user.video_duration,
        )
    elif mode == "audio":
        return t(
            i18n,
            "settings.audio_title",
            audio_model=fmt_model(user.audio_model),
            audio_voice=user.audio_voice,
        )
    elif mode == "text":
        return t(
            i18n,
            "settings.text_title",
            text_model=fmt_model(user.text_model),
        )
    return ""


async def _balance_line(i18n: dict[str, str]) -> str:
    bal = await pollinations.get_balance()
    if isinstance(bal, BalanceUnavailable):
        if bal.reason == "missing_permission":
            return t(i18n, "balance.unavailable_permission")
        return t(i18n, "balance.unavailable_generic")
    from services.pollinations import BalanceInfo
    if isinstance(bal, BalanceInfo) and bal.tier_balance is not None and bal.paid_balance is not None:
        return t(
            i18n,
            "balance.line_detailed",
            balance=format_price(bal),
            tier=format_price(bal.tier_balance),
            paid=format_price(bal.paid_balance),
        )
    return t(i18n, "balance.line", balance=format_price(bal))


async def _models_index(modality: str = "image") -> tuple[list[ModelInfo], dict[str, ModelInfo]]:
    models = await pollinations.list_models(modality)
    return models, {m.name: m for m in models}


async def _all_models_index() -> dict[str, ModelInfo]:
    res = {}
    for mod in ["image", "video", "audio", "text"]:
        models = await pollinations.list_models(mod)
        for m in models:
            res[m.name] = m
    return res


@router.message(Command("settings"))
@router.message(F.text.in_(SETTINGS_LABELS))
async def open_settings(message: Message, i18n: dict[str, str]) -> None:
    if message.from_user is None:
        return
    user = await get_user(message.from_user.id)
    if user is None:
        return
    by_key = await _all_models_index()
    await message.answer(_format_settings(user, by_key, i18n, "main"), reply_markup=settings_menu(i18n))


@router.callback_query(F.data == "set:back")
async def cb_back(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.from_user is None or cb.message is None:
        return
    user = await get_user(cb.from_user.id)
    if user is None:
        return
    by_key = await _all_models_index()
    await cb.message.edit_text(_format_settings(user, by_key, i18n, "main"), reply_markup=settings_menu(i18n))


@router.callback_query(F.data == "set:image_menu")
async def cb_image_menu(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.from_user is None or cb.message is None:
        return
    user = await get_user(cb.from_user.id)
    if user is None:
        return
    by_key = await _all_models_index()
    await cb.message.edit_text(_format_settings(user, by_key, i18n, "image"), reply_markup=image_settings_menu(i18n))


@router.callback_query(F.data == "set:video_menu")
async def cb_video_menu(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.from_user is None or cb.message is None:
        return
    user = await get_user(cb.from_user.id)
    if user is None:
        return
    by_key = await _all_models_index()
    await cb.message.edit_text(_format_settings(user, by_key, i18n, "video"), reply_markup=video_settings_menu(i18n))


@router.callback_query(F.data == "set:audio_menu")
async def cb_audio_menu(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.from_user is None or cb.message is None:
        return
    user = await get_user(cb.from_user.id)
    if user is None:
        return
    by_key = await _all_models_index()
    await cb.message.edit_text(_format_settings(user, by_key, i18n, "audio"), reply_markup=audio_settings_menu(i18n))


@router.callback_query(F.data == "set:text_menu")
async def cb_text_menu(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.from_user is None or cb.message is None:
        return
    user = await get_user(cb.from_user.id)
    if user is None:
        return
    by_key = await _all_models_index()
    await cb.message.edit_text(_format_settings(user, by_key, i18n, "text"), reply_markup=text_settings_menu(i18n))


@router.callback_query(F.data == "set:model")
async def cb_pick_model(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.from_user is None or cb.message is None:
        return
    user = await get_user(cb.from_user.id)
    if user is None:
        return
    models, _ = await _models_index("image")
    balance_line = await _balance_line(i18n)
    header = t(i18n, "settings.choose_model_header", balance=balance_line)
    await cb.message.edit_text(
        header,
        reply_markup=models_kb(user.model, models, i18n, field="model", back_route="set:image_menu"),
    )


@router.callback_query(F.data == "set:edit_model")
async def cb_pick_edit_model(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.from_user is None or cb.message is None:
        return
    user = await get_user(cb.from_user.id)
    if user is None:
        return
    all_models, _ = await _models_index("image")
    editable = [m for m in all_models if m.supports_image_input]
    if not editable:
        await cb.message.edit_text(t(i18n, "settings.no_edit_models"))
        return
    balance_line = await _balance_line(i18n)
    header = t(i18n, "settings.choose_edit_model", balance=balance_line)
    await cb.message.edit_text(
        header,
        reply_markup=models_kb(user.edit_model, editable, i18n, field="edit_model", back_route="set:image_menu"),
    )


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


@router.callback_query(F.data == "set:video_model")
async def cb_pick_video_model(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.from_user is None or cb.message is None:
        return
    user = await get_user(cb.from_user.id)
    if user is None:
        return
    models, _ = await _models_index("video")
    balance_line = await _balance_line(i18n)
    header = t(i18n, "settings.choose_video_model", balance=balance_line)
    await cb.message.edit_text(
        header,
        reply_markup=models_kb(user.video_model, models, i18n, field="video_model", back_route="set:video_menu"),
    )


@router.callback_query(F.data == "set:video_ratio")
async def cb_pick_video_ratio(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.from_user is None or cb.message is None:
        return
    user = await get_user(cb.from_user.id)
    if user is None:
        return
    await cb.message.edit_text(t(i18n, "settings.choose_video_ratio"), reply_markup=video_ratios_kb(user.video_aspect_ratio, i18n))


@router.callback_query(F.data == "set:video_duration")
async def cb_pick_video_duration(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.from_user is None or cb.message is None:
        return
    user = await get_user(cb.from_user.id)
    if user is None:
        return
    await cb.message.edit_text(t(i18n, "settings.choose_video_duration"), reply_markup=video_durations_kb(user.video_duration, i18n))


@router.callback_query(F.data == "set:audio_model")
async def cb_pick_audio_model(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.from_user is None or cb.message is None:
        return
    user = await get_user(cb.from_user.id)
    if user is None:
        return
    models, _ = await _models_index("audio")
    balance_line = await _balance_line(i18n)
    header = t(i18n, "settings.choose_audio_model", balance=balance_line)
    await cb.message.edit_text(
        header,
        reply_markup=models_kb(user.audio_model, models, i18n, field="audio_model", back_route="set:audio_menu"),
    )


@router.callback_query(F.data == "set:audio_voice")
async def cb_pick_audio_voice(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.from_user is None or cb.message is None:
        return
    user = await get_user(cb.from_user.id)
    if user is None:
        return
    await cb.message.edit_text(t(i18n, "settings.choose_audio_voice"), reply_markup=audio_voices_kb(user.audio_voice, i18n))


@router.callback_query(F.data == "set:text_model")
async def cb_pick_text_model(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.from_user is None or cb.message is None:
        return
    user = await get_user(cb.from_user.id)
    if user is None:
        return
    models, _ = await _models_index("text")
    balance_line = await _balance_line(i18n)
    header = t(i18n, "settings.choose_text_model", balance=balance_line)
    await cb.message.edit_text(
        header,
        reply_markup=models_kb(user.text_model, models, i18n, field="text_model", back_route="set:text_menu"),
    )


@router.callback_query(F.data.startswith("setval:"))
async def cb_set_value(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    if cb.from_user is None or cb.message is None or cb.data is None:
        await cb.answer()
        return
    _, field, value = cb.data.split(":", 2)

    if field == "model":
        _, by_key = await _models_index("image")
        if value not in by_key:
            await cb.answer()
            return
        back_menu = "image"
    elif field == "edit_model":
        _, by_key = await _models_index("image")
        edit_info = by_key.get(value)
        if edit_info is None or not edit_info.supports_image_input:
            await cb.answer()
            return
        back_menu = "image"
    elif field == "ratio":
        back_menu = "image"
    elif field == "style":
        back_menu = "image"
    elif field == "video_model":
        _, by_key = await _models_index("video")
        if value not in by_key:
            await cb.answer()
            return
        back_menu = "video"
    elif field == "video_aspect_ratio":
        back_menu = "video"
    elif field == "video_duration":
        try:
            value = int(value)
        except ValueError:
            await cb.answer()
            return
        back_menu = "video"
    elif field == "audio_model":
        _, by_key = await _models_index("audio")
        if value not in by_key:
            await cb.answer()
            return
        back_menu = "audio"
    elif field == "audio_voice":
        back_menu = "audio"
    elif field == "text_model":
        _, by_key = await _models_index("text")
        if value not in by_key:
            await cb.answer()
            return
        back_menu = "text"
    else:
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
        
    all_by_key = await _all_models_index()
    if back_menu == "image":
        await cb.message.edit_text(_format_settings(user, all_by_key, i18n, "image"), reply_markup=image_settings_menu(i18n))
    elif back_menu == "video":
        await cb.message.edit_text(_format_settings(user, all_by_key, i18n, "video"), reply_markup=video_settings_menu(i18n))
    elif back_menu == "audio":
        await cb.message.edit_text(_format_settings(user, all_by_key, i18n, "audio"), reply_markup=audio_settings_menu(i18n))
    elif back_menu == "text":
        await cb.message.edit_text(_format_settings(user, all_by_key, i18n, "text"), reply_markup=text_settings_menu(i18n))
