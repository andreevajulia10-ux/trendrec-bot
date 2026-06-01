"""
Миграции БД. Создаёт таблицы, если их нет.
"""

import logging

from bot.db.connection import get_pool

logger = logging.getLogger(__name__)

INIT_SQL = """
-- Пользователи Telegram
CREATE TABLE IF NOT EXISTS users (
    id            BIGSERIAL PRIMARY KEY,
    tg_id         BIGINT UNIQUE NOT NULL,
    tg_username   TEXT,
    first_name    TEXT,
    last_name     TEXT,
    language      TEXT DEFAULT 'ru',
    digest_enabled BOOLEAN DEFAULT TRUE,
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Ниши / категории контента
CREATE TABLE IF NOT EXISTS niches (
    id            SERIAL PRIMARY KEY,
    name          TEXT UNIQUE NOT NULL,
    slug          TEXT UNIQUE NOT NULL,
    description   TEXT,
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Подписки пользователя на ниши
CREATE TABLE IF NOT EXISTS user_niches (
    user_id       BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    niche_id      INT NOT NULL REFERENCES niches(id) ON DELETE CASCADE,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, niche_id)
);

-- Тренды TikTok
CREATE TABLE IF NOT EXISTS trends (
    id            BIGSERIAL PRIMARY KEY,
    title         TEXT NOT NULL,
    description   TEXT,
    niche_id      INT REFERENCES niches(id),
    source_url    TEXT,
    video_url     TEXT,
    source        TEXT DEFAULT 'tiktok_creative_center',
    trend_type    TEXT DEFAULT 'hashtag',
    engagement    INT DEFAULT 0,
    collected_at  TIMESTAMPTZ DEFAULT NOW(),
    expires_at    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Примеры видео для трендов
CREATE TABLE IF NOT EXISTS trend_examples (
    id            BIGSERIAL PRIMARY KEY,
    trend_id      BIGINT NOT NULL REFERENCES trends(id) ON DELETE CASCADE,
    video_url     TEXT NOT NULL,
    video_title   TEXT DEFAULT '',
    author_name   TEXT DEFAULT '',
    views         INT DEFAULT 0,
    is_featured   INT DEFAULT 0,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Идеи для видео
CREATE TABLE IF NOT EXISTS ideas (
    id            BIGSERIAL PRIMARY KEY,
    trend_id      BIGINT REFERENCES trends(id) ON DELETE SET NULL,
    niche_id      INT REFERENCES niches(id),
    title         TEXT NOT NULL,
    description   TEXT,
    script_preview TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- История отправленных трендов пользователям
CREATE TABLE IF NOT EXISTS sent_trends (
    user_id       BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    trend_id      BIGINT NOT NULL REFERENCES trends(id) ON DELETE CASCADE,
    sent_at       TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, trend_id)
);

-- Обратная связь пользователей (лайк/дизлайк тренда)
CREATE TABLE IF NOT EXISTS user_feedback (
    id            BIGSERIAL PRIMARY KEY,
    user_id       BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    trend_id      BIGINT NOT NULL REFERENCES trends(id) ON DELETE CASCADE,
    reaction      TEXT NOT NULL CHECK (reaction IN ('like', 'dislike', 'skip')),
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, trend_id)
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_users_tg_id ON users(tg_id);
CREATE INDEX IF NOT EXISTS idx_trends_niche ON trends(niche_id);
CREATE INDEX IF NOT EXISTS idx_trends_collected ON trends(collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_ideas_niche ON ideas(niche_id);
CREATE INDEX IF NOT EXISTS idx_trend_examples_trend ON trend_examples(trend_id);
"""

SEED_NICHES_SQL = """
INSERT INTO niches (name, slug, description) VALUES
    ('Танцы',        'dance',      'Танцевальные тренды, челленджи, хореография'),
    ('Юмор',         'comedy',     'Скетчи, мемы, смешные ситуации'),
    ('Образование',  'education',  'Обучающие видео, лайфхаки, факты'),
    ('Красота',      'beauty',     'Макияж, уход, прически, трансформации'),
    ('Еда',          'food',       'Рецепты, обзоры, челленджи с едой'),
    ('Спорт',        'sport',      'Тренировки, фитнес, достижения'),
    ('Музыка',       'music',      'Каверы, песни, музыкальные челленджи'),
    ('Игры',         'gaming',     'Игровой контент, стримы, моменты'),
    ('Технологии',   'tech',       'Гаджеты, обзоры, IT-тренды'),
    ('Лайфстайл',    'lifestyle',  'Повседневная жизнь, влоги, рутина')
ON CONFLICT (name) DO NOTHING;
"""


async def run_migrations() -> None:
    """Запускает миграции — создаёт таблицы и заполняет начальные данные."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        logger.info("Запуск миграций...")

        # Создаём таблицы
        await conn.execute(INIT_SQL)
        logger.info("Таблицы созданы/проверены")

        # Заполняем ниши
        await conn.execute(SEED_NICHES_SQL)
        logger.info("Начальные ниши добавлены/проверены")

        logger.info("Миграции завершены")
