from typing import Self

from pydantic import AmqpDsn, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RabbitMQSettings(BaseSettings):
    HOST: str
    PORT: int
    USER: str
    PASSWORD: SecretStr
    VIRTUAL_HOST: str

    PREFETCH_COUNT: int = 10
    HEARTBEAT: int = 60

    DATABASE_URL: str = ""

    @model_validator(mode="after")
    def build_database_url(self) -> Self:
        self.DATABASE_URL = str(
            AmqpDsn.build(
                scheme="amqp",
                username=self.USER,
                password=self.PASSWORD.get_secret_value(),
                host=self.HOST,
                port=self.PORT,
                path=self.VIRTUAL_HOST,
            )
        )
        return self

    model_config = SettingsConfigDict(
        env_prefix="RABBITMQ_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
