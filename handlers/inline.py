from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultPhoto
from loguru import logger

from services.pollinations import pollinations
from utils.aspect_ratios import RATIOS_BY_KEY
from utils.models import INLINE_MODEL

router = Router(name=__name__)

INLINE_RATIO = RATIOS_BY_KEY["1:1"]
INLINE_VARIANTS = 3


@router.inline_query()
async def inline_handler(query: InlineQuery) -> None:
    text = query.query.strip()
    if not text or len(text) < 2:
        await query.answer([], cache_time=1, is_personal=True)
        return
    if len(text) > 200:
        await query.answer([], cache_time=1, is_personal=True)
        return

    try:
        results: list[InlineQueryResultPhoto] = []
        for i in range(INLINE_VARIANTS):
            url = await pollinations.generate_image_url(
                text,
                width=INLINE_RATIO.width,
                height=INLINE_RATIO.height,
                model=INLINE_MODEL,
                seed=hash((text, i)) & 0x7FFFFFFF,
            )
            results.append(
                InlineQueryResultPhoto(
                    id=f"{query.id}_{i}",
                    photo_url=url,
                    thumbnail_url=url,
                    photo_width=INLINE_RATIO.width,
                    photo_height=INLINE_RATIO.height,
                    title=text[:60],
                    caption=f"🎨 {text[:1000]}",
                )
            )
        await query.answer(results, cache_time=10, is_personal=True)
    except Exception as e:
        logger.warning("inline error: {}", e)
        await query.answer([], cache_time=1, is_personal=True)
