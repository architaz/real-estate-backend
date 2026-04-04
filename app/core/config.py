"""
Application configuration using Pydantic Settings (v2).
Reads from environment variables with validation.
"""
# pyright: reportCallIssue=false
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    app_name: str = "Real Estate Backend"
    debug: bool = False
    log_level: str = "INFO"

    # Database
    database_url: str = ""

    # External API
    external_api_url: str = ""
    external_api_key: str = ""
    external_api_host: str = ""


    # Background Jobs
    sync_interval_hours: int = 1

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


settings = Settings()