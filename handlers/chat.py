from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, Message
from loguru import logger

from keyboards.generation import post_media_kb
from keyboards.main import chat_keyboard, main_menu
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
from states.generation import GenStates
from utils.i18n import t
from utils.menu import (
    ALL_MENU_LABELS,
    CHAT_LABELS,
    CLEAR_CONTEXT_LABELS,
    BACK_TO_MENU_LABELS,
)

router = Router(name=__name__)

MAX_CHAT_LEN = 4000


@router.message(F.text.in_(CHAT_LABELS))
async def enter_chat_mode(message: Message, state: FSMContext, i18n: dict[str, str]) -> None:
    await state.set_state(GenStates.waiting_for_chat_prompt)
    await state.update_data(chat_history=[])
    await message.answer(
        t(i18n, "chat.ask_prompt"),
        reply_markup=chat_keyboard(i18n),
    )


@router.message(GenStates.waiting_for_chat_prompt, F.text.in_(BACK_TO_MENU_LABELS))
@router.message(GenStates.waiting_for_chat_prompt, Command("cancel", "menu"))
async def exit_chat_mode(message: Message, state: FSMContext, i18n: dict[str, str]) -> None:
    await state.clear()
    await message.answer(
        t(i18n, "chat.returned_to_menu"),
        reply_markup=main_menu(i18n),
    )


@router.message(GenStates.waiting_for_chat_prompt, F.text.in_(CLEAR_CONTEXT_LABELS))
@router.message(GenStates.waiting_for_chat_prompt, Command("clear", "reset"))
async def clear_chat_history_handler(message: Message, state: FSMContext, i18n: dict[str, str]) -> None:
    await state.update_data(chat_history=[])
    await message.answer(
        t(i18n, "chat.context_cleared"),
        reply_markup=chat_keyboard(i18n),
    )


@router.message(
    GenStates.waiting_for_chat_prompt,
    F.text,
    ~F.text.startswith("/"),
    ~F.text.in_(ALL_MENU_LABELS),
)
async def receive_chat_message(message: Message, state: FSMContext, i18n: dict[str, str]) -> None:
    if message.from_user is None or message.bot is None or not message.text:
        return
    text = message.text.strip()
    if not text:
        return
    if len(text) > MAX_CHAT_LEN:
        await message.answer(t(i18n, "generation.too_long"))
        return

    data = await state.get_data()
    chat_history = list(data.get("chat_history") or [])
    chat_history.append({"role": "user", "content": text})

    await _do_chat_generation(
        bot=message.bot,
        chat_id=message.chat.id,
        user_telegram_id=message.from_user.id,
        prompt=text,
        chat_history=chat_history,
        state=state,
        i18n=i18n,
    )


async def _do_chat_generation(
    *,
    bot: Bot,
    chat_id: int,
    user_telegram_id: int,
    prompt: str,
    chat_history: list[dict[str, str]],
    state: FSMContext,
    i18n: dict[str, str],
) -> None:
    user = await get_user(user_telegram_id)
    if user is None:
        logger.warning("text generation requested by unknown user {}", user_telegram_id)
        await bot.send_message(chat_id, t(i18n, "errors.generic"))
        return

    progress_msg = await bot.send_message(chat_id, t(i18n, "chat.in_progress"))
    try:
        await bot.send_chat_action(chat_id, "typing")
        response_text = await pollinations.generate_text(
            messages=chat_history,
            model=user.text_model,
        )
    except NSFWRejected:
        await progress_msg.edit_text(t(i18n, "generation.nsfw"))
        return
    except PremiumRequired:
        logger.info("premium required for text model {}", user.text_model)
        await progress_msg.edit_text(t(i18n, "generation.premium_required", model=user.text_model))
        return
    except QuotaExhausted as e:
        logger.warning("quota exhausted: {}", e)
        await progress_msg.edit_text(t(i18n, "errors.api_down"))
        return
    except PollinationsError as e:
        logger.warning("pollinations text error: {}", e)
        await progress_msg.edit_text(t(i18n, "chat.error"))
        return

    # Update chat history in the FSM state
    chat_history.append({"role": "assistant", "content": response_text})
    if len(chat_history) > 20:
        chat_history = chat_history[-20:]
    await state.update_data(chat_history=chat_history)

    gen_id = await save_generation(
        user_id=user.id,
        prompt=prompt,
        enhanced_prompt=None,
        model=user.text_model,
        aspect_ratio="1:1",
        style=None,
        seed=0,
        file_id=None,
        kind="text",
    )

    # Offer basic regeneration/favorite options
    if len(response_text) > 4000:
        md_file = BufferedInputFile(response_text.encode("utf-8"), filename="response.md")
        sent = await bot.send_document(
            chat_id=chat_id,
            document=md_file,
            caption=t(i18n, "chat.response_too_long_caption"),
            reply_markup=post_media_kb(gen_id, is_fav=False, i18n=i18n, kind="text"),
        )
        if sent.document:
            await update_generation_file_id(gen_id, sent.document.file_id)
    else:
        await bot.send_message(
            chat_id=chat_id,
            text=response_text,
            reply_markup=post_media_kb(gen_id, is_fav=False, i18n=i18n, kind="text"),
        )

    try:
        await progress_msg.delete()
    except Exception:
        pass
