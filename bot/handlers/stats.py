"""Хендлер для статистики — /stats"""

import logging

from aiogram import Router, types
from aiogram.filters import Command

from bot.db.connection import fetchval, fetchrow

logger = logging.getLogger(__name__)

router = Router(name="stats")


@router.message(Command("stats"))
async def cmd_stats(message: types.Message) -> None:
    """Показывает статистику бота."""
    users_count = await fetchval("SELECT COUNT(*) FROM users") or 0
    active_count = await fetchval("SELECT COUNT(*) FROM users WHERE is_active = TRUE") or 0
    trends_count = await fetchval("SELECT COUNT(*) FROM trends") or 0
    ideas_count = await fetchval("SELECT COUNT(*) FROM ideas") or 0
    niches_count = await fetchval("SELECT COUNT(*) FROM niches") or 0

    # Последний тренд
    last_trend = await fetchrow(
        "SELECT title, collected_at FROM trends ORDER BY collected_at DESC LIMIT 1"
    )

    text = (
        "📊 <b>Статистика бота</b>\n\n"
        f"👥 Пользователей: {users_count}\n"
        f"✅ Активных: {active_count}\n"
        f"📂 Ниш: {niches_count}\n"
        f"📈 Трендов собрано: {trends_count}\n"
        f"💡 Идей: {ideas_count}\n"
    )

    if last_trend:
        text += f"\n🕐 Последний тренд: {last_trend['title']}\n"
        text += f"   Собран: {last_trend['collected_at']}"

    await message.answer(text)

