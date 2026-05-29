import asyncio
import logging
import random
from datetime import datetime

import aiohttp
from bs4 import BeautifulSoup

from bot.db.connection import get_connection

logger = logging.getLogger(__name__)

# Фейковые данные, если парс упал или Creative Center недоступен
FALLBACK_TRENDS = {
    "dance": [
        ("#dancechallenge", "Новый танцевальный челлендж", "hashtag", 850000),
        ("#hiphopmoves", "Трендовые hip-hop движения", "hashtag", 620000),
        ("#viralchoreo", "Вирусная хореография", "hashtag", 510000),
    ],
    "comedy": [
        ("#relatable", "Жизненные ситуации с юмором", "hashtag", 920000),
        ("#sketchcomedy", "Короткие смешные скетчи", "hashtag", 740000),
        ("#expectationvsreality", "Ожидание vs реальность", "hashtag", 680000),
    ],
    "education": [
        ("#learnontiktok", "Образовательный контент набирает обороты", "hashtag", 780000),
        ("#didyouknow", "Интересные факты за 60 секунд", "hashtag", 550000),
        ("#lifeprotips", "Лайфхаки для жизни", "hashtag", 490000),
    ],
    "beauty": [
        ("#makeuptutorial", "Туториалы по макияжу", "hashtag", 910000),
        ("#skincareroutine", "Уход за кожей", "hashtag", 670000),
        ("#transformation", "Трансформации до/после", "hashtag", 830000),
    ],
    "food": [
        ("#recipe", "Быстрые рецепты", "hashtag", 720000),
        ("#foodhack", "Лайфхаки с едой", "hashtag", 580000),
        ("#cookingathome", "Готовим дома", "hashtag", 440000),
    ],
    "sport": [
        ("#workout", "Домашние тренировки", "hashtag", 660000),
        ("#gymmotivation", "Мотивация для зала", "hashtag", 530000),
        ("#yogatiktok", "Йога и растяжка", "hashtag", 390000),
    ],
    "music": [
        ("#originalsong", "Авторские песни", "hashtag", 810000),
        ("#covers", "Каверы на популярные треки", "hashtag", 640000),
        ("#musicproduction", "Создание музыки", "hashtag", 470000),
    ],
    "gaming": [
        ("#gamingontiktok", "Игровой контент", "hashtag", 890000),
        ("#gamereview", "Обзоры игр", "hashtag", 560000),
        ("#minecraft", "Майнкрафт тренды", "hashtag", 710000),
    ],
    "tech": [
        ("#gadgets", "Новые гаджеты", "hashtag", 630000),
        ("#productivity", "Продуктивность и софт", "hashtag", 480000),
        ("#techreview", "Обзоры техники", "hashtag", 520000),
    ],
    "lifestyle": [
        ("#dailyvlog", "Ежедневные влоги", "hashtag", 590000),
        ("#morningroutine", "Утренние рутины", "hashtag", 540000),
        ("#organization", "Организация пространства", "hashtag", 410000),
    ],
}

