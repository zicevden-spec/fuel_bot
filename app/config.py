from pydantic_settings import BaseSettings
from pydantic import SecretStr


class Settings(BaseSettings):
    BOT_TOKEN: SecretStr
    ADMIN_IDS: list[int]
    DATABASE_URL: str
    REDIS_URL: str
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = ""utf-8"


def get_settings() -> Settings:
    return Settings()
