from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.db.queries import get_or_create_user, get_all_niches, set_user_niches

router = Router()


class Onboarding(StatesGroup):
    choosing_niches = State()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    user = await get_or_create_user(
        tg_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    await message.answer(
        f"Привет, {message.from_user.first_name or 'создатель'}! \U0001f44b\n\n"
        "Я TrendRec - твой помощник по трендам TikTok.\n"
        "Я буду присылать тебе свежие тренды и идеи для видео.\n\n"
        "Давай сначала выберем темы, которые тебя интересуют."
    )

    niches = await get_all_niches()
    if not niches:
        await message.answer("Пока нет доступных ниш. Попробуй позже.")
        return

    builder = InlineKeyboardBuilder()
    for niche in niches:
        builder.button(
            text=niche["name"],
            callback_data=f"niche_{niche['id']}"
        )
    builder.button(text="\u2705 Готово", callback_data="niche_done")
    builder.adjust(2)

    await state.set_state(Onboarding.choosing_niches)
    await state.set_data({"selected": []})
    await message.answer("Выбери темы (можно несколько):", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("niche_"), Onboarding.choosing_niches)
async def niche_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    selected: list = data.get("selected", [])

    if callback.data == "niche_done":
        if not selected:
            await callback.answer("Выбери хотя бы одну тему!", show_alert=True)
            return
        await set_user_niches(callback.from_user.id, selected)
        await state.clear()
        await callback.message.edit_text(
            f"\u2705 Темы сохранены!\n\n"
            "Теперь ты можешь пользоваться командами:\n"
            "/trends - показать тренды\n"
            "/idea - идея для видео\n\n"
            "Каждый день я буду присылать тебе тренд дня."
        )
        await callback.answer()
        return

    niche_id = int(callback.data.replace("niche_", ""))
    if niche_id in selected:
        selected.remove(niche_id)
    else:
        selected.append(niche_id)

    await state.update_data(selected=selected)

    niches = await get_all_niches()
    builder = InlineKeyboardBuilder()
    for niche in niches:
        check = "\u2705 " if niche["id"] in selected else ""
        builder.button(
            text=f"{check}{niche['name']}",
            callback_data=f"niche_{niche['id']}"
        )
    builder.button(text="\u2705 Готово", callback_data="niche_done")
    builder.adjust(2)

    await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    await callback.answer()
