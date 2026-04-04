from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Real Estate Backend"
    debug: bool = False
    log_level: str = "INFO"

    # Database - individual parts to avoid URL parsing issues
    db_host: str = ""
    db_port: int = 3306
    db_user: str = ""
    db_password: str = ""
    db_name: str = "railway"

    # External API
    external_api_url: str = ""
    external_api_key: str = ""
    external_api_host: str = ""

    sync_interval_hours: int = 1

    @property
    def database_url(self) -> str:
        from urllib.parse import quote_plus
        password = quote_plus(self.db_password)  # safely encodes @ and other special chars
        return f"mysql+pymysql://{self.db_user}:{password}@{self.db_host}:{self.db_port}/{self.db_name}"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )

settings = Settings()