"""Хендлер для /start — регистрация и выбор ниш."""

import logging

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.db.queries import (
    get_or_create_user,
    get_all_niches,
    set_user_niches,
    get_user_niches,
)

logger = logging.getLogger(__name__)

router = Router(name="start")


@router.message(Command("start"))
async def cmd_start(message: types.Message) -> None:
    """Регистрирует пользователя и предлагает выбрать ниши."""
    tg_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    user = await get_or_create_user(tg_id, username, first_name, last_name)

    if not user:
        await message.answer("❌ Ошибка регистрации. Попробуй позже.")
        return

    text = (
        f"👋 Привет, {first_name or 'создатель'}!\n\n"
        "Я помогу тебе находить тренды TikTok по твоим интересам.\n"
        "Каждый день собираю свежие идеи и тренды.\n\n"
        "📌 Выбери темы, которые тебе интересны:"
    )

    await _show_niche_selection(message, text)


async def _show_niche_selection(
    message: types.Message,
    text: str = "Выбери темы (можно несколько):",
) -> None:
    """Показывает клавиатуру выбора ниш."""
    niches = await get_all_niches()
    builder = InlineKeyboardBuilder()

    for niche in niches:
        builder.button(text=f"📂 {niche['name']}", callback_data=f"niche_{niche['id']}")

    builder.adjust(2)
    builder.row(
        InlineKeyboardButton(text="✅ Готово", callback_data="niches_done"),
        InlineKeyboardButton(text="❌ Очистить", callback_data="niches_clear"),
    )

    await message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(lambda c: c.data and c.data.startswith("niche_"))
async def callback_niche_toggle(callback: types.CallbackQuery) -> None:
    """Обрабатывает выбор/отмену ниши."""
    if not callback.data:
        return

    tg_id = callback.from_user.id

    if callback.data == "niches_done":

        current = await get_user_niches(tg_id)
        if not current:
            await callback.message.edit_text(
                "⚠️ Выбери хотя бы одну тему!\n\n"
                "Напиши /start чтобы попробовать снова."
            )
        else:
            names = [n["name"] for n in current]
            await callback.message.edit_text(
                f"✅ Отлично! Я буду следить за трендами по:\n"
                f"{', '.join(names)}\n\n"
                f"📈 /trends — смотреть тренды\n"
                f"💡 /idea — идея для видео\n"
                f"📋 /digest — дайджест"
            )
        await callback.answer()
        return

    if callback.data == "niches_clear":
        await set_user_niches(tg_id, [])
        await callback.message.edit_text(
            "🗑️ Темы очищены.\n"
            "Напиши /start чтобы выбрать заново."
        )
        await callback.answer()
        return

    # Toggle ниши
    niche_id = int(callback.data.split("_")[1])
    current = await get_user_niches(tg_id)
    current_ids = [n["id"] for n in current]

    if niche_id in current_ids:
        current_ids.remove(niche_id)
    else:
        current_ids.append(niche_id)

    await set_user_niches(tg_id, current_ids)

    # Обновляем сообщение
    updated = await get_user_niches(tg_id)
    names = [n["name"] for n in updated]
    status_text = f"✅ Выбрано: {', '.join(names)}" if names else "Темы не выбраны"

    await callback.message.edit_text(
        f"📌 {status_text}\n\n"
        "Выбери темы (можно несколько) и нажми «Готово»:",
        reply_markup=callback.message.reply_markup,
    )
    await callback.answer()


@router.message(Command("niches"))
async def cmd_niches(message: types.Message) -> None:
    """Команда для изменения ниш."""
    await _show_niche_selection(message, "📂 Измени свои темы (можно несколько):")

