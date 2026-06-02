"""
Периодические задачи TrendRec.

- collect_trends: сбор трендов из TikTok
- send_daily_digest: рассылка дайджеста всем пользователям
"""

import asyncio
import logging
from datetime import datetime

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import config
from bot.db.queries import get_all_users_with_niches, get_active_trends_for_niches, get_daily_trend
from bot.services.tiktok_parser import collect_all

logger = logging.getLogger(__name__)


def format_video_link(video_url: str) -> str:
    if video_url:
        return f"\u25b6\ufe0f <a href=\"{video_url}\">Смотреть пример</a>"
    return ""


def format_trend_block(t: dict, index: int = 0) -> list[str]:
    lines = []
    if index > 0:
        lines.append(f"  {index}. <b>{t['title']}</b>")
    else:
        lines.append(f"   <b>{t['title']}</b>")
    if t.get('description'):
        lines.append(f"     {t['description']}")
    video_link = format_video_link(t.get('video_url', ''))
    if video_link:
        lines.append(f"     {video_link}")
    if t.get('engagement'):
        lines.append(f"     \U0001f440 {t['engagement']:,} просмотров".replace(",", " "))
    if t.get('niche_name'):
        lines.append(f"     \U0001f4c2 {t.get('niche_name', '?')}")
    return lines


async def collect_trends() -> None:
    logger.info("=" * 50)
    logger.info("ПЛАНОВЫЙ СБОР ТРЕНДОВ [%s]", datetime.now().strftime("%Y-%m-%d %H:%M"))
    logger.info("=" * 50)
    try:
        trend_count, idea_count = await collect_all()
        logger.info("Плановый сбор завершён: %d трендов, %d идей", trend_count, idea_count)
    except Exception as e:
        logger.error("Ошибка при плановом сборе: %s", e)


async def send_daily_digest() -> None:
    logger.info("=" * 50)
    logger.info("ЗАПУСК РАССЫЛКИ ДАЙДЖЕСТА [%s]", datetime.now().strftime("%Y-%m-%d %H:%M"))
    logger.info("=" * 50)

    users = await get_all_users_with_niches()
    if not users:
        logger.info("Нет пользователей для рассылки")
        return

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    sent_count = 0
    failed_count = 0

    try:
        for user in users:
            tg_id = user["tg_id"]
            niches = user["niches"]
            first_name = user.get("first_name") or "создатель"

            if not niches:
                continue

            if not user.get("digest_enabled", True):
                continue

            niche_ids = [n["id"] for n in niches]
            niche_names = [n["name"] for n in niches]

            daily_trend = await get_daily_trend(niche_ids)
            fresh_trends = await get_active_trends_for_niches(niche_ids, hours=24, limit=5)

            lines = [f"\u2600\ufe0f <b>Доброе утро, {first_name}!</b>\n"]

            if daily_trend:
                lines.append("\U0001f525 <b>Тренд дня:</b>")
                lines.extend(format_trend_block(daily_trend))
                lines.append("")

            if fresh_trends:
                lines.append("\U0001f4c8 <b>Свежие тренды за 24ч:</b>")
                for i, t in enumerate(fresh_trends[:3], 1):
                    lines.extend(format_trend_block(t, i))
                lines.append("")

            lines.append(f"\U0001f4c2 <b>Твои ниши:</b> {', '.join(niche_names)}")
            lines.append("")
            lines.append("\U0001f4a1 <b>Что делать:</b>")
            lines.append("   /trends — все тренды")
            lines.append("   /idea — идея для видео")
            lines.append("   /niches — изменить ниши")

            message = "\n".join(lines)

            try:
                await bot.send_message(chat_id=tg_id, text=message)
                sent_count += 1
            except Exception as e:
                failed_count += 1
                logger.warning("Не удалось отправить пользователю %d: %s", tg_id, e)

            await asyncio.sleep(0.1)

    finally:
        await bot.session.close()

    logger.info("Рассылка завершена: отправлено=%d, ошибок=%d", sent_count, failed_count)
