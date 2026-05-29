import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import config
from bot.handlers import start, trends, idea
from bot.db.connection import get_connection, close
from bot.services.tiktok_parser import collect_if_empty

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

    # Init DB on startup
    get_connection()

    # Fill DB with trends & ideas if empty
    await collect_if_empty()

    logger.info("Bot starting...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        close()
        logger.info("Bot stopped gracefully")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
