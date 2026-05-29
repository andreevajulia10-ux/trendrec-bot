import os
from pydantic_settings import BaseSettings
from pydantic import Field


class Config(BaseSettings):
    bot_token: str = Field(alias='BOT_TOKEN')
    admin_ids: str = Field(default='', alias='ADMIN_IDS')
    daily_digest_time: str = Field(default='10:00', alias='DAILY_DIGEST_TIME')

    # Railway provides DATABASE_URL
    database_url: str = Field(default='', alias='DATABASE_URL')

    @property
    def admin_list(self) -> list[int]:
        if not self.admin_ids:
            return []
        return [int(x.strip()) for x in self.admin_ids.split(",") if x.strip()]

    model_config = {'env_file': '.env', 'env_file_encoding': 'utf-8'}


config = Config()  # type: ignore
