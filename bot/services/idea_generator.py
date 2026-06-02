"""
AI-генератор идей и сценариев для TikTok.

Использует OpenAI или YandexGPT (бесплатно) для генерации идей,
которые звучат как от живого человека, а не как от AI.

Фишки:
- Человеческий, разговорный язык
- Без шаблонных фраз ("в заключение", "в современном мире")
- С учётом реальных трендов пользователя
- Адаптация под конкретную нишу
- Поддержка YandexGPT (бесплатно через Yandex Cloud)
"""

import json
import logging
import random
import re
from dataclasses import dataclass, field
from typing import Optional

from bot.config import config

logger = logging.getLogger(__name__)


# =============================================================================
# Модели данных
# =============================================================================

@dataclass
class GeneratedIdea:
    title: str = ""
    description: str = ""
    script: str = ""
    hook: str = ""
    vibe: str = ""
    niche_slug: str = "general"


@dataclass
class GenerationRequest:
    niche_name: str
    niche_slug: str
    trends: list[str] = field(default_factory=list)
    tone: str = "casual"
    count: int = 2


# =============================================================================
# Системный промпт — самая важная часть
# =============================================================================

SYSTEM_PROMPT = """Ты — TikTok-стратег с 5-летним опытом. Твоя задача — придумывать идеи для видео.

ВАЖНО: Пиши так, как говорит живой человек. Без:
- "В современном мире", "в наше время", "сегодня особенно актуально"
- "Давайте рассмотрим", "следует отметить", "нельзя не упомянуть"
- Официальных оборотов, канцелярита, штампов
- Слов-паразитов AI: "уникальный", "инновационный", "революционный"
- Восклицательных знаков после каждого предложения
- Эмодзи в каждом абзаце

Пиши коротко, по делу, с энергией. Как будто объясняешь другу идею за чаем.

Формат ответа — JSON-массив:

```json
[
  {
    "title": "Короткий заголовок (до 8 слов)",
    "description": "О чём видео (1-2 предложения без воды)",
    "hook": "Что будет в первые 3 секунды, чтобы зритель не пролистал",
    "script": "Сценарий по шагам (3-5 пунктов, каждый — одно действие)",
    "vibe": "Настроение видео: смешное/дерзкое/уютное/энергичное/полезное"
  }
]
```"""


def _build_user_prompt(request: GenerationRequest) -> str:
    """Собирает промпт под конкретную нишу и тренды."""
    trends_text = ""
    if request.trends:
        trends_text = "\nАктуальные тренды в этой нише:\n" + "\n".join(f"- {t}" for t in request.trends)

    tone_desc = {
        "casual": "простой, разговорный стиль, как будто рассказываешь знакомому",
        "energetic": "заряженный, драйвовый, чтобы хотелось бежать снимать",
        "educational": "полезный, но без занудства — объясняешь на пальцах",
        "funny": "с юмором, самоирония, без напряга",
    }

    tone_text = tone_desc.get(request.tone, tone_desc["casual"])

    prompt = f"""Придумай {request.count} идей для TikTok в нише «{request.niche_name}».
{trends_text}

Стиль: {tone_text}

Сделай так, чтобы идеи были:
- Понятны новичку (не надо специального оборудования)
- Реализуемы за 15-30 минут съёмки
- Заходили в рекомендации (высокая удерживаемость)
- Основаны на реальном опыте, а не на теории"""

    return prompt


# =============================================================================
# Парсер ответа AI
# =============================================================================

def _parse_ideas(text: str, niche_slug: str) -> list[GeneratedIdea]:
    """Парсит JSON из ответа AI."""
    text = text.strip()

    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start:end])
            except json.JSONDecodeError:
                logger.warning("Не удалось распарсить JSON из ответа AI")
                return []
        else:
            logger.warning("В ответе AI нет JSON массива")
            return []

    if not isinstance(data, list):
        data = [data]

    ideas = []
    for item in data:
        if not isinstance(item, dict):
            continue
        ideas.append(GeneratedIdea(
            title=item.get("title", "Идея без названия"),
            description=item.get("description", ""),
            script=item.get("script", ""),
            hook=item.get("hook", ""),
            vibe=item.get("vibe", ""),
            niche_slug=niche_slug,
        ))

    return ideas


# =============================================================================
# Проверка: похоже ли на AI?
# =============================================================================

