import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import config
from bot.handlers import start, trends, idea, digest, settings, stats
from bot.db.connection import get_pool, close_pool, init_db
from bot.services.tiktok_parser import collect_if_empty
from bot.services.scheduler import scheduler
from bot.services.tasks import collect_trends, send_daily_digest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def on_startup() -> None:
    logger.info("=" * 50)
    logger.info("ЗАПУСК TRENDREC BOT")
    logger.info("=" * 50)

    # Инициализация БД: создаём пул + таблицы
    await init_db()
    logger.info("База данных инициализирована")
    await collect_if_empty()

    scheduler.register_task(
        name="collect_trends",
        func=collect_trends,
        cron_expr="0 8 * * *",
    )

    digest_time = config.daily_digest_time
    scheduler.register_task(
        name="send_daily_digest",
        func=send_daily_digest,
        cron_expr=f"{digest_time.split(':')[1]} {digest_time.split(':')[0]} * * *",
    )

    logger.info("Первичный сбор трендов при запуске...")
    await collect_trends()

    await scheduler.start()
    logger.info("Инициализация завершена. Бот готов к работе!")


async def on_shutdown() -> None:
    logger.info("Остановка бота...")
    await scheduler.stop()
    await close_pool()
    logger.info("Бот остановлен")


async def main() -> None:
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.include_router(start.router)
    dp.include_router(trends.router)
    dp.include_router(idea.router)
    dp.include_router(digest.router)
    dp.include_router(settings.router)
    dp.include_router(stats.router)

    await on_startup()

    logger.info("Bot starting polling...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await on_shutdown()
        await bot.session.close()
        logger.info("Bot stopped gracefully")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

