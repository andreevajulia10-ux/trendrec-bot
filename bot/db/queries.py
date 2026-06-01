"""
Асинхронные запросы к БД (asyncpg).
"""

import asyncpg
from bot.db.connection import fetch, fetchrow, fetchval, execute, get_pool


async def get_trend_examples(trend_id: int, limit: int = 3) -> list[dict]:
    rows = await fetch(
        "SELECT id, video_url, video_title, author_name, views "
        "FROM trend_examples "
        "WHERE trend_id = $1 "
        "ORDER BY is_featured DESC, views DESC "
        "LIMIT $2",
        trend_id, limit
    )
    return [dict(r) for r in rows]


async def save_trend_example(trend_id: int, video_url: str, video_title: str = "",
                             author_name: str = "", views: int = 0, is_featured: int = 0) -> int:
    row = await fetchrow(
        "INSERT INTO trend_examples (trend_id, video_url, video_title, author_name, views, is_featured) "
        "VALUES ($1, $2, $3, $4, $5, $6) "
        "RETURNING id",
        trend_id, video_url, video_title, author_name, views, is_featured
    )
    return row["id"] if row else 0


async def get_or_create_user(tg_id: int, username: str | None,
                              first_name: str | None, last_name: str | None) -> dict:
    row = await fetchrow(
        "INSERT INTO users (tg_id, tg_username, first_name, last_name) "
        "VALUES ($1, $2, $3, $4) "
        "ON CONFLICT (tg_id) DO UPDATE SET "
        "  tg_username = EXCLUDED.tg_username, "
        "  first_name = EXCLUDED.first_name, "
        "  last_name = EXCLUDED.last_name "
        "RETURNING id, tg_id, tg_username, first_name, is_active",
        tg_id, username, first_name, last_name
    )
    return dict(row) if row else {}


async def get_user_niches(tg_id: int) -> list[dict]:
    rows = await fetch(
        "SELECT n.id, n.name, n.slug "
        "FROM user_niches un "
        "JOIN niches n ON n.id = un.niche_id "
        "JOIN users u ON u.id = un.user_id "
        "WHERE u.tg_id = $1",
        tg_id
    )
    return [dict(r) for r in rows]


async def set_user_niches(tg_id: int, niche_ids: list[int]) -> None:
    user = await fetchrow("SELECT id FROM users WHERE tg_id = $1", tg_id)
    if not user:
        return
    async with get_pool().acquire() as conn:
        await conn.execute("DELETE FROM user_niches WHERE user_id = $1", user["id"])
        for nid in niche_ids:
            await conn.execute(
                "INSERT INTO user_niches (user_id, niche_id) VALUES ($1, $2)",
                user["id"], nid
            )


async def get_all_niches() -> list[dict]:
    rows = await fetch(
        "SELECT id, name, slug, description FROM niches WHERE is_active = TRUE ORDER BY name"
    )
    return [dict(r) for r in rows]


async def get_trends_for_niches(niche_ids: list[int], limit: int = 5) -> list[dict]:
    if not niche_ids:
        return []
    placeholders = ",".join(f"${i+1}" for i in range(len(niche_ids)))
    limit_ph = f"${len(niche_ids)+1}"
    query = (
        f"SELECT t.id, t.title, t.description, t.source_url, t.video_url, "
        f"       t.trend_type, t.engagement "
        f"FROM trends t "
        f"WHERE t.niche_id IN ({placeholders}) "
        f"ORDER BY t.engagement DESC, t.collected_at DESC "
        f"LIMIT {limit_ph}"
    )
    rows = await fetch(query, *niche_ids, limit)
    return [dict(r) for r in rows]


async def get_daily_trend(niche_ids: list[int]) -> dict | None:
    if not niche_ids:
        return None
    placeholders = ",".join(f"${i+1}" for i in range(len(niche_ids)))
    row = await fetchrow(
        f"SELECT t.id, t.title, t.description, t.source_url, t.video_url, "
        f"       t.trend_type, n.name as niche_name "
        f"FROM trends t "
        f"JOIN niches n ON n.id = t.niche_id "
        f"WHERE t.niche_id IN ({placeholders}) "
        f"ORDER BY RANDOM() "
        f"LIMIT 1",
        *niche_ids
    )
    return dict(row) if row else None


async def get_idea_for_niche(niche_slug: str) -> dict | None:
    row = await fetchrow(
        "SELECT i.id, i.title, i.description, i.script_preview "
        "FROM ideas i "
        "JOIN niches n ON n.id = i.niche_id "
        "WHERE n.slug = $1 "
        "ORDER BY RANDOM() "
        "LIMIT 1",
        niche_slug
    )
    return dict(row) if row else None


async def get_digest_enabled(tg_id: int) -> bool:
    val = await fetchval(
        "SELECT digest_enabled FROM users WHERE tg_id = $1",
        tg_id
    )
    return bool(val) if val is not None else True


async def set_digest_enabled(tg_id: int, enabled: bool) -> None:
    await execute(
        "UPDATE users SET digest_enabled = $1, updated_at = NOW() WHERE tg_id = $2",
        enabled, tg_id
    )


async def get_all_users_with_niches() -> list[dict]:
    rows = await fetch(
        "SELECT u.id, u.tg_id, u.tg_username, u.first_name, u.digest_enabled "
        "FROM users u "
        "WHERE u.is_active = TRUE"
    )
    result = []
    for user in rows:
        niches = await fetch(
            "SELECT n.id, n.name, n.slug "
            "FROM user_niches un "
            "JOIN niches n ON n.id = un.niche_id "
            "WHERE un.user_id = $1",
            user["id"]
        )
        result.append({
            **dict(user),
            "niches": [dict(n) for n in niches],
        })
    return result


async def get_active_trends_for_niches(niche_ids: list[int], hours: int = 24, limit: int = 3) -> list[dict]:
    if not niche_ids:
        return []
    placeholders = ",".join(f"${i+1}" for i in range(len(niche_ids)))
    hours_ph = f"${len(niche_ids)+1}"
    limit_ph = f"${len(niche_ids)+2}"
    query = (
        f"SELECT t.id, t.title, t.description, t.source_url, t.video_url, "
        f"       t.trend_type, t.engagement, n.name as niche_name "
        f"FROM trends t "
        f"JOIN niches n ON n.id = t.niche_id "
        f"WHERE t.niche_id IN ({placeholders}) "
        f"  AND t.collected_at >= NOW() - make_interval(hours => {hours_ph}) "
        f"ORDER BY t.engagement DESC "
        f"LIMIT {limit_ph}"
    )
    rows = await fetch(query, *niche_ids, hours, limit)
    return [dict(r) for r in rows]
