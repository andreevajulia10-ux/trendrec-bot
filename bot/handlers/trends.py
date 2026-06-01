"""Хендлер для /trends — просмотр трендов."""

import logging

from aiogram import Router, types
from aiogram.filters import Command

from bot.db.queries import get_user_niches, get_trends_for_niches, get_trend_examples

logger = logging.getLogger(__name__)

router = Router(name="trends")


@router.message(Command("trends"))
async def cmd_trends(message: types.Message) -> None:
    """Показывает тренды по нишам пользователя."""
    tg_id = message.from_user.id
    niches = await get_user_niches(tg_id)

    if not niches:
        await message.answer(
            "😕 Сначала выбери темы через /start\n"
            "Или настрой их заново: /niches"
        )
        return

    niche_ids = [n["id"] for n in niches]
    trends = await get_trends_for_niches(niche_ids, limit=5)

    if not trends:
        await message.answer(
            "🔍 Пока нет трендов по твоим темам.\n"
            "Скоро появятся — я собираю их каждый день!"
        )
        return

    lines = ["📌 <b>Тренды для тебя:</b>\n"]

    for i, t in enumerate(trends, 1):
        title = t["title"]
        desc = t.get("description") or ""
        eng = t.get("engagement") or 0

        lines.append(f"{i}. <b>{title}</b>")
        if desc:
            lines.append(f"   {desc}")
        lines.append(f"   👀 Активность: {eng:,}".replace(",", " "))

        # Примеры видео для этого тренда
        examples = await get_trend_examples(t["id"], limit=2)
        if examples:
            for ex in examples:
                ex_title = ex.get("video_title") or "Смотреть пример"
                lines.append(f"   ▶️ <a href=\"{ex['video_url']}\">{ex_title}</a>")
        else:
            # Если нет примеров — показываем video_url из самого тренда
            video_url = t.get("video_url", "")
            if video_url:
                lines.append(f"   ▶️ <a href=\"{video_url}\">Смотреть пример</a>")

        lines.append("")

    lines.append("💡 /idea — идея для видео")
    lines.append("📋 /digest — дайджест")

    await message.answer("\n".join(lines))

