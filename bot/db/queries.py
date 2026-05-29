import asyncio
from bot.db.connection import get_connection


async def get_or_create_user(tg_id: int, username: str | None, first_name: str | None, last_name: str | None) -> dict:
    def _sync():
        conn = get_connection()
        cur = conn.execute(
            "INSERT INTO users (tg_id, tg_username, first_name, last_name) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT (tg_id) DO UPDATE SET "
            "  tg_username = excluded.tg_username, "
            "  first_name = excluded.first_name, "
            "  last_name = excluded.last_name "
            "RETURNING id, tg_id, tg_username, first_name, is_active",
            (tg_id, username, first_name, last_name)
        )
        row = cur.fetchone()
        conn.commit()
        return dict(row) if row else {}
    return await asyncio.to_thread(_sync)


async def get_user_niches(tg_id: int) -> list[dict]:
    def _sync():
        conn = get_connection()
        rows = conn.execute(
            "SELECT n.id, n.name, n.slug "
            "FROM user_niches un "
            "JOIN niches n ON n.id = un.niche_id "
            "JOIN users u ON u.id = un.user_id "
            "WHERE u.tg_id = ?",
            (tg_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    return await asyncio.to_thread(_sync)


async def set_user_niches(tg_id: int, niche_ids: list[int]) -> None:
    def _sync():
        conn = get_connection()
        user = conn.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,)).fetchone()
        if not user:
            return
        conn.execute("DELETE FROM user_niches WHERE user_id = ?", (user["id"],))
        for nid in niche_ids:
            conn.execute(
                "INSERT INTO user_niches (user_id, niche_id) VALUES (?, ?)",
                (user["id"], nid)
            )
        conn.commit()
    await asyncio.to_thread(_sync)


async def get_all_niches() -> list[dict]:
    def _sync():
        conn = get_connection()
        rows = conn.execute(
            "SELECT id, name, slug, description FROM niches WHERE is_active = 1 ORDER BY name"
        ).fetchall()
        return [dict(r) for r in rows]
    return await asyncio.to_thread(_sync)


async def get_trends_for_niches(niche_ids: list[int], limit: int = 5) -> list[dict]:
    if not niche_ids:
        return []
    def _sync():
        conn = get_connection()
        placeholders = ",".join("?" for _ in niche_ids)
        rows = conn.execute(
            f"SELECT t.id, t.title, t.description, t.source_url, t.trend_type, t.engagement "
            f"FROM trends t "
            f"WHERE t.niche_id IN ({placeholders}) "
            f"ORDER BY t.engagement DESC, t.collected_at DESC "
            f"LIMIT ?",
            (*niche_ids, limit)
        ).fetchall()
        return [dict(r) for r in rows]
    return await asyncio.to_thread(_sync)


async def get_daily_trend(niche_ids: list[int]) -> dict | None:
    if not niche_ids:
        return None
    def _sync():
        conn = get_connection()
        placeholders = ",".join("?" for _ in niche_ids)
        row = conn.execute(
            f"SELECT t.id, t.title, t.description, t.source_url, t.trend_type, n.name as niche_name "
            f"FROM trends t "
            f"JOIN niches n ON n.id = t.niche_id "
            f"WHERE t.niche_id IN ({placeholders}) "
            f"ORDER BY RANDOM() "
            f"LIMIT 1",
            niche_ids
        ).fetchone()
        return dict(row) if row else None
    return await asyncio.to_thread(_sync)


async def get_idea_for_niche(niche_slug: str) -> dict | None:
    def _sync():
        conn = get_connection()
        row = conn.execute(
            "SELECT i.id, i.title, i.description, i.script_preview "
            "FROM ideas i "
            "JOIN niches n ON n.id = i.niche_id "
            "WHERE n.slug = ? "
            "ORDER BY RANDOM() "
            "LIMIT 1",
            (niche_slug,)
        ).fetchone()
        return dict(row) if row else None
    return await asyncio.to_thread(_sync)
