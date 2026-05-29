from bot.db.connection import connect


async def get_or_create_user(tg_id: int, username: str | None, first_name: str | None, last_name: str | None) -> dict:
    pool = await connect()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO users (tg_id, tg_username, first_name, last_name) "
            "VALUES (, , , ) "
            "ON CONFLICT (tg_id) DO UPDATE SET "
            "  tg_username = EXCLUDED.tg_username, "
            "  first_name = EXCLUDED.first_name, "
            "  last_name = EXCLUDED.last_name "
            "RETURNING id, tg_id, tg_username, first_name, is_active",
            tg_id, username, first_name, last_name
        )
        return dict(row) if row else {}


async def get_user_niches(tg_id: int) -> list[dict]:
    pool = await connect()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT n.id, n.name, n.slug "
            "FROM user_niches un "
            "JOIN niches n ON n.id = un.niche_id "
            "JOIN users u ON u.id = un.user_id "
            "WHERE u.tg_id = ",
            tg_id
        )
        return [dict(r) for r in rows]


async def set_user_niches(tg_id: int, niche_ids: list[int]) -> None:
    pool = await connect()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT id FROM users WHERE tg_id = ", tg_id)
        if not user:
            return
        await conn.execute("DELETE FROM user_niches WHERE user_id = ", user["id"])
        for nid in niche_ids:
            await conn.execute(
                "INSERT INTO user_niches (user_id, niche_id) VALUES (, ) ON CONFLICT DO NOTHING",
                user["id"], nid
            )


async def get_all_niches() -> list[dict]:
    pool = await connect()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, name, slug, description FROM niches WHERE is_active = TRUE ORDER BY name"
        )
        return [dict(r) for r in rows]


async def get_trends_for_niches(niche_ids: list[int], limit: int = 5) -> list[dict]:
    if not niche_ids:
        return []
    pool = await connect()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT t.id, t.title, t.description, t.source_url, t.trend_type, t.engagement "
            "FROM trends t "
            "WHERE t.niche_id = ANY(::int[]) "
            "ORDER BY t.engagement DESC, t.collected_at DESC "
            "LIMIT ",
            niche_ids, limit
        )
        return [dict(r) for r in rows]


async def get_daily_trend(niche_ids: list[int]) -> dict | None:
    if not niche_ids:
        return None
    pool = await connect()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT t.id, t.title, t.description, t.source_url, t.trend_type, n.name as niche_name "
            "FROM trends t "
            "JOIN niches n ON n.id = t.niche_id "
            "WHERE t.niche_id = ANY(::int[]) "
            "ORDER BY RANDOM() "
            "LIMIT 1",
            niche_ids
        )
        return dict(row) if row else None


async def get_idea_for_niche(niche_slug: str) -> dict | None:
    pool = await connect()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT i.id, i.title, i.description, i.script_preview "
            "FROM ideas i "
            "JOIN niches n ON n.id = i.niche_id "
            "WHERE n.slug =  "
            "ORDER BY RANDOM() "
            "LIMIT 1",
            niche_slug
        )
        return dict(row) if row else None
