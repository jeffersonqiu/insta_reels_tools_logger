from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _strip_secret(v: object) -> object:
    if not isinstance(v, str):
        return v
    s = v.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1].strip()
    return s


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    supabase_url: str = ""
    supabase_service_key: str = ""
    assemblyai_api_key: str = ""
    anthropic_api_key: str = ""
    anthropic_model: str = Field(default="claude-sonnet-4-6", min_length=1)
    telegram_bot_token: str = ""
    telegram_allowed_user_ids: str = ""
    public_app_url: str = ""
    webhook_secret: str = ""
    cors_allow_origins: str = "*"
    processing_mode: Literal["inline", "github_actions"] = "inline"
    instagram_cookies_b64: str = ""

    @field_validator(
        "supabase_url",
        "supabase_service_key",
        "assemblyai_api_key",
        "anthropic_api_key",
        "anthropic_model",
        "telegram_bot_token",
        "public_app_url",
        "webhook_secret",
        "instagram_cookies_b64",
        mode="before",
    )
    @classmethod
    def strip_secrets(cls, v: object) -> object:
        return _strip_secret(v)

    @field_validator("telegram_allowed_user_ids")
    @classmethod
    def validate_telegram_users(cls, value: str) -> str:
        if not value.strip():
            return ""
        ids = [part.strip() for part in value.split(",")]
        if any(not part.isascii() or not part.isdigit() or int(part) <= 0 for part in ids):
            raise ValueError("Use comma-separated positive Telegram user IDs.")
        return ",".join(str(int(part)) for part in ids)


settings = Settings()