IDEAS_FALLBACK = {
    "dance": [
        {"title": "Повтори танец из кино", "description": "Выбери культовый танец из фильма и повтори его в своём стиле", "script_preview": "1. Покажи оригинал, 2. Своя версия, 3. Сравнение"},
        {"title": "Танцевальный батл с другом", "description": "Вызови друга на танцевальный батл под трендовый трек", "script_preview": "1. Дуэт, 2. Поочерёдные проходки, 3. Победитель"},
    ],
    "comedy": [
        {"title": "Ситуация: утро перед работой", "description": "Покажи в комедийном ключе типичное утро", "script_preview": "1. Будильник, 2. 5 минут до выхода, 3. Финал"},
        {"title": "POV: твой внутренний голос", "description": "Озвучь внутренний монолог в неловкой ситуации", "script_preview": "1. Ситуация, 2. Мысли вслух, 3. Реакция"},
    ],
    "education": [
        {"title": "Сложная тема за 60 секунд", "description": "Объясни сложную концепцию простыми словами", "script_preview": "1. Проблема, 2. Аналогия, 3. Решение"},
        {"title": "3 факта, которые удивят", "description": "Подборка малоизвестных фактов по твоей теме", "script_preview": "1. Факт 1, 2. Факт 2, 3. Факт 3"},
    ],
    "beauty": [
        {"title": "Трансформация за 5 минут", "description": "Покажи быстрый макияж из обычного в праздничный", "script_preview": "1. До, 2. Процесс, 3. После"},
        {"title": "Разбор косметички", "description": "Топ-5 продуктов, которыми пользуешься каждый день", "script_preview": "1. Продукт 1, 2. ... , 5. Итоговый образ"},
    ],
    "food": [
        {"title": "Блюдо за 10 минут", "description": "Рецепт простого и вкусного блюда", "script_preview": "1. Ингредиенты, 2. Процесс, 3. Результат"},
        {"title": "Фуд-хак: как нарезать лук без слёз", "description": "Лайфхак для кухни, который облегчает готовку", "script_preview": "1. Проблема, 2. Лайфхак, 3. Удивление"},
    ],
    "sport": [
        {"title": "Зарядка на 5 минут", "description": "Быстрая утренняя зарядка без инвентаря", "script_preview": "1. Разминка, 2. Упражнения, 3. Растяжка"},
        {"title": "Челлендж: 100 приседаний в день", "description": "Покажи свой прогресс за неделю", "script_preview": "1. День 1, 2. День 7, 3. Результат"},
    ],
    "music": [
        {"title": "Караоке под трендовый трек", "description": "Спой популярную песню в своём стиле", "script_preview": "1. Интро, 2. Припев, 3. Финал"},
        {"title": "Как я написал трек за час", "description": "Покажи процесс создания музыки", "script_preview": "1. Идея, 2. Бит, 3. Готовый трек"},
    ],
    "gaming": [
        {"title": "Лучший момент в игре", "description": "Нарезка эпичных моментов", "script_preview": "1. Момент 1, 2. Момент 2, 3. Финал"},
        {"title": "Обзор за 30 секунд", "description": "Короткий обзор игры, в которую стоит поиграть", "script_preview": "1. Жанр, 2. Графика, 3. Вердикт"},
    ],
    "tech": [
        {"title": "Гаджет, который изменил мою жизнь", "description": "Расскажи о технике, которую реально используешь", "script_preview": "1. Что это, 2. Как использую, 3. Стоит ли"},
        {"title": "Топ-3 приложений для продуктивности", "description": "Подборка полезных приложений", "script_preview": "1. Приложение 1, 2. ..., 3. Бонус"},
    ],
    "lifestyle": [
        {"title": "Моя утренняя рутина", "description": "Покажи свой идеальный старт дня", "script_preview": "1. Пробуждение, 2. Ритуалы, 3. Старт"},
        {"title": "Организация рабочего места", "description": "Преображение рабочего стола", "script_preview": "1. До, 2. Процесс, 3. Результат"},
    ],
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

TIKTOK_CC_URL = "https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/en"


async def fetch_trends_from_tiktok() -> dict[str, list[dict]] | None:
    """Пытается спарсить TikTok Creative Center. Возвращает None если не получилось."""
    try:
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(TIKTOK_CC_URL, timeout=15) as resp:
                if resp.status != 200:
                    logger.warning("TikTok CC returned status %s", resp.status)
                    return None
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")

                # Пытаемся найти трендовые хештеги — структура может меняться
                trends_by_niche: dict[str, list[dict]] = {}
                current_niche = "general"
                for tag in soup.find_all(["h2", "h3", "h4", "a"]):
                    text = tag.get_text(strip=True)
                    if text.lower() in [s.lower() for s in FALLBACK_TRENDS.keys()]:
                        current_niche = text.lower()
                    if tag.name == "a" and text.startswith("#"):
                        niche_list = trends_by_niche.setdefault(current_niche, [])
                        niche_list.append({
                            "title": text,
                            "description": tag.find_next("p").get_text(strip=True) if tag.find_next("p") else "",
                            "trend_type": "hashtag",
                            "engagement": random.randint(100000, 900000),
                        })

                if trends_by_niche:
                    return trends_by_niche
                return None
    except Exception as e:
        logger.warning("TikTok parse failed: %s", e)
        return None


def _build_fallback_trends() -> dict[str, list[dict]]:
    """Собирает тренды из запасного словаря."""
    result = {}
    for slug, trends in FALLBACK_TRENDS.items():
        result[slug] = [
            {"title": t[0], "description": t[1], "trend_type": t[2], "engagement": t[3]}
            for t in trends
        ]
    return result


def _build_fallback_ideas() -> dict[str, list[dict]]:
    """Собирает идеи из запасного словаря."""
    return {slug: ideas for slug, ideas in IDEAS_FALLBACK.items()}


async def save_trends(trends_by_niche: dict[str, list[dict]]) -> int:
    """Сохраняет тренды в БД. Возвращает количество сохранённых."""
    conn = get_connection()
    count = 0
    for slug, trends in trends_by_niche.items():
        niche = conn.execute("SELECT id FROM niches WHERE slug = ?", (slug,)).fetchone()
        if not niche:
            continue
        niche_id = niche["id"]
        for t in trends:
            exists = conn.execute(
                "SELECT id FROM trends WHERE title = ? AND niche_id = ?",
                (t["title"], niche_id)
            ).fetchone()
            if exists:
                continue
            conn.execute(
                "INSERT INTO trends (title, description, niche_id, source, trend_type, engagement, collected_at) "
                "VALUES (?, ?, ?, 'tiktok_cc_fallback', ?, ?, datetime('now'))",
                (t["title"], t.get("description", ""), niche_id, t.get("trend_type", "hashtag"), t.get("engagement", 0))
            )
            count += 1
    conn.commit()
    logger.info("Saved %d new trends", count)
    return count


async def save_ideas(ideas_by_niche: dict[str, list[dict]]) -> int:
    """Сохраняет идеи в БД. Возвращает количество сохранённых."""
    conn = get_connection()
    count = 0
    for slug, ideas in ideas_by_niche.items():
        niche = conn.execute("SELECT id FROM niches WHERE slug = ?", (slug,)).fetchone()
        if not niche:
            continue
        niche_id = niche["id"]
        for idea in ideas:
            exists = conn.execute(
                "SELECT id FROM ideas WHERE title = ? AND niche_id = ?",
                (idea["title"], niche_id)
            ).fetchone()
            if exists:
                continue
            conn.execute(
                "INSERT INTO ideas (niche_id, title, description, script_preview) "
                "VALUES (?, ?, ?, ?)",
                (niche_id, idea["title"], idea.get("description", ""), idea.get("script_preview", ""))
            )
            count += 1
    conn.commit()
    logger.info("Saved %d new ideas", count)
    return count


async def collect_all() -> tuple[int, int]:
    """Главная функция: собирает тренды и идеи. Возвращает (тренды, идеи)."""
    logger.info("Starting trend collection...")

    # Пробуем TikTok Creative Center
    real_trends = await fetch_trends_from_tiktok()

    if real_trends:
        trends_data = real_trends
        logger.info("Using real data from TikTok Creative Center")
    else:
        trends_data = _build_fallback_trends()
        logger.info("TikTok CC unavailable, using fallback data")

    trend_count = await save_trends(trends_data)

    # Идеи всегда из запасного словаря (их можно потом генерировать через LLM)
    ideas_data = _build_fallback_ideas()
    idea_count = await save_ideas(ideas_data)

    return trend_count, idea_count


async def collect_if_empty() -> None:
    """Заполняет БД, если там пусто."""
    conn = get_connection()
    trend_count = conn.execute("SELECT COUNT(*) FROM trends").fetchone()[0]
    idea_count = conn.execute("SELECT COUNT(*) FROM ideas").fetchone()[0]

    if trend_count == 0 or idea_count == 0:
        logger.info("DB is empty (trends=%d, ideas=%d), collecting...", trend_count, idea_count)
        await collect_all()
    else:
        logger.info("DB already has data (trends=%d, ideas=%d), skipping", trend_count, idea_count)


if __name__ == "__main__":
    async def _test():
        t, i = await collect_all()
        print(f"Collected: {t} trends, {i} ideas")
    asyncio.run(_test())
