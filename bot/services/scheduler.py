"""
Планировщик периодических задач.

Использует APScheduler для запуска задач по расписанию.
"""

import asyncio
import logging
from datetime import datetime
from typing import Callable, Coroutine, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Планировщик задач с поддержкой cron-расписаний."""

    def __init__(self):
        self._scheduler = AsyncIOScheduler()
        self._tasks: dict[str, str] = {}

    def register_task(
        self,
        name: str,
        func: Callable[..., Coroutine[Any, Any, Any]],
        cron_expr: str,
        args: list | None = None,
    ) -> None:
        """Регистрирует периодическую задачу.

        Args:
            name: Уникальное имя задачи
            func: Асинхронная функция
            cron_expr: CRON-выражение (например "0 8 * * *" = каждый день в 8:00)
            args: Аргументы для функции
        """
        if name in self._tasks:
            logger.warning("Задача '%s' уже зарегистрирована", name)
            return

        trigger = CronTrigger.from_crontab(cron_expr)
        self._scheduler.add_job(
            func,
            trigger=trigger,
            args=args or [],
            id=name,
            name=name,
            misfire_grace_time=300,  # 5 минут на случай опоздания
        )
        self._tasks[name] = cron_expr
        logger.info("Задача '%s' зарегистрирована (cron: %s)", name, cron_expr)

    async def start(self) -> None:
        """Запускает планировщик."""
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("Планировщик запущен (%d задач)", len(self._tasks))
            for name, cron in self._tasks.items():
                logger.info("  - %s: %s", name, cron)

    async def stop(self) -> None:
        """Останавливает планировщик."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Планировщик остановлен")

    def get_task_info(self) -> list[dict]:
        """Возвращает информацию о зарегистрированных задачах."""
        return [
            {"name": name, "cron": cron, "next_run": str(job.next_run_time) if job.next_run_time else "N/A"}
            for name, cron in self._tasks.items()
            for job in [self._scheduler.get_job(name)]
        ]


# Единый экземпляр планировщика
scheduler = TaskScheduler()
