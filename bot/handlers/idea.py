"""Хендлер для /idea — генерация идей для видео."""

import logging
import random

from aiogram import Router, types
from aiogram.filters import Command

from bot.db.queries import (
    get_user_niches,
    get_idea_for_niche,
    get_trends_for_niches,
)
from bot.services.idea_generator import (
    idea_generator,
    GenerationRequest,
    format_ideas_for_tg,
)

logger = logging.getLogger(__name__)

router = Router(name="idea")


# =============================================================================
# Fallback-идеи (когда AI недоступен)
# =============================================================================

FALLBACK_IDEAS = {
    "dance": [
        {"title": "Повтори танец из кино", "desc": "Выбери культовый танец из фильма и повтори"},
        {"title": "Танцевальный батл с другом", "desc": "Вызови друга на танцевальный батл"},
    ],
    "comedy": [
        {"title": "Ситуация: утро перед работой", "desc": "Покажи типичное утро в комедийном ключе"},
        {"title": "POV: твой внутренний голос", "desc": "Озвучь внутренний монолог в неловкой ситуации"},
    ],
    "education": [
        {"title": "Сложная тема за 60 секунд", "desc": "Объясни сложную концепцию простыми словами"},
        {"title": "3 факта, которые удивят", "desc": "Подборка малоизвестных фактов"},
    ],
    "beauty": [
        {"title": "Трансформация за 5 минут", "desc": "Покажи быстрый макияж"},
        {"title": "Разбор косметички", "desc": "Топ продуктов, которыми пользуешься"},
    ],
    "food": [
        {"title": "Блюдо за 10 минут", "desc": "Рецепт простого блюда"},
        {"title": "Фуд-хак: как нарезать лук без слёз", "desc": "Кухонный лайфхак"},
    ],
    "sport": [
        {"title": "Зарядка на 5 минут", "desc": "Быстрая утренняя зарядка"},
        {"title": "Челлендж: 100 приседаний", "desc": "Покажи прогресс за неделю"},
    ],
    "music": [
        {"title": "Караоке под трендовый трек", "desc": "Спой популярную песню"},
        {"title": "Как я написал трек за час", "desc": "Процесс создания музыки"},
    ],
    "gaming": [
        {"title": "Лучший момент в игре", "desc": "Нарезка эпичных моментов"},
        {"title": "Обзор за 30 секунд", "desc": "Короткий обзор игры"},
    ],
    "tech": [
        {"title": "Гаджет, который изменил жизнь", "desc": "Расскажи о технике"},
        {"title": "Топ-3 приложений", "desc": "Подборка полезных приложений"},
    ],
    "lifestyle": [
        {"title": "Моя утренняя рутина", "desc": "Покажи идеальный старт дня"},
        {"title": "Организация рабочего места", "desc": "Преображение стола"},
    ],
}


def _get_fallback_idea(niche_slug: str) -> str:
    """Возвращает fallback-идею, если AI недоступен."""
    ideas = FALLBACK_IDEAS.get(niche_slug, FALLBACK_IDEAS["lifestyle"])
    idea = random.choice(ideas)
    return (
        f"💡 <b>Идея для видео</b>\n\n"
        f"<b>{idea['title']}</b>\n"
        f"{idea['desc']}\n\n"
        f"📝 Сними это и посмотри, как залетит!\n\n"
        f"💡 /idea — ещё идея"
    )


@router.message(Command("idea"))
async def cmd_idea(message: types.Message) -> None:
    """Показывает идею для видео на основе ниш пользователя."""
    tg_id = message.from_user.id
    niches = await get_user_niches(tg_id)

    if not niches:
        await message.answer(
            "😕 Сначала выбери темы через /start\n"
            "Или настрой их заново: /niches"
        )
        return

    # Берём случайную нишу пользователя
    niche = random.choice(niches)
    niche_name = niche["name"]
    niche_slug = niche["slug"]

    # Пробуем AI-генерацию
    try:
        trends = await get_trends_for_niches([niche["id"]], limit=5)
        trend_titles = [t["title"] for t in trends]

        request = GenerationRequest(
            niche_name=niche_name,
            niche_slug=niche_slug,
            trends=trend_titles,
            count=2,
        )

        ideas = await idea_generator.generate(request)

        if ideas:
            text = format_ideas_for_tg(ideas, niche_name, message.from_user.first_name)
            await message.answer(text)
            return
    except Exception as e:
        logger.warning("AI-генерация не удалась для %s: %s", niche_slug, e)

    # Fallback: статическая идея
    await message.answer(_get_fallback_idea(niche_slug))

