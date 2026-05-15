"""Image-editing flow.

UX:
- Tap «✏️ Edit» (or /edit) → bot enters EditStates.collecting and asks for
  1–4 photos plus a text description.
- Photo handler accumulates file_ids in FSM state['photos'].
- If a single photo arrives WITH a caption (no media_group_id), the caption
  is used as the prompt and generation kicks off immediately.
- Otherwise, the user signals completion by sending a text message — that
  text is the prompt.

Photos are stored as file_ids (small strings) and lazily downloaded to
bytes only when the API call fires. This keeps FSM memory tiny and works
even when several edits run concurrently.
"""

from __future__ import annotations

import asyncio
import io

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from loguru import logger

from keyboards.edit import edit_cancel_kb
from keyboards.generation import post_gen_kb
from services.database import (
    get_user,
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
from states.generation import EditStates
from utils.aspect_ratios import RATIOS_BY_KEY
from utils.i18n import t
from utils.menu import EDIT_LABELS

router = Router(name=__name__)

MAX_PHOTOS = 4
MAX_PROMPT_LEN = 500


# ──────────────────────────── entry points ─────────────────────────────


@router.message(Command("edit"))
@router.message(F.text.in_(EDIT_LABELS))
async def open_edit(message: Message, state: FSMContext, i18n: dict[str, str]) -> None:
    if message.from_user is None:
        return
    await state.clear()
    await state.set_state(EditStates.collecting)
    await state.update_data(photos=[], caption=None)
    await message.answer(
        t(i18n, "edit.ask_input"),
        reply_markup=edit_cancel_kb(i18n),
    )


# ───────────────────────────── cancel ───────────────────────────────────


@router.callback_query(F.data == "edit:cancel")
async def cb_edit_cancel(cb: CallbackQuery, state: FSMContext, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.message is None:
        return
    await state.clear()
    try:
        await cb.message.edit_text(t(i18n, "edit.cancelled"))
    except Exception:
        await cb.message.answer(t(i18n, "edit.cancelled"))


# ─────────────────────────── photo collection ──────────────────────────


@router.message(EditStates.collecting, F.photo)
async def receive_photo(message: Message, state: FSMContext, i18n: dict[str, str]) -> None:
    if message.bot is None or message.from_user is None or not message.photo:
        return

    data = await state.get_data()
    photos: list[str] = list(data.get("photos") or [])

    if len(photos) >= MAX_PHOTOS:
        await message.answer(t(i18n, "edit.too_many"))
        return

    # Largest variant has the highest-resolution file_id.
    file_id = message.photo[-1].file_id
    photos.append(file_id)

    # Caption priority: explicit prompt from earlier > current caption.
    caption: str | None = data.get("caption")
    if caption is None and message.caption:
        caption = message.caption.strip() or None

    # Bump ack-token: only the latest scheduled ack survives. This debounces
    # Telegram media-groups (4 photos arrive in ~300 ms, but we want one
    # consolidated reply, not four). For lone photos the debounce is a
    # harmless ~0.7 s wait.
    ack_token = int(data.get("ack_token", 0)) + 1
    await state.update_data(photos=photos, caption=caption, ack_token=ack_token)

    # Fast path: a single photo with caption and no media-group context →
    # treat the caption as the prompt and kick off the edit immediately.
    if len(photos) == 1 and caption and message.media_group_id is None:
        await _run_edit(
            bot=message.bot,
            chat_id=message.chat.id,
            user_telegram_id=message.from_user.id,
            photos=photos,
            prompt=caption,
            state=state,
            i18n=i18n,
        )
        return

    asyncio.create_task(_debounced_photo_ack(message, state, ack_token, i18n))


async def _debounced_photo_ack(
    message: Message,
    state: FSMContext,
    my_token: int,
    i18n: dict[str, str],
) -> None:
    """Wait briefly, then send a single 'Photo N/4' reply only if no newer
    photo arrived in the meantime. Coalesces album/media-group replies."""
    await asyncio.sleep(0.7)
    data = await state.get_data()
    if data.get("ack_token") != my_token:
        return  # superseded by a newer photo
    photos = data.get("photos") or []
    if not photos:
        return  # state was cleared (e.g. fast-path fired)
    try:
        await message.answer(t(i18n, "edit.photo_received", n=len(photos)))
    except Exception as e:
        logger.debug("debounced ack send failed: {}", e)


# ─────────────────────────── text → trigger ─────────────────────────────


@router.message(EditStates.collecting, F.text)
async def receive_prompt(message: Message, state: FSMContext, i18n: dict[str, str]) -> None:
    if message.bot is None or message.from_user is None or not message.text:
        return

    # Menu reply-buttons and /commands are caught by their dedicated routers
    # (settings/history/balance/start), which are included BEFORE this router
    # in bot.py — so by the time we get here, the text is genuinely a prompt.
    # We still guard against /commands defensively in case routing changes.
    text = message.text.strip()
    if text.startswith("/"):
        return

    data = await state.get_data()
    photos: list[str] = list(data.get("photos") or [])
    if not photos:
        await message.answer(t(i18n, "edit.no_photos"))
        return

    if len(text) < 2:
        await message.answer(t(i18n, "generation.empty_prompt"))
        return
    if len(text) > MAX_PROMPT_LEN:
        await message.answer(t(i18n, "generation.too_long"))
        return

    await _run_edit(
        bot=message.bot,
        chat_id=message.chat.id,
        user_telegram_id=message.from_user.id,
        photos=photos,
        prompt=text,
        state=state,
        i18n=i18n,
    )


# ──────────────────────────── core flow ────────────────────────────────


async def _run_edit(
    *,
    bot: Bot,
    chat_id: int,
    user_telegram_id: int,
    photos: list[str],
    prompt: str,
    state: FSMContext,
    i18n: dict[str, str],
) -> None:
    user = await get_user(user_telegram_id)
    if user is None:
        logger.warning("edit requested by unknown user {}", user_telegram_id)
        await bot.send_message(chat_id, t(i18n, "errors.generic"))
        await state.clear()
        return

    ratio = RATIOS_BY_KEY.get(user.aspect_ratio)
    if ratio is None:
        await bot.send_message(chat_id, t(i18n, "errors.generic"))
        await state.clear()
        return

    progress = await bot.send_message(
        chat_id,
        t(i18n, "edit.in_progress", n=len(photos), model=user.edit_model),
    )
    await bot.send_chat_action(chat_id, "upload_photo")

    # Download photos concurrently. Any failure aborts the edit.
    try:
        image_bytes_list = await asyncio.gather(
            *(_download_photo(bot, file_id) for file_id in photos)
        )
    except Exception as e:
        logger.warning(
            "photo download failed user={} photos={!r}: {!r}",
            user_telegram_id, photos, e,
        )
        await progress.edit_text(t(i18n, "edit.download_failed"))
        await state.clear()
        return

    try:
        out_bytes, seed = await pollinations.edit_image(
            prompt,
            list(image_bytes_list),
            model=user.edit_model,
            width=ratio.width,
            height=ratio.height,
        )
    except NSFWRejected:
        await progress.edit_text(t(i18n, "generation.nsfw"))
        await state.clear()
        return
    except PremiumRequired:
        logger.info("edit premium required for {}", user.edit_model)
        await progress.edit_text(t(i18n, "generation.premium_required", model=user.edit_model))
        await state.clear()
        return
    except QuotaExhausted as e:
        logger.warning("edit quota exhausted: {}", e)
        await progress.edit_text(t(i18n, "errors.api_down"))
        await state.clear()
        return
    except PollinationsError as e:
        logger.warning("edit pollinations error: {}", e)
        await progress.edit_text(t(i18n, "edit.error"))
        await state.clear()
        return

    # Persist to history so user sees the edited result alongside generations.
    # We tag the prompt with [EDIT] marker so it's recognisable in history.
    history_prompt = f"[EDIT × {len(photos)}] {prompt}"
    gen_id = await save_generation(
        user_id=user.id,
        prompt=history_prompt,
        enhanced_prompt=None,
        model=user.edit_model,
        aspect_ratio=user.aspect_ratio,
        style=user.style,
        seed=seed,
        file_id=None,
    )

    photo = BufferedInputFile(out_bytes, filename=f"edit_{gen_id}.jpg")
    sent = await bot.send_photo(
        chat_id=chat_id,
        photo=photo,
        caption=t(i18n, "edit.done_caption", prompt=prompt[:900]),
        reply_markup=post_gen_kb(gen_id, is_fav=False, i18n=i18n),
    )
    if sent.photo:
        await update_generation_file_id(gen_id, sent.photo[-1].file_id)

    try:
        await progress.delete()
    except Exception:
        pass

    await state.clear()


# ─────────────────────────── helpers ───────────────────────────────────


async def _download_photo(bot: Bot, file_id: str) -> bytes:
    """Download a Telegram file_id to bytes via bot.download_file."""
    file = await bot.get_file(file_id)
    if file.file_path is None:
        raise RuntimeError(f"telegram returned no file_path for {file_id}")
    buf = io.BytesIO()
    await bot.download_file(file.file_path, destination=buf)
    buf.seek(0)
    return buf.read()
