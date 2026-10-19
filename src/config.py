"""Управління конфігурацією застосунку через ``pydantic-settings``."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфігураційні параметри застосунку.

    Attributes:
        bot_token: Токен Telegram-бота, отриманий від @BotFather.
        db_url: Рядок підключення до PostgreSQL (asyncpg драйвер).
        log_level: Рівень логування застосунку.
        locale: Код локалізації інтерфейсу.
        openrouter_api_key: API-ключ OpenRouter (порожній — OCR вимкнено).
        openrouter_model: Ідентифікатор Vision-LLM моделі OpenRouter.
        openrouter_base_url: Базовий URL OpenAI-сумісного API OpenRouter.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    bot_token: str
    db_url: str
    log_level: str = "INFO"
    locale: str = "uk"
    openrouter_api_key: str = ""
    openrouter_model: str = "nvidia/nemotron-3.5-super-vl:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"


@lru_cache
def get_settings() -> Settings:
    """Повертає закешований екземпляр конфігурації.

    Returns:
        Settings: Готовий до використання об'єкт налаштувань.
    """
    return Settings()
