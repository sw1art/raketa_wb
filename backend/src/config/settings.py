"""Application settings loaded from environment variables / .env file."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "CheckStock"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"

    database_url: str = (
        "postgresql+asyncpg://checkstock:checkstock@localhost:5432/checkstock"
    )

    rabbitmq_url: str = "amqp://checkstock:checkstock@localhost:5672/"
    rabbitmq_exchange: str = "checkstock.events"
    rabbitmq_queue: str = "checkstock.events.queue"
    rabbitmq_dlq: str = "checkstock.events.dlq"
    rabbitmq_consumer_name: str = "event-journal"

    outbox_poll_interval: float = 1.0
    outbox_batch_size: int = 100
    outbox_max_retries: int = 5
    outbox_retry_base_delay: float = 2.0

    # Wildberries integration. Empty token => local demo mode.
    wb_api_token: str | None = None
    wb_content_base_url: str = "https://content-api.wildberries.ru"
    wb_marketplace_base_url: str = "https://marketplace-api.wildberries.ru"
    wb_statistics_base_url: str = "https://statistics-api.wildberries.ru"
    wb_supplies_base_url: str = "https://supplies-api.wildberries.ru"
    wb_request_timeout: float = 15.0
    wb_max_retries: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
