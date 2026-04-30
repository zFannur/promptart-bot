from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from loguru import logger

from keyboards.generation import history_item_kb, post_gen_kb
from services.database import (
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
    if message.from_user is None:
        return
    user = await get_user(message.from_user.id)
    if user is None:
        return
    gens = await list_user_generations(user.id, limit=10)
    if not gens:
        await message.answer(t(i18n, "history.empty"))
        return

    lines = [t(i18n, "history.title"), ""]
    for idx, g in enumerate(gens, start=1):
        prompt_short = g.prompt[:80] + ("…" if len(g.prompt) > 80 else "")
        lines.append(t(i18n, "history.item", idx=idx, prompt=prompt_short, model=g.model, ratio=g.aspect_ratio))
    await message.answer("\n\n".join(lines))


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
