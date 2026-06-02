"""
Подключение к PostgreSQL через asyncpg.

DATABASE_URL берётся из конфига (переменная окружения).
Формат: postgresql+asyncpg://user:password@host:5432/dbname
"""

import logging
from typing import Optional

import asyncpg

from bot.config import config

logger = logging.getLogger(__name__)

# Глобальный пул соединений
_pool: Optional[asyncpg.Pool] = None


def _clean_dsn(raw: str) -> str:
    """Приводит DATABASE_URL к формату, понятному asyncpg.
    Убирает протокол +asyncpg, если есть.
    """
    return raw.replace("+asyncpg", "").replace("postgresql://", "postgresql://")


async def get_pool() -> asyncpg.Pool:
    """Возвращает пул подключений (создаёт, если ещё не создан)."""
    global _pool
    if _pool is None:
        dsn = _clean_dsn(config.database_url)
        logger.info("Создаю пул подключений к PostgreSQL...")
        _pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=2,
            max_size=20,          # Увеличено с 10 до 20
            max_inactive_connection_lifetime=60.0,  # Закрываем неактивные через 60с
            command_timeout=10,   # Уменьшено с 30 до 10 секунд
            timeout=10,           # Таймаут получения соединения из пула
        )
        logger.info("Пул подключений создан (max_size=20, timeout=10s)")
    return _pool


async def close_pool() -> None:
    """Закрывает пул подключений."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Пул подключений закрыт")


async def execute(sql: str, *args) -> str:
    """Выполняет SQL-запрос без возврата строк (INSERT/UPDATE/DELETE)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.execute(sql, *args)


async def fetch(sql: str, *args) -> list[asyncpg.Record]:
    """Выполняет SELECT и возвращает список записей."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(sql, *args)


async def fetchrow(sql: str, *args) -> Optional[asyncpg.Record]:
    """Выполняет SELECT и возвращает одну запись или None."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(sql, *args)


async def fetchval(sql: str, *args) -> any:
    """Выполняет SELECT и возвращает одно значение."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(sql, *args)


async def init_db() -> None:
    """Создаёт таблицы, если их нет."""
    from bot.db.migrations import run_migrations
    await run_migrations()
