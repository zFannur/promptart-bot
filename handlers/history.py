from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from loguru import logger

from keyboards.generation import (
    confirm_clear_history_kb,
    history_clear_kb,
    history_item_kb,
    post_gen_kb,
)
from services.database import (
    clear_user_generations,
    get_user,
    is_favorite,
    list_user_favorites,
    list_user_generations,
)
from utils.i18n import t
from utils.menu import FAVORITES_LABELS, HISTORY_LABELS

router = Router(name=__name__)


@router.message(Command("history"))
@router.message(F.text.in_(HISTORY_LABELS))
async def cmd_history(message: Message, i18n: dict[str, str]) -> None:
    """Render the user's last 10 generations as actual photo previews with
    inline buttons (Again / Edit / Favorite) — same UX as /favorites."""
    if message.from_user is None:
        return
    user = await get_user(message.from_user.id)
    if user is None:
        return
    gens = await list_user_generations(user.id, limit=10)
    if not gens:
        await message.answer(t(i18n, "history.empty"))
        return

    await message.answer(t(i18n, "history.title"), reply_markup=history_clear_kb(i18n))
    for g in gens:
        caption = t(i18n, "generation.done_caption", prompt=g.prompt[:900])
        fav = await is_favorite(user.id, g.id)
        kb = post_gen_kb(g.id, is_fav=fav, i18n=i18n)
        try:
            if g.file_id:
                await message.answer_photo(g.file_id, caption=caption, reply_markup=kb)
            else:
                # Old rows from before file_id was tracked. Show text fallback
                # with a re-generate option.
                await message.answer(caption, reply_markup=history_item_kb(g.id, i18n))
        except Exception as e:
            logger.warning("history send failed for gen {}: {}", g.id, e)
            await message.answer(caption, reply_markup=history_item_kb(g.id, i18n))


@router.message(Command("clearhistory"))
@router.callback_query(F.data == "hist_clear")
async def ask_clear_history(event: Message | CallbackQuery, i18n: dict[str, str]) -> None:
    target = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()
    if target is not None:
        await target.answer(t(i18n, "history.clear_confirm"), reply_markup=confirm_clear_history_kb(i18n))


@router.callback_query(F.data == "hist_clear_yes")
async def do_clear_history(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    user = await get_user(cb.from_user.id)
    if user is None:
        await cb.answer()
        return
    removed = await clear_user_generations(user.id)
    await cb.answer()
    if isinstance(cb.message, Message):
        await cb.message.edit_text(t(i18n, "history.cleared", count=removed))
    logger.info("user {} cleared {} generations", cb.from_user.id, removed)


@router.callback_query(F.data == "hist_clear_no")
async def cancel_clear_history(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    await cb.answer()
    if isinstance(cb.message, Message):
        await cb.message.edit_text(t(i18n, "history.clear_cancelled"))


@router.message(Command("favorites"))
@router.message(F.text.in_(FAVORITES_LABELS))
async def cmd_favorites(message: Message, i18n: dict[str, str]) -> None:
    if message.from_user is None:
        return
    user = await get_user(message.from_user.id)
    if user is None:
        return
    favs = await list_user_favorites(user.id, limit=10)
    if not favs:
        await message.answer(t(i18n, "favorites.empty"))
        return

    await message.answer(t(i18n, "favorites.title"))
    for g in favs:
        caption = t(i18n, "generation.done_caption", prompt=g.prompt[:900])
        kb = post_gen_kb(g.id, is_fav=True, i18n=i18n)
        try:
            if g.file_id:
                await message.answer_photo(g.file_id, caption=caption, reply_markup=kb)
            else:
                await message.answer(caption, reply_markup=history_item_kb(g.id, i18n))
        except Exception as e:
            logger.warning("favorites send failed for gen {}: {}", g.id, e)
            await message.answer(caption, reply_markup=history_item_kb(g.id, i18n))
