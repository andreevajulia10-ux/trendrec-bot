"""Хендлер для ручного запроса дайджеста — /digest"""

import logging

from aiogram import Router, types
from aiogram.filters import Command

from bot.db.queries import get_user_niches, get_daily_trend, get_active_trends_for_niches
from bot.services.tasks import format_trend_block as _format_trend_block

logger = logging.getLogger(__name__)

router = Router(name="digest")


@router.message(Command("digest"))
async def cmd_digest(message: types.Message) -> None:
    """Показывает дайджест по запросу пользователя."""
    tg_id = message.from_user.id
    first_name = message.from_user.first_name or "\u0441\u043e\u0437\u0434\u0430\u0442\u0435\u043b\u044c"


    # Показываем "печатает", чтобы пользователь не думал что бот завис
    await message.bot.send_chat_action(tg_id, "typing")

    niches = await get_user_niches(tg_id)

    if not niches:
        await message.answer(
            "\U0001f615 \u0423 \u0442\u0435\u0431\u044f \u0435\u0449\u0451 \u043d\u0435 \u0432\u044b\u0431\u0440\u0430\u043d\u044b \u043d\u0438\u0448\u0438.\n"
            "\u041d\u0430\u043f\u0438\u0448\u0438 /niches, \u0447\u0442\u043e\u0431\u044b \u0432\u044b\u0431\u0440\u0430\u0442\u044c \u0442\u0435\u043c\u044b, \u0437\u0430 \u043a\u043e\u0442\u043e\u0440\u044b\u043c\u0438 \u0441\u043b\u0435\u0434\u0438\u0442\u044c."
        )
        return

    niche_ids = [n["id"] for n in niches]
    niche_names = [n["name"] for n in niches]

    # Получаем данные ДО того, как используем их
    daily_trend = await get_daily_trend(niche_ids)
    fresh_trends = await get_active_trends_for_niches(niche_ids, hours=24, limit=5)

    lines = [f"\U0001f4cb <b>\u0422\u0432\u043e\u0439 \u0434\u0430\u0439\u0434\u0436\u0435\u0441\u0442, {first_name}</b>\n"]

    if daily_trend:
        lines.append("\U0001f525 <b>\u0422\u0440\u0435\u043d\u0434 \u0434\u043d\u044f:</b>")
        lines.extend(_format_trend_block(daily_trend))
        lines.append("")

    if fresh_trends:
        lines.append("\U0001f4c8 <b>\u0421\u0432\u0435\u0436\u0438\u0435 \u0442\u0440\u0435\u043d\u0434\u044b \u0437\u0430 24\u0447:</b>")
        for i, t in enumerate(fresh_trends[:3], 1):
            lines.extend(_format_trend_block(t, i))
        lines.append("")
    else:
        lines.append("\U0001f4ed \u0421\u0432\u0435\u0436\u0438\u0445 \u0442\u0440\u0435\u043d\u0434\u043e\u0432 \u0437\u0430 \u0441\u0435\u0433\u043e\u0434\u043d\u044f \u043d\u0435\u0442 \u2014 \u043f\u0440\u043e\u0432\u0435\u0440\u044c \u043f\u043e\u0437\u0436\u0435.\n")

    lines.append(f"\U0001f4c2 <b>\u0422\u0432\u043e\u0438 \u043d\u0438\u0448\u0438:</b> {', '.join(niche_names)}")
    lines.append("")
    lines.append("\U0001f4a1 /trends \u2014 \u0432\u0441\u0435 \u0442\u0440\u0435\u043d\u0434\u044b")
    lines.append("\U0001f4a1 /idea \u2014 \u0438\u0434\u0435\u044f \u0434\u043b\u044f \u0432\u0438\u0434\u0435\u043e")
    lines.append("\U0001f4a1 /niches \u2014 \u0438\u0437\u043c\u0435\u043d\u0438\u0442\u044c \u043d\u0438\u0448\u0438")

    await message.answer("\n".join(lines))
