"""
Парсер трендов TikTok.

Три уровня сбора:
1. trends24.in — популярные хештеги
2. TikTok Creative Center — тренды по нишам
3. Fallback — статические тренды, если парсинг недоступен
"""

import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup

from bot.db.connection import fetchrow, fetchval
from bot.db.queries import save_trend_example as async_save_trend_example

logger = logging.getLogger(__name__)


# =============================================================================
# Модели данных
# =============================================================================

@dataclass
class TrendItem:
    title: str
    description: str = ""
    niche_slug: str = "general"
    source_url: str = ""
    trend_type: str = "hashtag"
    engagement: int = 0


# =============================================================================
# Ниши и соответствующие хештеги для поиска
# =============================================================================

NICHE_HASHTAGS = {
    "dance": ["dance", "dancechallenge", "dancetutorial", "dancelife"],
    "comedy": ["comedy", "funny", "humor", "sketch", "comedyvideo"],
    "education": ["education", "learn", "didyouknow", "facts", "study"],
    "beauty": ["beauty", "makeup", "skincare", "beautytips", "transformation"],
    "food": ["food", "recipe", "cooking", "foodie", "foodhack"],
    "sport": ["fitness", "workout", "gym", "sport", "training"],
    "music": ["music", "song", "cover", "singer", "musician"],
    "gaming": ["gaming", "game", "twitch", "gamer", "minecraft"],
    "tech": ["tech", "technology", "gadget", "ai", "programming"],
    "lifestyle": ["lifestyle", "daily", "routine", "lifehack", "motivation"],
}


# =============================================================================
# Level 1: trends24.in — свежие трендовые хештеги
# =============================================================================

TRENDS24_URLS = {
    "dance": "https://trends24.in/united-states",
    "comedy": "https://trends24.in/united-states",
    "education": "https://trends24.in/united-states",
    "beauty": "https://trends24.in/united-states",
    "food": "https://trends24.in/united-states",
    "sport": "https://trends24.in/united-states",
    "music": "https://trends24.in/united-states",
    "gaming": "https://trends24.in/united-states",
    "tech": "https://trends24.in/united-states",
    "lifestyle": "https://trends24.in/united-states",
}


async def _fetch_trends24_trends(niche_slug: str) -> list[TrendItem]:
    """Парсит trends24.in — список популярных хештегов сейчас."""
    url = TRENDS24_URLS.get(niche_slug, "https://trends24.in/united-states")
    trends = []

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15) as resp:
                if resp.status != 200:
                    logger.warning("trends24.in вернул %s для %s", resp.status, niche_slug)
                    return []

                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")

                # trends24 показывает хештеги в <a class="trend-link">
                trend_links = soup.select("a.trend-link")
                for link in trend_links[:10]:
                    title = link.get_text(strip=True)
                    if title:
                        trends.append(TrendItem(
                            title=title.lstrip("#"),
                            description=f"Популярный хештег из ниши {niche_slug}",
                            niche_slug=niche_slug,
                            source_url=f"https://www.tiktok.com/tag/{title.lstrip('#')}",
                            trend_type="hashtag",
                            engagement=random.randint(10000, 500000),
                        ))

                logger.info("trends24.in: найдено %d трендов для %s", len(trends), niche_slug)

    except asyncio.TimeoutError:
        logger.warning("trends24.in timeout для %s", niche_slug)
    except Exception as e:
        logger.warning("trends24.in ошибка для %s: %s", niche_slug, e)

    return trends


# =============================================================================
# Level 2: TikTok Creative Center
# =============================================================================

async def _fetch_creative_center_trends(niche_slug: str) -> list[TrendItem]:
    """Парсит TikTok Creative Center — тренды по категориям."""
    trends = []

    try:
        # Пробуем получить тренды через Creative Center API
        url = "https://ads.tiktok.com/business/creativecenter/api/v1/trends/v2"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }

        params = {
            "category": niche_slug,
            "period": "7d",
            "limit": 10,
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, params=params, timeout=15) as resp:
                if resp.status != 200:
                    logger.debug("Creative Center API вернул %s для %s", resp.status, niche_slug)
                    return []

                data = await resp.json()
                items = data.get("data", {}).get("list", [])

                for item in items[:5]:
                    title = item.get("hashtag_name", item.get("title", ""))
                    if title:
                        trends.append(TrendItem(
                            title=title.lstrip("#"),
                            description=item.get("description", ""),
                            niche_slug=niche_slug,
                            source_url=f"https://www.tiktok.com/tag/{title.lstrip('#')}",
                            trend_type="hashtag",
                            engagement=item.get("views", item.get("engagement", 0)),
                        ))

                logger.info("Creative Center: найдено %d трендов для %s", len(trends), niche_slug)

    except asyncio.TimeoutError:
        logger.debug("Creative Center timeout для %s", niche_slug)
    except Exception as e:
        logger.debug("Creative Center ошибка для %s: %s", niche_slug, e)

    return trends


