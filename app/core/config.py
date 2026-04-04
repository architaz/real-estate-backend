import os
import logging
from urllib.parse import quote_plus
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    app_name: str = "Real Estate Backend"
    debug: bool = False
    log_level: str = "INFO"

    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "railway"

    external_api_url: str = ""
    external_api_key: str = ""
    external_api_host: str = ""

    sync_interval_hours: int = 1

    @property
    def database_url(self) -> str:
        password = quote_plus(self.db_password)
        url = f"mysql+pymysql://{self.db_user}:{password}@{self.db_host}:{self.db_port}/{self.db_name}"
        # Temporary debug — remove after fixing
        print(f"[DEBUG] DB_HOST={self.db_host}, DB_PORT={self.db_port}, DB_USER={self.db_user}, DB_NAME={self.db_name}")
        print(f"[DEBUG] Built URL: mysql+pymysql://{self.db_user}:***@{self.db_host}:{self.db_port}/{self.db_name}")
        return url

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )

settings = Settings()

# Also print all relevant env vars at import time
print(f"[DEBUG] os.environ DB_HOST={os.environ.get('DB_HOST', 'NOT SET')}")
print(f"[DEBUG] os.environ DB_PORT={os.environ.get('DB_PORT', 'NOT SET')}")
print(f"[DEBUG] os.environ DB_USER={os.environ.get('DB_USER', 'NOT SET')}")
print(f"[DEBUG] os.environ DB_NAME={os.environ.get('DB_NAME', 'NOT SET')}")