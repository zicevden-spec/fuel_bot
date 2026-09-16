from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, field_validator
from typing import Optional
import os


class Settings(BaseSettings):
    BOT_TOKEN: SecretStr
    DATABASE_URL: str = "sqlite+aiosqlite:///fuel_bot.db"
    REDIS_URL: Optional[str] = None
    DEBUG: bool = False
    PROXY_URL: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

    @property
    def ADMIN_IDS(self) -> list[int]:
        admin_ids_str = os.getenv('ADMIN_IDS', '')
        if not admin_ids_str:
            return []
        try:
            return [int(x.strip()) for x in admin_ids_str.split(',') if x.strip()]
        except ValueError:
            return []


def get_settings() -> Settings:
    return Settings()
