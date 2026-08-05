from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from handlers.generation import _do_generation
from keyboards.generation import prompt_options_kb
from services.database import (
    get_generation,
    get_user,
    save_user_prompt,
    list_user_prompts,
    delete_user_prompt,
    get_user_prompt,
)
from states.generation import PromptStates
from utils.i18n import t
from utils.menu import USER_TEXT
from utils.prompt_builder import build_prompt
from utils.prompt_templates import TRENDING_TEMPLATES

router = Router(name=__name__)


@router.message(Command("prompts", "prompt"))
async def cmd_prompts(message: Message, i18n: dict[str, str]) -> None:
    await message.answer(t(i18n, "generation.ask_prompt"), reply_markup=prompt_options_kb(i18n))


@router.callback_query(F.data == "prompt_menu:main")
async def cb_prompt_main(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.message is None:
        return
    await cb.message.edit_text(t(i18n, "generation.ask_prompt"), reply_markup=prompt_options_kb(i18n))


# --- 1. Saved Prompts Logic ---

@router.callback_query(F.data == "prompt_menu:saved")
async def cb_saved_prompts(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.from_user is None or cb.message is None:
        return
    user = await get_user(cb.from_user.id)
    if user is None:
        return
    
    prompts = await list_user_prompts(user.id)
    if not prompts:
        builder = InlineKeyboardBuilder()
        builder.button(text=t(i18n, "buttons.back"), callback_data="prompt_menu:main")
        await cb.message.edit_text(t(i18n, "prompt.saved_empty"), reply_markup=builder.as_markup())
        return
    
    builder = InlineKeyboardBuilder()
    for p in prompts:
        builder.button(text=p["title"], callback_data=f"prompt_detail:{p['id']}")
    builder.button(text=t(i18n, "buttons.back"), callback_data="prompt_menu:main")
    builder.adjust(1)
    
    await cb.message.edit_text(t(i18n, "prompt.saved_title"), reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("prompt_detail:"))
async def cb_prompt_detail(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.from_user is None or cb.message is None or cb.data is None:
        return
    prompt_id = int(cb.data.split(":", 1)[1])
    user = await get_user(cb.from_user.id)
    if user is None:
        return
    
    prompt = await get_user_prompt(user.id, prompt_id)
    if not prompt:
        await cb.message.edit_text(t(i18n, "errors.generic"))
        return
    
    is_ru = i18n.get("menu.create_image") == "🎨 Создать изображение"
    gen_text = "🎨 Генерировать" if is_ru else "🎨 Generate"
    del_text = "🗑️ Удалить" if is_ru else "🗑️ Delete"
    
    builder = InlineKeyboardBuilder()
    builder.button(text=gen_text, callback_data=f"prompt_gen:{prompt_id}")
    builder.button(text=del_text, callback_data=f"prompt_del:{prompt_id}")
    builder.button(text=t(i18n, "buttons.back"), callback_data="prompt_menu:saved")
    builder.adjust(2, 1)
    
    text = t(i18n, "prompt.generate_confirm", title=prompt["title"], prompt=prompt["prompt_text"])
    await cb.message.edit_text(text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("prompt_gen:"))
async def cb_prompt_gen(cb: CallbackQuery, state: FSMContext, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.from_user is None or cb.message is None or cb.data is None or cb.bot is None:
        return
    prompt_id = int(cb.data.split(":", 1)[1])
    user = await get_user(cb.from_user.id)
    if user is None:
        return
    
    prompt = await get_user_prompt(user.id, prompt_id)
    if not prompt:
        await cb.message.edit_text(t(i18n, "errors.generic"))
        return
    
    try:
        await cb.message.delete()
    except Exception:
        pass
    
    await state.clear()
    await _do_generation(
        bot=cb.bot,
        chat_id=cb.message.chat.id,
        user_telegram_id=cb.from_user.id,
        prompt=prompt["prompt_text"],
        i18n=i18n,
    )


@router.callback_query(F.data.startswith("prompt_del:"))
async def cb_prompt_del(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    if cb.from_user is None or cb.message is None or cb.data is None:
        await cb.answer()
        return
    prompt_id = int(cb.data.split(":", 1)[1])
    user = await get_user(cb.from_user.id)
    if user is None:
        await cb.answer()
        return
    
    deleted = await delete_user_prompt(user.id, prompt_id)
    if deleted:
        await cb.answer(t(i18n, "prompt.delete_success"))
    else:
        await cb.answer(t(i18n, "errors.generic"))
        
    await cb_saved_prompts(cb, i18n)


@router.callback_query(F.data.startswith("save_pr:"))
async def cb_save_prompt(cb: CallbackQuery, state: FSMContext, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.from_user is None or cb.message is None or cb.data is None:
        return
    gen_id = int(cb.data.split(":", 1)[1])
    gen = await get_generation(gen_id)
    if gen is None:
        await cb.message.answer(t(i18n, "errors.generic"))
        return
    
    await state.update_data(save_prompt_text=gen.prompt)
    await state.set_state(PromptStates.waiting_for_title)
    await cb.message.answer(t(i18n, "prompt.ask_title"))


@router.message(PromptStates.waiting_for_title, USER_TEXT)
async def process_save_title(message: Message, state: FSMContext, i18n: dict[str, str]) -> None:
    if message.from_user is None or not message.text:
        return
    title = message.text.strip()
    data = await state.get_data()
    prompt_text = data.get("save_prompt_text")
    if not prompt_text:
        await message.answer(t(i18n, "errors.generic"))
        await state.clear()
        return
    
    user = await get_user(message.from_user.id)
    if user is None:
        await message.answer(t(i18n, "errors.generic"))
        await state.clear()
        return
    
    if not title or title.lower() in ("/cancel", "cancel", "отмена"):
        title = prompt_text[:25] + "..." if len(prompt_text) > 25 else prompt_text
        
    await save_user_prompt(user.id, title, prompt_text)
    await message.answer(t(i18n, "prompt.saved_success"))
    await state.clear()


# --- 2. Trending Templates Logic ---

@router.callback_query(F.data == "prompt_menu:trending")
async def cb_prompt_trending(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.message is None:
        return
    
    builder = InlineKeyboardBuilder()
    is_ru = i18n.get("menu.create_image") == "🎨 Создать изображение"
    for cat_key, cat_data in TRENDING_TEMPLATES.items():
        name = cat_data["ru_name"] if is_ru else cat_data["en_name"]
        builder.button(text=name, callback_data=f"trend_cat:{cat_key}")
    builder.button(text=t(i18n, "buttons.back"), callback_data="prompt_menu:main")
    builder.adjust(1)
    
    await cb.message.edit_text(t(i18n, "prompt.trending_categories"), reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("trend_cat:"))
async def cb_trend_cat(cb: CallbackQuery, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.message is None or cb.data is None:
        return
    cat_key = cb.data.split(":", 1)[1]
    cat_data = TRENDING_TEMPLATES.get(cat_key)
    if not cat_data:
        return
    
    is_ru = i18n.get("menu.create_image") == "🎨 Создать изображение"
    cat_name = cat_data["ru_name"] if is_ru else cat_data["en_name"]
    
    builder = InlineKeyboardBuilder()
    for idx, tpl in enumerate(cat_data["templates"]):
        btn_text = tpl.replace("[subject]", "...").strip()
        if len(btn_text) > 40:
            btn_text = btn_text[:37] + "..."
        builder.button(text=btn_text, callback_data=f"trend_tpl:{cat_key}:{idx}")
    builder.button(text=t(i18n, "buttons.back"), callback_data="prompt_menu:trending")
    builder.adjust(1)
    
    await cb.message.edit_text(t(i18n, "prompt.trending_list", category=cat_name), reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("trend_tpl:"))
async def cb_trend_tpl(cb: CallbackQuery, state: FSMContext, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.message is None or cb.data is None:
        return
    parts = cb.data.split(":")
    cat_key = parts[1]
    idx = int(parts[2])
    cat_data = TRENDING_TEMPLATES.get(cat_key)
    if not cat_data or idx >= len(cat_data["templates"]):
        return
    
    template = cat_data["templates"][idx]
    await state.update_data(template_text=template, cat_key=cat_key)
    await state.set_state(PromptStates.waiting_for_subject)
    
    builder = InlineKeyboardBuilder()
    builder.button(text=t(i18n, "buttons.cancel"), callback_data=f"trend_cat:{cat_key}")
    
    await cb.message.edit_text(
        t(i18n, "prompt.replace_subject", template=template),
        reply_markup=builder.as_markup()
    )


@router.message(PromptStates.waiting_for_subject, USER_TEXT)
async def process_template_subject(message: Message, state: FSMContext, i18n: dict[str, str]) -> None:
    if message.from_user is None or message.bot is None or not message.text:
        return
    subject = message.text.strip()
    if subject.lower() in ("/cancel", "cancel", "отмена"):
        await message.answer(t(i18n, "chat.returned_to_menu"))
        await state.clear()
        return
        
    data = await state.get_data()
    template = data.get("template_text")
    if not template:
        await message.answer(t(i18n, "errors.generic"))
        await state.clear()
        return
        
    final_prompt = template.replace("[subject]", subject)
    await state.clear()
    await _do_generation(
        bot=message.bot,
        chat_id=message.chat.id,
        user_telegram_id=message.from_user.id,
        prompt=final_prompt,
        i18n=i18n,
    )


# --- 3. Prompt Builder Wizard Logic ---

@router.callback_query(F.data == "prompt_menu:builder")
async def cb_prompt_builder(cb: CallbackQuery, state: FSMContext, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.message is None:
        return
    
    await state.update_data(pb_lighting=None, pb_angle=None, pb_lens=None)
    
    builder = InlineKeyboardBuilder()
    builder.button(text=t(i18n, "prompt.builder.lighting.natural"), callback_data="pb_light:natural")
    builder.button(text=t(i18n, "prompt.builder.lighting.golden"), callback_data="pb_light:golden")
    builder.button(text=t(i18n, "prompt.builder.lighting.studio"), callback_data="pb_light:studio")
    builder.button(text=t(i18n, "prompt.builder.lighting.dramatic"), callback_data="pb_light:dramatic")
    builder.button(text=t(i18n, "prompt.builder.lighting.neon"), callback_data="pb_light:neon")
    builder.button(text=t(i18n, "prompt.builder.lighting.none"), callback_data="pb_light:none")
    builder.button(text=t(i18n, "buttons.back"), callback_data="prompt_menu:main")
    builder.adjust(2, 2, 2, 1)
    
    await cb.message.edit_text(t(i18n, "prompt.builder_step1"), reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("pb_light:"))
async def cb_pb_light(cb: CallbackQuery, state: FSMContext, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.message is None or cb.data is None:
        return
    val = cb.data.split(":", 1)[1]
    if val != "none":
        await state.update_data(pb_lighting=val)
        
    builder = InlineKeyboardBuilder()
    builder.button(text=t(i18n, "prompt.builder.angle.portrait"), callback_data="pb_angle:portrait")
    builder.button(text=t(i18n, "prompt.builder.angle.wide"), callback_data="pb_angle:wide")
    builder.button(text=t(i18n, "prompt.builder.angle.macro"), callback_data="pb_angle:macro")
    builder.button(text=t(i18n, "prompt.builder.angle.aerial"), callback_data="pb_angle:aerial")
    builder.button(text=t(i18n, "prompt.builder.angle.none"), callback_data="pb_angle:none")
    builder.button(text=t(i18n, "buttons.back"), callback_data="prompt_menu:builder")
    builder.adjust(2, 2, 1, 1)
    
    await cb.message.edit_text(t(i18n, "prompt.builder_step2"), reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("pb_angle:"))
async def cb_pb_angle(cb: CallbackQuery, state: FSMContext, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.message is None or cb.data is None:
        return
    val = cb.data.split(":", 1)[1]
    if val != "none":
        await state.update_data(pb_angle=val)
        
    builder = InlineKeyboardBuilder()
    builder.button(text=t(i18n, "prompt.builder.lens.lens85"), callback_data="pb_lens:lens85")
    builder.button(text=t(i18n, "prompt.builder.lens.lens35"), callback_data="pb_lens:lens35")
    builder.button(text=t(i18n, "prompt.builder.lens.lens24"), callback_data="pb_lens:lens24")
    builder.button(text=t(i18n, "prompt.builder.lens.canon"), callback_data="pb_lens:canon")
    builder.button(text=t(i18n, "prompt.builder.lens.none"), callback_data="pb_lens:none")
    builder.button(text=t(i18n, "buttons.back"), callback_data="prompt_menu:builder")
    builder.adjust(2, 2, 1, 1)
    
    await cb.message.edit_text(t(i18n, "prompt.builder_step3"), reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("pb_lens:"))
async def cb_pb_lens(cb: CallbackQuery, state: FSMContext, i18n: dict[str, str]) -> None:
    await cb.answer()
    if cb.message is None or cb.data is None:
        return
    val = cb.data.split(":", 1)[1]
    if val != "none":
        await state.update_data(pb_lens=val)
        
    await state.set_state(PromptStates.waiting_for_builder_subject)
    
    builder = InlineKeyboardBuilder()
    builder.button(text=t(i18n, "buttons.cancel"), callback_data="prompt_menu:builder")
    
    await cb.message.edit_text(t(i18n, "prompt.builder_subject"), reply_markup=builder.as_markup())


@router.message(PromptStates.waiting_for_builder_subject, USER_TEXT)
async def process_builder_subject(message: Message, state: FSMContext, i18n: dict[str, str]) -> None:
    if message.from_user is None or message.bot is None or not message.text:
        return
    subject = message.text.strip()
    if subject.lower() in ("/cancel", "cancel", "отмена"):
        await message.answer(t(i18n, "chat.returned_to_menu"))
        await state.clear()
        return
        
    data = await state.get_data()
    lighting = data.get("pb_lighting")
    angle = data.get("pb_angle")
    lens = data.get("pb_lens")
    
    final_prompt = build_prompt(subject, lighting, angle, lens)
    await state.clear()
    await _do_generation(
        bot=message.bot,
        chat_id=message.chat.id,
        user_telegram_id=message.from_user.id,
        prompt=final_prompt,
        i18n=i18n,
    )
