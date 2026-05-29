import asyncpg
import os
import logging
from bot.config import config

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def connect() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        # Railway provides DATABASE_URL automatically for attached PostgreSQL
        dsn = os.environ.get("DATABASE_URL") or config.database_url
        if not dsn:
            raise ValueError(
                "DATABASE_URL not set! "
                "Make sure PostgreSQL is linked to this service in Railway."
            )
        logger.info("Connecting to database...")
        _pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=5)
        await _init_db(_pool)
        logger.info("Database connected")
    return _pool


async def _init_db(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            BIGSERIAL PRIMARY KEY,
                tg_id         BIGINT UNIQUE NOT NULL,
                tg_username   TEXT,
                first_name    TEXT,
                last_name     TEXT,
                language      TEXT DEFAULT 'ru',
                is_active     BOOLEAN DEFAULT TRUE,
                created_at    TIMESTAMPTZ DEFAULT NOW(),
                updated_at    TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS niches (
                id            SERIAL PRIMARY KEY,
                name          TEXT UNIQUE NOT NULL,
                slug          TEXT UNIQUE NOT NULL,
                description   TEXT,
                is_active     BOOLEAN DEFAULT TRUE,
                created_at    TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS user_niches (
                user_id       BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                niche_id      INT NOT NULL REFERENCES niches(id) ON DELETE CASCADE,
                created_at    TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (user_id, niche_id)
            );
            CREATE TABLE IF NOT EXISTS trends (
                id            BIGSERIAL PRIMARY KEY,
                title         TEXT NOT NULL,
                description   TEXT,
                niche_id      INT REFERENCES niches(id),
                source_url    TEXT,
                source        TEXT DEFAULT 'tiktok_creative_center',
                trend_type    TEXT DEFAULT 'hashtag',
                engagement    INT DEFAULT 0,
                collected_at  TIMESTAMPTZ DEFAULT NOW(),
                expires_at    TIMESTAMPTZ,
                created_at    TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS ideas (
                id            BIGSERIAL PRIMARY KEY,
                trend_id      BIGINT REFERENCES trends(id) ON DELETE SET NULL,
                niche_id      INT REFERENCES niches(id),
                title         TEXT NOT NULL,
                description   TEXT,
                script_preview TEXT,
                created_at    TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS sent_trends (
                user_id       BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                trend_id      BIGINT NOT NULL REFERENCES trends(id) ON DELETE CASCADE,
                sent_at       TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (user_id, trend_id)
            );
        """)

        count = await conn.fetchval("SELECT COUNT(*) FROM niches")
        if count == 0:
            await conn.executemany(
                "INSERT INTO niches (name, slug, description) VALUES (, , )",
                [
                    ("Танцы", "dance", "Танцевальные тренды, челленджи, хореография"),
                    ("Юмор", "comedy", "Скетчи, мемы, смешные ситуации"),
                    ("Образование", "education", "Обучающие видео, лайфхаки, факты"),
                    ("Красота", "beauty", "Макияж, уход, прически, трансформации"),
                    ("Еда", "food", "Рецепты, обзоры, челленджи с едой"),
                    ("Спорт", "sport", "Тренировки, фитнес, достижения"),
                    ("Музыка", "music", "Каверы, песни, музыкальные челленджи"),
                    ("Игры", "gaming", "Игровой контент, стримы, моменты"),
                    ("Технологии", "tech", "Гаджеты, обзоры, IT-тренды"),
                    ("Лайфстайл", "lifestyle", "Повседневная жизнь, влоги, рутина"),
                ]
            )
            logger.info("Default niches inserted")


async def close() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database connection closed")
