from functools import cache
from typing import Literal, Self

from pydantic import AnyHttpUrl, model_validator
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
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    API_PREFIX: str = "/api"
    API_VERSION_PREFIX: str = "/v1"
    ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1"]

    CORS_ORIGINS: list[AnyHttpUrl] = []

    postgres: PostgresSettings = PostgresSettings()
    rabbit_mq: RabbitMQSettings = RabbitMQSettings()

    @model_validator(mode="after")
    def set_debug(self) -> Self:
        self.DEBUG = self.APP_ENV != "production"
        return self


@cache
def get_settings() -> Settings:
    return Settings()
