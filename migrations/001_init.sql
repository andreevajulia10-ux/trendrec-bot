-- 001_init.sql
-- TrendRec Telegram Bot — начальная схема БД

-- Пользователи Telegram
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

-- Ниши / категории контента
CREATE TABLE IF NOT EXISTS niches (
    id            SERIAL PRIMARY KEY,
    name          TEXT UNIQUE NOT NULL,        -- например: «танцы», «юмор», «образование»
    slug          TEXT UNIQUE NOT NULL,         -- например: dance, comedy, education
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
    source        TEXT DEFAULT 'tiktok_creative_center',  -- откуда собрали
    trend_type    TEXT DEFAULT 'hashtag',                 -- hashtag, sound, effect, style, video
    engagement    INT DEFAULT 0,                          -- примерная активность
    collected_at  TIMESTAMPTZ DEFAULT NOW(),
    expires_at    TIMESTAMPTZ,                            -- когда тренд «устареет»
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Идеи для видео (сгенерированные или вручную)
CREATE TABLE IF NOT EXISTS ideas (
    id            BIGSERIAL PRIMARY KEY,
    trend_id      BIGINT REFERENCES trends(id) ON DELETE SET NULL,
    niche_id      INT REFERENCES niches(id),
    title         TEXT NOT NULL,
    description   TEXT,
    script_preview TEXT,                                  -- короткий сценарий
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

-- История отправленных трендов пользователям (чтоб не дублировать)
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

-- Начальные ниши
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

