from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, Message
from loguru import logger

from keyboards.generation import post_media_kb
from keyboards.main import main_menu
from services.database import (
    get_user,
    save_generation,
    update_generation_file_id,
)
from services.pollinations import (
    TokenRequired,
    NSFWRejected,
    PollinationsError,
    PremiumRequired,
    QuotaExhausted,
    pollinations,
)
from states.generation import GenStates
from utils.i18n import t
from utils.menu import CREATE_AUDIO_LABELS

router = Router(name=__name__)

MAX_TEXT_LEN = 4000


@router.message(F.text.in_(CREATE_AUDIO_LABELS))
async def ask_audio_prompt(message: Message, state: FSMContext, i18n: dict[str, str]) -> None:
    await state.set_state(GenStates.waiting_for_audio_prompt)
    await message.answer(t(i18n, "audio.ask_prompt"))


@router.message(GenStates.waiting_for_audio_prompt, F.text)
async def receive_audio_prompt(message: Message, state: FSMContext, i18n: dict[str, str]) -> None:
    if message.from_user is None or message.bot is None or not message.text:
        return
    text = message.text.strip()
    if not text:
        await message.answer(t(i18n, "generation.empty_prompt"))
        return
    if len(text) > MAX_TEXT_LEN:
        await message.answer(t(i18n, "generation.too_long"))
        return

    await state.clear()
    await _do_audio_generation(
        bot=message.bot,
        chat_id=message.chat.id,
        user_telegram_id=message.from_user.id,
        prompt=text,
        i18n=i18n,
    )


async def _do_audio_generation(
    *,
    bot: Bot,
    chat_id: int,
    user_telegram_id: int,
    prompt: str,
    i18n: dict[str, str],
) -> None:
    user = await get_user(user_telegram_id)
    if user is None:
        logger.warning("audio generation requested by unknown user {}", user_telegram_id)
        await bot.send_message(chat_id, t(i18n, "errors.generic"))
        return

    progress_msg = await bot.send_message(chat_id, t(i18n, "audio.in_progress"))
    try:
        await bot.send_chat_action(chat_id, "record_voice")
        audio_bytes = await pollinations.generate_audio(
            prompt,
            model=user.audio_model,
            voice=user.audio_voice,
        )
    except NSFWRejected:
        await progress_msg.edit_text(t(i18n, "generation.nsfw"))
        return
    except PremiumRequired:
        logger.info("premium required for audio model {}", user.audio_model)
        await progress_msg.edit_text(t(i18n, "generation.premium_required", model=user.audio_model))
        return
    except QuotaExhausted as e:
        logger.warning("quota exhausted: {}", e)
        await progress_msg.edit_text(t(i18n, "errors.api_down"))
        return
    except TokenRequired:
        # Subclass of PollinationsError — must be caught first so a user without
        # a key is told how to get one instead of "generation failed".
        await progress_msg.edit_text(t(i18n, "token.required"), reply_markup=get_key_button(i18n))
        return
    except PollinationsError as e:
        logger.warning("pollinations audio error: {}", e)
        await progress_msg.edit_text(t(i18n, "audio.error"))
        return
    except Exception as e:  # noqa: BLE001
        # Without this, an unforeseen failure left "in progress…" on screen
        # forever and the bot looked hung.
        logger.exception("unexpected audio failure: {}", e)
        await progress_msg.edit_text(t(i18n, "audio.error"))
        return

    gen_id = await save_generation(
        user_id=user.id,
        prompt=prompt,
        enhanced_prompt=None,
        model=user.audio_model,
        aspect_ratio="1:1",
        style=None,
        seed=0,
        file_id=None,
        kind="audio",
    )

    audio_file = BufferedInputFile(audio_bytes, filename=f"gen_{gen_id}.mp3")
    sent = await bot.send_audio(
        chat_id=chat_id,
        audio=audio_file,
        caption=t(i18n, "audio.done_caption"),
        reply_markup=post_media_kb(gen_id, is_fav=False, i18n=i18n, kind="audio"),
    )
    if sent.audio:
        await update_generation_file_id(gen_id, sent.audio.file_id)

    try:
        await progress_msg.delete()
    except Exception:
        pass