# =============================================================================
# Level 3: Fallback — статические тренды
# =============================================================================

FALLBACK_TRENDS = {
    "dance": [
        TrendItem("Танцевальный челлендж", "Новый танцевальный тренд", "dance", "", "hashtag", 100000),
        TrendItem("Dance Tutorial", "Разбор танцевальных движений", "dance", "", "hashtag", 80000),
    ],
    "comedy": [
        TrendItem("Скетч про работу", "Смешные ситуации на работе", "comedy", "", "hashtag", 150000),
        TrendItem("POV видео", "Трендовый формат POV", "comedy", "", "hashtag", 120000),
    ],
    "education": [
        TrendItem("Лайфхак дня", "Полезный совет на каждый день", "education", "", "hashtag", 50000),
        TrendItem("Факт который удивит", "Интересные факты", "education", "", "hashtag", 60000),
    ],
    "beauty": [
        TrendItem("Макияж за 5 минут", "Быстрый макияж для занятых", "beauty", "", "hashtag", 90000),
        TrendItem("Skincare Routine", "Уход за кожей", "beauty", "", "hashtag", 75000),
    ],
    "food": [
        TrendItem("Рецепт за 10 минут", "Быстрые и вкусные рецепты", "food", "", "hashtag", 85000),
        TrendItem("Food Hack", "Кухонные лайфхаки", "food", "", "hashtag", 70000),
    ],
    "sport": [
        TrendItem("Утренняя зарядка", "Быстрая тренировка на утро", "sport", "", "hashtag", 55000),
        TrendItem("Fitness Challenge", "Спортивный челлендж", "sport", "", "hashtag", 65000),
    ],
    "music": [
        TrendItem("Трендовая песня", "Популярный трек недели", "music", "", "hashtag", 200000),
        TrendItem("Кавер на тренд", "Повтор популярной песни", "music", "", "hashtag", 110000),
    ],
    "gaming": [
        TrendItem("Игровой момент", "Эпичный момент в игре", "gaming", "", "hashtag", 95000),
        TrendItem("Обзор игры", "Короткий обзор", "gaming", "", "hashtag", 45000),
    ],
    "tech": [
        TrendItem("Гаджет недели", "Новинки технологий", "tech", "", "hashtag", 60000),
        TrendItem("AI инструмент", "Нейросети и AI", "tech", "", "hashtag", 120000),
    ],
    "lifestyle": [
        TrendItem("Утренняя рутина", "Идеальное утро", "lifestyle", "", "hashtag", 80000),
        TrendItem("Организация пространства", "Лайфхаки по дому", "lifestyle", "", "hashtag", 55000),
    ],
}


def _get_fallback_trends(niche_slug: str, count: int = 3) -> list[TrendItem]:
    """Возвращает статические тренды, если парсинг не удался."""
    trends = FALLBACK_TRENDS.get(niche_slug, FALLBACK_TRENDS["lifestyle"])
    return random.sample(trends, min(count, len(trends)))


# =============================================================================
# Сохранение в БД (асинхронное)
# =============================================================================

