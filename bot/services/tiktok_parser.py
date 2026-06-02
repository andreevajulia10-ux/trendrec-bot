"""
Парсер трендов TikTok.

Два уровня сбора:
1. TikTok Creative Center — тренды по нишам
2. Fallback — статические тренды, если парсинг недоступен
"""

import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import aiohttp

from bot.db.connection import fetchrow, fetchval

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
# Level 1: TikTok Creative Center
# =============================================================================

# Единая aiohttp сессия для всех запросов (переиспользуем HTTP-соединения)
_shared_session: Optional[aiohttp.ClientSession] = None
_SESSION_LOCK = asyncio.Lock()


async def _get_shared_session() -> aiohttp.ClientSession:
    """Возвращает общую aiohttp сессию (создаёт при первом вызове)."""
    global _shared_session
    if _shared_session is None or _shared_session.closed:
        async with _SESSION_LOCK:
            # Double-check locking
            if _shared_session is None or _shared_session.closed:
                connector = aiohttp.TCPConnector(limit=5, limit_per_host=2, ttl_dns_cache=300)
                timeout = aiohttp.ClientTimeout(total=3, connect=2)
                _shared_session = aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Accept": "application/json",
                    },
                )
    return _shared_session


async def _fetch_creative_center_trends(niche_slug: str) -> list[TrendItem]:
    """Парсит TikTok Creative Center — тренды по категориям."""
    trends = []

    try:
        session = await _get_shared_session()
        url = "https://ads.tiktok.com/business/creativecenter/api/v1/trends/v2"

        params = {
            "category": niche_slug,
            "period": "7d",
            "limit": 10,
        }

        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=2)) as resp:
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
# Level 2: Fallback — статические тренды
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

        # Вставляем новый тренд (video_url не заполняем — это ссылка на хештег, а не видео)
    row = await fetchrow(
        "INSERT INTO trends (title, description, niche_id, source_url, trend_type, engagement) "
        "VALUES ($1, $2, $3, $4, $5, $6) "
        "RETURNING id",
        trend.title, trend.description, niche_id, trend.source_url, trend.trend_type, trend.engagement
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
        "1. Начни с зацепки: «Ты видел этот тренд?»\n"
        "2. Покажи свою версию за 15-30 секунд\n"
        "3. Добавь уникальный элемент\n"
        "4. Призови подписчиков повторить"
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

    # Level 1: Creative Center
    trends = await _fetch_creative_center_trends(niche_slug)

    # Level 2: Fallback (если Creative Center не дал результатов)
    is_fallback = False
    if not trends:
        trends = _get_fallback_trends(niche_slug, count=3)
        is_fallback = True
        logger.info("Fallback: %d трендов для %s", len(trends), niche_slug)

    # Сохраняем в БД
    for trend in trends:
        trend_id = await _save_trend_to_db(trend)
        if trend_id:
            trend_count += 1
            # Генерируем идею только для fallback-трендов, чтобы не засорять БД
            if is_fallback:
                await _generate_fallback_idea(trend)
                idea_count += 1

    return trend_count, idea_count


async def collect_all() -> tuple[int, int]:
    """Собирает тренды для всех ниш (параллельно). Возвращает (всего трендов, всего идей)."""
    logger.info("Начинаю сбор трендов для всех ниш (параллельно)...")

    results = await asyncio.gather(
        *(collect_for_niche(slug) for slug in NICHE_HASHTAGS.keys()),
        return_exceptions=True
    )

    total_trends = 0
    total_ideas = 0
    for slug, result in zip(NICHE_HASHTAGS.keys(), results):
        if isinstance(result, Exception):
            logger.error("Ошибка при сборе для ниши '%s': %s", slug, result)
            continue
        t, i = result
        total_trends += t
        total_ideas += i
        logger.info("Ниша '%s': %d трендов, %d идей", slug, t, i)

    logger.info("Сбор завершён: %d трендов, %d идей (за ~3с вместо 160с)", total_trends, total_ideas)
    return total_trends, total_ideas


async def collect_if_empty() -> None:
    """Собирает тренды, если таблица trends пуста."""
    count = await fetchval("SELECT COUNT(*) FROM trends")

    if count == 0:
        logger.info("Таблица trends пуста — запускаю первичный сбор...")
        await collect_all()
    else:
        logger.info("Таблица trends содержит %d записей — пропускаю первичный сбор", count)


async def close_parser_session() -> None:
    """Закрывает общую aiohttp сессию. Вызывать при shutdown бота."""
    global _shared_session
    if _shared_session and not _shared_session.closed:
        await _shared_session.close()
        logger.info("Общая aiohttp сессия закрыта")
