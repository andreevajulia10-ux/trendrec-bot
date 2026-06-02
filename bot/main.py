"""
Точка входа TrendRec Bot.
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession
from bot.config import config
from bot.handlers import start, trends, idea, digest, settings, stats
from bot.db.connection import close_pool, init_db
from bot.services.tiktok_parser import collect_if_empty, close_parser_session
from bot.services.scheduler import scheduler
from bot.services.tasks import collect_trends, send_daily_digest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Флаг: идёт ли первичный сбор трендов
_initial_collect_done = False


async def background_collect() -> None:
    """Фоновый сбор трендов после старта polling."""
    global _initial_collect_done
    try:
        await collect_if_empty()
        # Ждём 10 секунд, чтобы бот точно стартанул, потом собираем свежие тренды
        await asyncio.sleep(10)
        if not _initial_collect_done:
            _initial_collect_done = True
            logger.info("Запуск фонового сбора трендов...")
            await collect_trends()
    except Exception as e:
        logger.error("Ошибка фонового сбора трендов: %s", e)


async def on_startup(bot: Bot) -> None:
    """Вызывается при старте бота (после запуска polling)."""
    logger.info("=" * 50)
    logger.info("TRENDREC BOT ЗАПУЩЕН")
    logger.info("=" * 50)

    # Инициализация БД
    await init_db()
    logger.info("База данных инициализирована")

    # Регистрируем задачи планировщика
    scheduler.register_task(
        name="collect_trends",
        func=collect_trends,
        cron_expr="0 8 * * *",
    )

    digest_time = config.daily_digest_time
    try:
        hour, minute = digest_time.split(":")
        scheduler.register_task(
            name="send_daily_digest",
            func=send_daily_digest,
            cron_expr=f"{minute} {hour} * * *",
        )
    except Exception as e:
        logger.warning("Неверный формат времени дайджеста '%s': %s", digest_time, e)

    await scheduler.start()
    logger.info("Планировщик запущен")

    # Запускаем фоновый сбор трендов (не блокирует старт бота)
    asyncio.create_task(background_collect())

    logger.info("Бот готов к работе! Ожидаю команды...")


async def on_shutdown() -> None:
    """Вызывается при остановке бота."""
    logger.info("Остановка бота...")
    try:
        await scheduler.stop()
    except Exception:
        pass
    try:
        await close_parser_session()
    except Exception:
        pass
    try:
        await close_pool()
    except Exception:
        pass
    logger.info("Бот остановлен")


async def main() -> None:
    """Основная функция запуска бота."""
    # Создаём сессию с прокси, если указан и он валидный
    proxy = config.telegram_proxy
    if proxy and (proxy.startswith("http") or proxy.startswith("socks")):
        session = AiohttpSession(proxy=proxy)
        logger.info("Использую прокси: %s", proxy.split("@")[-1] if "@" in proxy else proxy)
    else:
        session = None
        if proxy:
            logger.warning("Прокси '%s' невалидный (нужен http:// или socks5://) - работаю без прокси", proxy)
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session,
    )

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Подключаем хендлеры
    dp.include_router(start.router)
    dp.include_router(trends.router)
    dp.include_router(idea.router)
    dp.include_router(digest.router)
    dp.include_router(settings.router)
    dp.include_router(stats.router)

    # Регистрируем startup/shutdown
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("Запуск polling...")
    try:
        # Проверяем, что бот может подключиться к Telegram
        bot_me = await bot.get_me()
        logger.info("Бот @%s успешно подключился к Telegram", bot_me.username)
        
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except aiogram.exceptions.TelegramNetworkError as e:
        logger.error("ОШИБКА: Не удалось подключиться к Telegram API! Прокси проблема или блокировка: %s", e, exc_info=True)
        logger.error("Проверьте TELEGRAM_PROXY или отключите его (TELEGRAM_PROXY=)")
    except Exception as e:
        logger.error("Критическая ошибка при работе бота: %s", e, exc_info=True)
    finally:
        try:
            await on_shutdown()
        except Exception:
            pass
        try:
            await bot.session.close()
        except Exception:
            pass
        logger.info("Бот завершил работу")


if __name__ == "__main__":
    # На Windows используем SelectorEventLoop вместо ProactorEventLoop
    # чтобы aiohttp не падал с WinError 121
    import platform
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error("Фатальная ошибка: %s", e, exc_info=True)

