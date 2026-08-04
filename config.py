from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(..., min_length=20)
    admin_id: int

    # ponytail: no owner-wide Pollinations key. Every user pays with their own
    # token (/token), stored per-user in the DB. Setting this makes the bot fall
    # back to YOUR balance for everyone — leave it empty.
    pollinations_api_key: str = ""

    db_path: str = "data/bot.db"
    log_level: str = "INFO"
    pollinations_referrer: str = "promptart-bot"

    rate_limit_per_minute: int = 5
    daily_quota_free: int = 30


settings = Settings()
