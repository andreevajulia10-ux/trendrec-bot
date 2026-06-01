"""Хендлер для настроек — /settings"""

import logging

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.db.queries import get_digest_enabled, set_digest_enabled

logger = logging.getLogger(__name__)

router = Router(name="settings")


@router.message(Command("settings"))
async def cmd_settings(message: types.Message) -> None:
    """Показывает настройки пользователя."""
    tg_id = message.from_user.id
    digest_enabled = await get_digest_enabled(tg_id)

    text = (
        "⚙️ <b>Настройки</b>\n\n"
        f"📬 Ежедневная рассылка: {'✅ Включена' if digest_enabled else '❌ Отключена'}\n\n"
        "Выбери, что хочешь изменить:"
    )

    builder = InlineKeyboardBuilder()
    if digest_enabled:
        builder.button(text="🔇 Отключить рассылку", callback_data="digest_off")
    else:
        builder.button(text="🔔 Включить рассылку", callback_data="digest_on")
    builder.button(text="📂 Изменить ниши", callback_data="change_niches")
    builder.adjust(1)

    await message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(lambda c: c.data in ("digest_on", "digest_off"))
async def callback_digest_toggle(callback: types.CallbackQuery) -> None:
    """Включает/отключает рассылку."""
    tg_id = callback.from_user.id
    enabled = callback.data == "digest_on"

    await set_digest_enabled(tg_id, enabled)

    status = "включена" if enabled else "отключена"
    await callback.message.edit_text(
        f"✅ Рассылка {status}.\n"
        "Изменить можно в любой момент через /settings"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "change_niches")
async def callback_change_niches(callback: types.CallbackQuery) -> None:
    """Перенаправляет на /niches."""
    await callback.message.answer("📂 Используй команду /niches чтобы изменить темы")
    await callback.answer()