import random

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.db.queries import get_user_niches, get_idea_for_niche

router = Router()

IDEA_TEMPLATES = [
    "Попробуй снять {title}. {description}",
    "Идея для тебя: {title}. {description}",
    "Вот что сейчас залетает: {title}. {description}",
]


@router.message(Command("idea"))
async def cmd_idea(message: Message) -> None:
    niches = get_user_niches(message.from_user.id)
    if not niches:
        await message.answer(
            "Сначала выбери темы через /start\n"
            "Или настрой их заново: /niches"
        )
        return

    niche = random.choice(niches)
    idea = get_idea_for_niche(niche["slug"])

    if idea:
        template = random.choice(IDEA_TEMPLATES)
        text = template.format(
            title=idea["title"],
            description=idea["description"] or ""
        )
        if idea.get("script_preview"):
            text += f"\n\n\U0001f3ac Сценарий: {idea['script_preview']}"
    else:
        text = (
            f"\U0001f4a1 По нихе <b>{niche['name']}</b> пока нет готовых идей.\n"
            "Но вот совет: зайди в TikTok, найди 3 популярных видео в этой нише "
            "и сними свою версию самого просматриваемого!"
        )

    await message.answer(text)
