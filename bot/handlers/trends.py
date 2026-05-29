from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.db.queries import get_user_niches, get_trends_for_niches

router = Router()


@router.message(Command("trends"))
async def cmd_trends(message: Message) -> None:
    niches = get_user_niches(message.from_user.id)
    if not niches:
        await message.answer(
            "Сначала выбери темы через /start\n"
            "Или настрой их заново: /niches"
        )
        return

    niche_ids = [n["id"] for n in niches]
    trends = get_trends_for_niches(niche_ids, limit=5)

    if not trends:
        await message.answer(
            "\U0001f50d Пока нет трендов по твоим темам.\n"
            "Скоро появятся - я собираю их каждый день!"
        )
        return

    lines = ["\U0001f4cc <b>Тренды для тебя:</b>\n"]
    for i, t in enumerate(trends, 1):
        title = t["title"]
        desc = t["description"] or "Нет описания"
        eng = t["engagement"] or 0
        lines.append(f"{i}. <b>{title}</b>")
        lines.append(f"   {desc}")
        lines.append(f"   \U0001f4aa Активность: {eng}")
        lines.append("")

    await message.answer("\n".join(lines))
