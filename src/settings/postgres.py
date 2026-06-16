from typing import Self

from pydantic import PostgresDsn, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .common import ENV_FILE_PATH

DEFAULT_POSTGRES_DRIVER = "postgresql+asyncpg"


class PostgresSettings(BaseSettings):
    HOST: str
    PORT: int
    USER: str
    PASSWORD: SecretStr
    DATABASE: str

    POOL_SIZE: int
    MAX_OVERFLOW: int
    POOL_TIMEOUT: int
    POOL_RECYCLE: int

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

    model_config = SettingsConfigDict(env_file=ENV_FILE_PATH, env_prefix="POSTGRES_", extra="ignore")
