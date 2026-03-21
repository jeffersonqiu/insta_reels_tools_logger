from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    supabase_url: str = ""
    supabase_service_key: str = ""
    assemblyai_api_key: str = ""
    anthropic_api_key: str = ""
    telegram_bot_token: str = ""
    webhook_secret: str = ""
    cors_allow_origins: str = "*"


settings = Settings()
