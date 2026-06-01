import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Config(BaseSettings):
    bot_token: str = os.getenv("BOT_TOKEN", "")
    
    # База данных
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/trendrec")

    # OpenAI для генерации идей
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    # YandexGPT (альтернатива OpenAI, бесплатно)
    yandexgpt_api_key: str = os.getenv("YANDEXGPT_API_KEY", "")
    yandexgpt_folder_id: str = os.getenv("YANDEX_FOLDER_ID", "")
    
    # Какой AI использовать: "openai", "yandexgpt", или "" (только статика)
    ai_provider: str = os.getenv("AI_PROVIDER", "").lower()
    
    # Настройки AI
    ai_fallback_to_static: bool = os.getenv("AI_FALLBACK_TO_STATIC", "true").lower() in ("true", "1", "yes")
    
    # Настройки дайджеста
    daily_digest_time: str = os.getenv("DAILY_DIGEST_TIME", "10:00")

    model_config = {"env_file": ".env", "extra": "ignore"}


config = Config()

