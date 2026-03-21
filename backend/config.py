from pydantic import field_validator
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
    telegram_bot_token: str = ""
    webhook_secret: str = ""
    cors_allow_origins: str = "*"

    @field_validator(
        "supabase_url",
        "supabase_service_key",
        "assemblyai_api_key",
        "anthropic_api_key",
        "telegram_bot_token",
        "webhook_secret",
        mode="before",
    )
    @classmethod
    def strip_secrets(cls, v: object) -> object:
        return _strip_secret(v)


settings = Settings()