AI_PATTERNS = [
    "в современном мире", "в наше время", "сегодня особенно",
    "давайте рассмотрим", "следует отметить", "нельзя не упомянуть",
    "является важным", "представляет собой", "данный подход",
    "в контексте", "на сегодняшний день", "стоит подчеркнуть",
    "необходимо отметить", "в заключение", "подводя итог",
    "уникальный", "инновационный", "революционный",
    "оптимальный", "эффективный инструмент",
    "in today's world", "in modern world", "let's delve",
    "it's worth noting", "cutting-edge", "game-changer",
    "groundbreaking", "paradigm shift", "transformative",
]

AI_WORDS = ["revolutionary", "groundbreaking", "transformative"]


def _sounds_too_ai(text: str) -> bool:
    """Проверяет, не звучит ли текст как типичный AI."""
    text_lower = text.lower()
    phrase_matches = sum(1 for p in AI_PATTERNS if p in text_lower)
    if phrase_matches >= 2:
        return True
    words = text_lower.split()
    for ai_word in AI_WORDS:
        if ai_word in words:
            return True
    return False


def _humanize(text: str) -> str:
    """Делает текст более человечным."""
    replacements = {
        "В современном мире": "Сейчас", "В современном": "Сейчас",
        "На сегодняшний день": "Сейчас", "В наше время": "Сейчас",
        "Данный": "Этот", "Данная": "Эта", "Данное": "Это", "Данные": "Эти",
        "Представляет собой": "— это", "Является": "— это", "Являются": "— это",
        "В заключение": "Короче", "Подводя итог": "Короче говоря",
        "Следует отметить": "Кстати", "Нельзя не упомянуть": "Ещё важная штука",
        "Необходимо отметить": "Важно", "Стоит подчеркнуть": "Запомни",
        "В контексте": "В плане", "В рамках": "В",
        "Осуществлять": "Делать", "Использовать": "Юзать",
        "Уникальный": "Классный", "Инновационный": "Новый",
        "Революционный": "Прорывной", "Оптимальный": "Лучший",
        "Эффективный": "Рабочий", "Эффективный инструмент": "Рабочая штука",
    }

    result = text
    for old, new in replacements.items():
        result = result.replace(old, new)
        result = result.replace(old.lower(), new.lower())

    for word, replacement in [("revolutionary", "fresh"), ("groundbreaking", "new"), ("transformative", "powerful")]:
        result = re.sub(r'\b' + word + r'\b', replacement, result, flags=re.IGNORECASE)

    return result


def _validate_and_fix(idea: GeneratedIdea) -> GeneratedIdea:
    """Проверяет идею на 'AI-ность' и чистит её."""
    if _sounds_too_ai(idea.title):
        idea.title = _humanize(idea.title)
    if _sounds_too_ai(idea.description):
        idea.description = _humanize(idea.description)
    if _sounds_too_ai(idea.script):
        idea.script = _humanize(idea.script)
    if _sounds_too_ai(idea.hook):
        idea.hook = _humanize(idea.hook)
    return idea


# =============================================================================
# YandexGPT клиент
# =============================================================================

class YandexGPTClient:
    """Клиент для работы с YandexGPT через Yandex Cloud API."""

    API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    def __init__(self, api_key: str, folder_id: str):
        self.api_key = api_key
        self.folder_id = folder_id
        self.model_uri = f"gpt://{folder_id}/yandexgpt-lite"

    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 1.2) -> str:
        import aiohttp

        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "modelUri": self.model_uri,
            "completionOptions": {
                "stream": False,
                "temperature": temperature,
                "maxTokens": 2000,
            },
            "messages": [
                {"role": "system", "text": system_prompt},
                {"role": "user", "text": user_prompt},
            ],
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(self.API_URL, json=payload, timeout=30) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error("YandexGPT error %s: %s", resp.status, text)
                    return ""
                data = await resp.json()
                # YandexGPT возвращает ответ в альтернативах
                alternatives = data.get("result", {}).get("alternatives", [])
                if alternatives:
                    return alternatives[0].get("message", {}).get("text", "")
                return ""


# =============================================================================
# Основной генератор
# =============================================================================

