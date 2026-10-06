"""Typed configuration. Values come from environment variables, falling back to a .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class BrokerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"


class ServiceSettings(BrokerSettings):
    service_name: str = "unknown-service"
    environment: str = "dev"
    log_level: str = "INFO"
