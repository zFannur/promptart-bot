from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from loguru import logger

from keyboards.generation import confirm_enhance_kb, post_gen_kb
from keyboards.main import main_menu
from services.database import (
    add_favorite,
    get_generation,
    get_user,
    is_favorite,
    remove_favorite,
    save_generation,
    update_generation_file_id,
)
from services.pollinations import (
    NSFWRejected,
    PollinationsError,
    PremiumRequired,
    QuotaExhausted,
    pollinations,
)
from states.generation import GenStates
from utils.aspect_ratios import RATIOS_BY_KEY
from utils.i18n import t
from utils.menu import CREATE_LABELS
from utils.styles import apply_style

router = Router(name=__name__)

MAX_PROMPT_LEN = 500


@router.message(F.text.in_(CREATE_LABELS))
async def ask_prompt(message: Message, state: FSMContext, i18n: dict[str, str]) -> None:
    await state.set_state(GenStates.waiting_for_prompt)
    await message.answer(t(i18n, "generation.ask_prompt"))


@router.message(GenStates.waiting_for_prompt, F.text)
async def receive_prompt(message: Message, state: FSMContext, i18n: dict[str, str]) -> None:
    if message.from_user is None or message.bot is None or not message.text:
        return
    prompt = message.text.strip()
    if not prompt:
        await message.answer(t(i18n, "generation.empty_prompt"))
        return
    if len(prompt) > MAX_PROMPT_LEN:
        await message.answer(t(i18n, "generation.too_long"))
        return

    await state.clear()
    await _do_generation(
        bot=message.bot,
        chat_id=message.chat.id,
        user_telegram_id=message.from_user.id,
        prompt=prompt,
        i18n=i18n,
    )


async def _do_generation(
    *,
    bot: Bot,
    chat_id: int,
    user_telegram_id: int,
    prompt: str,
    i18n: dict[str, str],
) -> None:
    user = await get_user(user_telegram_id)
    if user is None:
        logger.warning("generation requested by unknown user {}", user_telegram_id)
        await bot.send_message(chat_id, t(i18n, "errors.generic"))
        return

    ratio = RATIOS_BY_KEY.get(user.aspect_ratio)
    if ratio is None:
        await bot.send_message(chat_id, t(i18n, "errors.generic"))
        return

    final_prompt = apply_style(prompt, user.style)
    progress_msg = await bot.send_message(chat_id, t(i18n, "generation.in_progress"))
    try:
        await bot.send_chat_action(chat_id, "upload_photo")
        image_bytes, seed = await pollinations.generate_image(
            final_prompt,
            width=ratio.width,
            height=ratio.height,
            model=user.model,
        )
    except NSFWRejected:
        await progress_msg.edit_text(t(i18n, "generation.nsfw"))
        return
    except PremiumRequired:
        logger.info("premium required for model {}", user.model)
        await progress_msg.edit_text(t(i18n, "generation.premium_required", model=user.model))
        return
    except QuotaExhausted as e:
        logger.warning("quota exhausted: {}", e)
        await progress_msg.edit_text(t(i18n, "errors.api_down"))
        return
    except PollinationsError as e:
        logger.warning("pollinations error: {}", e)
        await progress_msg.edit_text(t(i18n, "generation.error"))
        return

    gen_id = await save_generation(
        user_id=user.id,
        prompt=prompt,
        enhanced_prompt=None,
        model=user.model,
        aspect_ratio=user.aspect_ratio,
        style=user.style,
        seed=seed,
        file_id=None,
    )

    photo = BufferedInputFile(image_bytes, filename=f"gen_{gen_id}.jpg")
    sent = await bot.send_photo(
        chat_id=chat_id,
        photo=photo,
        caption=t(i18n, "generation.done_caption", prompt=prompt[:900]),
        reply_markup=post_gen_kb(gen_id, is_fav=False, i18n=i18n),
    )
    if sent.photo:
        await update_generation_file_id(gen_id, sent.photo[-1].file_id)

    try:
        await progress_msg.delete()
    except Exception:
        pass


