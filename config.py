from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(..., min_length=20)
    pollinations_api_key: str = Field(..., min_length=10)
    admin_id: int

    db_path: str = "data/bot.db"
    log_level: str = "INFO"
    pollinations_referrer: str = "promptart-bot"

    rate_limit_per_minute: int = 5
    daily_quota_free: int = 30


settings = Settings()
