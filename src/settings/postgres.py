from typing import Self

from pydantic import PostgresDsn, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_POSTGRES_DRIVER = "postgresql+asyncpg"


class PostgresSettings(BaseSettings):
    HOST: str
    PORT: int
    USER: str
    PASSWORD: SecretStr
    DATABASE: str

    POOL_SIZE: int = 10
    MAX_OVERFLOW: int = 20
    POOL_TIMEOUT: int = 30
    POOL_RECYCLE: int = 1800

    DATABASE_URL: str = ""

    @model_validator(mode="after")
    def build_database_url(self) -> Self:
        self.DATABASE_URL = str(
            PostgresDsn.build(
                scheme=DEFAULT_POSTGRES_DRIVER,
                username=self.USER,
                password=self.PASSWORD.get_secret_value(),
                host=self.HOST,
                port=self.PORT,
                path=self.DATABASE,
            )
        )
        return self

    model_config = SettingsConfigDict(
        env_prefix="POSTGRES_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