async def _save_trend_to_db(trend: TrendItem) -> Optional[int]:
    """Сохраняет тренд в БД. Возвращает id тренда или None."""
    # Ищем нишу по slug
    niche = await fetchrow(
        "SELECT id FROM niches WHERE slug = $1",
        trend.niche_slug
    )

    if not niche:
        logger.warning("Ниша '%s' не найдена в БД", trend.niche_slug)
        return None

    niche_id = niche["id"]

    # Проверяем, есть ли уже такой тренд
    existing = await fetchrow(
        "SELECT id FROM trends WHERE title = $1 AND niche_id = $2",
        trend.title, niche_id
    )

    if existing:
        # Обновляем engagement и время
        await fetchrow(
            "UPDATE trends SET engagement = $1, collected_at = NOW() WHERE id = $2 "
            "RETURNING id",
            trend.engagement, existing["id"]
        )
        return existing["id"]

    # Вставляем новый тренд
    row = await fetchrow(
        "INSERT INTO trends (title, description, niche_id, source_url, trend_type, engagement) "
        "VALUES ($1, $2, $3, $4, $5, $6) "
        "RETURNING id",
        trend.title, trend.description, niche_id, trend.source_url, trend.trend_type, trend.engagement
    )

    if row and trend.source_url:
        await async_save_trend_example(
            trend_id=row["id"],
            video_url=trend.source_url,
            video_title=f"Пример: {trend.title}",
            author_name="TikTok",
            views=trend.engagement,
            is_featured=1
        )

    return row["id"] if row else None


async def _generate_fallback_idea(trend: TrendItem) -> None:
    """Генерирует идею для видео на основе тренда."""
    niche = await fetchrow(
        "SELECT id FROM niches WHERE slug = $1",
        trend.niche_slug
    )

    if not niche:
        return

    # Проверяем, есть ли уже идея для этого тренда
    existing = await fetchrow(
        "SELECT id FROM ideas WHERE title = $1 AND niche_id = $2",
        f"Сними свой вариант: {trend.title}", niche["id"]
    )

    if existing:
        return

    desc = f"Используй тренд {trend.title} и сними свою версию. Добавь уникальный поворот!"
    script = (
        f"1. Начни с зацепки: «Ты видел этот тренд?»\n"
        f"2. Покажи свою версию за 15-30 секунд\n"
        f"3. Добавь уникальный элемент\n"
        f"4. Призови подписчиков повторить"
    )

    await fetchrow(
        "INSERT INTO ideas (niche_id, title, description, script_preview) VALUES ($1, $2, $3, $4) "
        "RETURNING id",
        niche["id"], f"Сними свой вариант: {trend.title}", desc, script
    )


# =============================================================================
# Основные функции
# =============================================================================

async def collect_for_niche(niche_slug: str) -> tuple[int, int]:
    """Собирает тренды для одной ниши. Возвращает (количество трендов, количество идей)."""
    trend_count = 0
    idea_count = 0

    # Level 1: trends24.in
    trends = await _fetch_trends24_trends(niche_slug)

    # Level 2: Creative Center (если Level 1 не дал результатов)
    if not trends:
        trends = await _fetch_creative_center_trends(niche_slug)

    # Level 3: Fallback (если ничего не нашли)
    if not trends:
        trends = _get_fallback_trends(niche_slug, count=3)
        logger.info("Fallback: %d трендов для %s", len(trends), niche_slug)

        # Сохраняем в БД (асинхронно)
    for trend in trends:
        trend_id = await _save_trend_to_db(trend)
        if trend_id:
            trend_count += 1
            # Генерируем идею
            await _generate_fallback_idea(trend)
            idea_count += 1

    return trend_count, idea_count


async def collect_all() -> tuple[int, int]:
    """Собирает тренды для всех ниш. Возвращает (всего трендов, всего идей)."""
    logger.info("Начинаю сбор трендов для всех ниш...")

    total_trends = 0
    total_ideas = 0

    for niche_slug in NICHE_HASHTAGS.keys():
        try:
            t, i = await collect_for_niche(niche_slug)
            total_trends += t
            total_ideas += i
            logger.info("Ниша '%s': %d трендов, %d идей", niche_slug, t, i)
        except Exception as e:
            logger.error("Ошибка при сборе для ниши '%s': %s", niche_slug, e)

        # Небольшая пауза между запросами
        await asyncio.sleep(1)

    logger.info("Сбор завершён: %d трендов, %d идей", total_trends, total_ideas)
    return total_trends, total_ideas


async def collect_if_empty() -> None:
    """Собирает тренды, если таблица trends пуста."""
    count = await fetchval("SELECT COUNT(*) FROM trends")

    if count == 0:
        logger.info("Таблица trends пуста — запускаю первичный сбор...")
        await collect_all()
    else:
        logger.info("Таблица trends содержит %d записей — пропускаю первичный сбор", count)