class IdeaGenerator:
    """Генератор идей для TikTok через AI (OpenAI или YandexGPT)."""

    def __init__(self):
        self.openai_client = None
        self.yandex_client = None
        self._provider = None

    def _init_openai(self):
        """Инициализирует асинхронный OpenAI клиент."""
        if not config.openai_api_key:
            return False
        try:
            from openai import AsyncOpenAI
            self.openai_client = AsyncOpenAI(api_key=config.openai_api_key)
            logger.info("Асинхронный OpenAI клиент инициализирован")
            return True
        except ImportError:
            logger.warning("Библиотека openai не установлена")
        except Exception as e:
            logger.warning("Ошибка инициализации OpenAI: %s", e)
        return False

    def _init_yandex(self):
        """Инициализирует YandexGPT клиент."""
        if not config.yandexgpt_api_key or not config.yandexgpt_folder_id:
            return False
        try:
            self.yandex_client = YandexGPTClient(config.yandexgpt_api_key, config.yandexgpt_folder_id)
            logger.info("YandexGPT клиент инициализирован")
            return True
        except Exception as e:
            logger.warning("Ошибка инициализации YandexGPT: %s", e)
        return False

    def _init(self):
        """Инициализирует нужного провайдера."""
        if self._provider is not None:
            return

        provider = config.ai_provider or ""

        if provider == "yandexgpt":
            if self._init_yandex():
                self._provider = "yandexgpt"
                return
        elif provider == "openai":
            if self._init_openai():
                self._provider = "openai"
                return
        else:
            # Автовыбор: пробуем OpenAI, потом YandexGPT
            if self._init_openai():
                self._provider = "openai"
                return
            if self._init_yandex():
                self._provider = "yandexgpt"
                return

        self._provider = "none"

    @property
    def available(self) -> bool:
        """Доступна ли AI-генерация."""
        self._init()
        return self._provider in ("openai", "yandexgpt")

    async def generate(self, request: GenerationRequest) -> list[GeneratedIdea]:
        """Генерирует идеи через доступного AI-провайдера."""
        self._init()

        if not self.available:
            logger.info("AI недоступен — возвращаю пустой список")
            return []

        user_prompt = _build_user_prompt(request)

        try:
            if self._provider == "openai":
                raw = await self._generate_openai(user_prompt)
            elif self._provider == "yandexgpt":
                raw = await self._generate_yandex(user_prompt)
            else:
                return []

            if not raw:
                return []

            ideas = _parse_ideas(raw, request.niche_slug)
            ideas = [_validate_and_fix(idea) for idea in ideas]
            logger.info("AI сгенерировал %d идей для ниши '%s'", len(ideas), request.niche_name)
            return ideas

        except Exception as e:
            logger.error("Ошибка AI-генерации: %s", e)
            return []

    async def _generate_openai(self, user_prompt: str) -> str:
        """Генерирует через OpenAI (асинхронно)."""
        if not self.openai_client:
            return ""

        response = await self.openai_client.chat.completions.create(
            model=config.openai_model or "gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=1.2,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or ""

    async def _generate_yandex(self, user_prompt: str) -> str:
        """Генерирует через YandexGPT."""
        if not self.yandex_client:
            return ""
        return await self.yandex_client.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=1.2,
        )

    async def generate_for_niche(self, niche_name: str, niche_slug: str,
                                  trends: Optional[list[str]] = None, count: int = 2) -> list[GeneratedIdea]:
        """Упрощённый вызов генерации для ниши."""
        request = GenerationRequest(
            niche_name=niche_name, niche_slug=niche_slug,
            trends=trends or [], count=count,
        )
        return await self.generate(request)


# =============================================================================
# Форматирование для Telegram
# =============================================================================

def format_ideas_for_tg(ideas: list[GeneratedIdea], niche_name: str, username: str = "создатель") -> str:
    """Форматирует сгенерированные идеи в сообщение для Telegram."""
    if not ideas:
        return ""
    lines = [f"🎬 <b>Идеи для видео — {niche_name}</b>", ""]
    for i, idea in enumerate(ideas, 1):
        lines.append(f"<b>{i}. {idea.title}</b>")
        if idea.description:
            lines.append(f"   {idea.description}")
        if idea.hook:
            lines.append(f"   🎯 <b>Зацепка:</b> {idea.hook}")
        if idea.vibe:
            lines.append(f"   🎭 <b>Настроение:</b> {idea.vibe}")
        if idea.script:
            lines.append(f"   📝 <b>Сценарий:</b>")
            for step in idea.script.split("\n"):
                step = step.strip()
                if step and not step.startswith("```"):
                    lines.append(f"     {step}")
        lines.append("")
    lines.append("💡 /idea — ещё идеи")
    lines.append("📋 /trends — тренды дня")
    return "\n".join(lines)


# =============================================================================
# Singleton
# =============================================================================

idea_generator = IdeaGenerator()