@router.callback_query(F.data.startswith("regen:"))
async def cb_regenerate(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    if cb.from_user is None or cb.message is None or cb.data is None or cb.bot is None:
        await cb.answer()
        return
    await cb.answer()
    gen_id = int(cb.data.split(":", 1)[1])
    gen = await get_generation(gen_id)
    if gen is None:
        await cb.bot.send_message(cb.message.chat.id, t(i18n, "errors.generic"))
        return
    await _do_generation(
        bot=cb.bot,
        chat_id=cb.message.chat.id,
        user_telegram_id=cb.from_user.id,
        prompt=gen.prompt,
        i18n=i18n,
    )


@router.callback_query(F.data.startswith("fav:"))
async def cb_favorite(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    if cb.from_user is None or cb.data is None or cb.message is None:
        await cb.answer()
        return
    gen_id = int(cb.data.split(":", 1)[1])
    user = await get_user(cb.from_user.id)
    if user is None:
        await cb.answer()
        return
    if await is_favorite(user.id, gen_id):
        await remove_favorite(user.id, gen_id)
        await cb.answer(t(i18n, "favorites.removed"))
        new_state = False
    else:
        await add_favorite(user.id, gen_id)
        await cb.answer(t(i18n, "favorites.added"))
        new_state = True
    try:
        await cb.message.edit_reply_markup(reply_markup=post_gen_kb(gen_id, new_state, i18n))
    except Exception:
        pass


@router.callback_query(F.data.startswith("enh:"))
async def cb_enhance(cb: CallbackQuery, state: FSMContext, i18n: dict[str, str]) -> None:
    if cb.from_user is None or cb.message is None or cb.data is None:
        await cb.answer()
        return
    await cb.answer()
    gen_id = int(cb.data.split(":", 1)[1])
    gen = await get_generation(gen_id)
    if gen is None:
        return

    progress = await cb.message.answer(t(i18n, "enhance.in_progress"))
    try:
        enhanced = await pollinations.enhance_prompt(gen.prompt)
    except PollinationsError:
        await progress.edit_text(t(i18n, "enhance.error"))
        return

    await state.update_data(enhanced_prompts={str(gen_id): enhanced})
    await progress.edit_text(
        t(i18n, "enhance.compare", old=gen.prompt[:400], new=enhanced[:400]),
        reply_markup=confirm_enhance_kb(gen_id, i18n),
    )


@router.callback_query(F.data.startswith("enh_apply:"))
async def cb_enhance_apply(cb: CallbackQuery, state: FSMContext, i18n: dict[str, str]) -> None:
    if cb.from_user is None or cb.message is None or cb.data is None or cb.bot is None:
        await cb.answer()
        return
    await cb.answer()
    gen_id = int(cb.data.split(":", 1)[1])
    fsm_data = await state.get_data()
    enhanced_map: dict[str, str] = fsm_data.get("enhanced_prompts", {})
    enhanced = enhanced_map.get(str(gen_id))
    if not enhanced:
        await cb.bot.send_message(cb.message.chat.id, t(i18n, "errors.generic"))
        return

    chat_id = cb.message.chat.id
    user_id = cb.from_user.id
    try:
        await cb.message.delete()
    except Exception:
        pass

    await _do_generation(
        bot=cb.bot,
        chat_id=chat_id,
        user_telegram_id=user_id,
        prompt=enhanced,
        i18n=i18n,
    )


@router.callback_query(F.data == "enh_cancel")
async def cb_enhance_cancel(cb: CallbackQuery) -> None:
    await cb.answer()
    if cb.message is None:
        return
    try:
        await cb.message.delete()
    except Exception:
        pass


@router.message(F.text)
async def fallback_text(message: Message, state: FSMContext, i18n: dict[str, str]) -> None:
    """Treat any plain text outside FSM as a fresh generation request."""
    if message.from_user is None or message.bot is None or not message.text:
        return
    if message.text.startswith("/"):
        return
    if await state.get_state():
        return
    prompt = message.text.strip()
    if len(prompt) < 2:
        await message.answer(t(i18n, "generation.ask_prompt"), reply_markup=main_menu(i18n))
        return
    if len(prompt) > MAX_PROMPT_LEN:
        await message.answer(t(i18n, "generation.too_long"))
        return
    await _do_generation(
        bot=message.bot,
        chat_id=message.chat.id,
        user_telegram_id=message.from_user.id,
        prompt=prompt,
        i18n=i18n,
    )
