import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "trendrec.db")

# Глобальное соединение — один раз создаётся, живёт всё время
_conn: sqlite3.Connection | None = None


def get_connection() -> sqlite3.Connection:
    """Get the global SQLite connection (no thread-local)."""
    global _conn
    if _conn is None:
        logger.info("Connecting to SQLite: %s", DB_PATH)
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA foreign_keys=ON")
        _init_db(_conn)
    return _conn


# Для queries.py — синоним
get_conn_sync = get_connection


def _init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id         INTEGER UNIQUE NOT NULL,
            tg_username   TEXT,
            first_name    TEXT,
            last_name     TEXT,
            language      TEXT DEFAULT 'ru',
            is_active     INTEGER DEFAULT 1,
            created_at    TEXT DEFAULT (datetime('now')),
            updated_at    TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS niches (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT UNIQUE NOT NULL,
            slug          TEXT UNIQUE NOT NULL,
            description   TEXT,
            is_active     INTEGER DEFAULT 1,
            created_at    TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS user_niches (
            user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            niche_id      INTEGER NOT NULL REFERENCES niches(id) ON DELETE CASCADE,
            created_at    TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (user_id, niche_id)
        );
        CREATE TABLE IF NOT EXISTS trends (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            title         TEXT NOT NULL,
            description   TEXT,
            niche_id      INTEGER REFERENCES niches(id),
            source_url    TEXT,
            source        TEXT DEFAULT 'tiktok_creative_center',
            trend_type    TEXT DEFAULT 'hashtag',
            engagement    INTEGER DEFAULT 0,
            collected_at  TEXT DEFAULT (datetime('now')),
            expires_at    TEXT,
            created_at    TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS ideas (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            trend_id      INTEGER REFERENCES trends(id) ON DELETE SET NULL,
            niche_id      INTEGER REFERENCES niches(id),
            title         TEXT NOT NULL,
            description   TEXT,
            script_preview TEXT,
            created_at    TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS sent_trends (
            user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            trend_id      INTEGER NOT NULL REFERENCES trends(id) ON DELETE CASCADE,
            sent_at       TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (user_id, trend_id)
        );
    """)
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM niches").fetchone()[0]
    if count == 0:
        default_niches = [
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
        conn.executemany(
            "INSERT INTO niches (name, slug, description) VALUES (?, ?, ?)",
            default_niches
        )
        conn.commit()
        logger.info("Default niches inserted")


def close() -> None:
    """Close the global connection."""
    global _conn
    if _conn:
        _conn.close()
        _conn = None
        logger.info("Database connection closed")
