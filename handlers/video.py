import base64
import random
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from loguru import logger

from keyboards.generation import post_media_kb
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
from utils.i18n import t
from utils.menu import CREATE_VIDEO_LABELS

router = Router(name=__name__)

MAX_PROMPT_LEN = 500


@router.message(F.text.in_(CREATE_VIDEO_LABELS))
async def ask_video_prompt(message: Message, state: FSMContext, i18n: dict[str, str]) -> None:
    await state.set_state(GenStates.waiting_for_video_prompt)
    await message.answer(t(i18n, "video.ask_prompt"))


@router.message(GenStates.waiting_for_video_prompt, F.text)
async def receive_video_prompt(message: Message, state: FSMContext, i18n: dict[str, str]) -> None:
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
    await _do_video_generation(
        bot=message.bot,
        chat_id=message.chat.id,
        user_telegram_id=message.from_user.id,
        prompt=prompt,
        i18n=i18n,
    )


async def _do_video_generation(
    *,
    bot: Bot,
    chat_id: int,
    user_telegram_id: int,
    prompt: str,
    i18n: dict[str, str],
) -> None:
    user = await get_user(user_telegram_id)
    if user is None:
        logger.warning("video generation requested by unknown user {}", user_telegram_id)
        await bot.send_message(chat_id, t(i18n, "errors.generic"))
        return

    progress_msg = await bot.send_message(chat_id, t(i18n, "video.in_progress"))
    try:
        await bot.send_chat_action(chat_id, "upload_video")
        
        # Determine dimensions from aspect ratio
        width, height = 1024, 576
        if user.video_aspect_ratio == "1:1":
            width, height = 768, 768
        elif user.video_aspect_ratio == "9:16":
            width, height = 576, 1024

        video_bytes, seed = await pollinations.generate_video(
            prompt,
            width=width,
            height=height,
            model=user.video_model,
            seconds=user.video_duration,
        )
    except NSFWRejected:
        await progress_msg.edit_text(t(i18n, "generation.nsfw"))
        return
    except PremiumRequired:
        logger.info("premium required for video model {}", user.video_model)
        await progress_msg.edit_text(t(i18n, "generation.premium_required", model=user.video_model))
        return
    except QuotaExhausted as e:
        logger.warning("quota exhausted: {}", e)
        await progress_msg.edit_text(t(i18n, "errors.api_down"))
        return
    except PollinationsError as e:
        logger.warning("pollinations video error: {}", e)
        await progress_msg.edit_text(t(i18n, "video.error"))
        return

    gen_id = await save_generation(
        user_id=user.id,
        prompt=prompt,
        enhanced_prompt=None,
        model=user.video_model,
        aspect_ratio=user.video_aspect_ratio,
        style=None,
        seed=seed,
        file_id=None,
        kind="video",
    )

    video_file = BufferedInputFile(video_bytes, filename=f"gen_{gen_id}.mp4")
    sent = await bot.send_video(
        chat_id=chat_id,
        video=video_file,
        caption=t(i18n, "video.done_caption", prompt=prompt[:900]),
        reply_markup=post_media_kb(gen_id, is_fav=False, i18n=i18n, kind="video"),
    )
    if sent.video:
        await update_generation_file_id(gen_id, sent.video.file_id)

    try:
        await progress_msg.delete()
    except Exception:
        pass
