from functools import cache
from typing import Literal

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

from .common import ENV_FILE_PATH
from .postgres import PostgresSettings
from .rabbit_mq import RabbitMQSettings

ApplicationEnvironment = Literal["development", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_TITLE: str = "Асинхронный сервис управления задачами"
    APP_VERSION: str = "0.1.0"
    APP_ENV: ApplicationEnvironment = "development"
    DEBUG: bool = APP_ENV != "production"
    LOG_LEVEL: str = "INFO"

    API_PREFIX: str = "/api"
    API_VERSION_PREFIX: str = "/v1"
    ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1"]

    CORS_ORIGINS: list[AnyHttpUrl] = []

    postgres: PostgresSettings = PostgresSettings()
    rabbit_mq: RabbitMQSettings = RabbitMQSettings()


@cache
def get_settings() -> Settings:
    return Settings()
