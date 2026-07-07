from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    database_url: str

    discord_webhook_url: str = ""

    gmail_personal_address: str = ""
    gmail_personal_app_password: str = ""
    gmail_business_address: str = ""
    gmail_business_app_password: str = ""

    account_holder_names: str = ""

    long_holiday_start: str = ""
    long_holiday_end: str = ""

    import_transactions_dir: str = "../import/transactions"
    import_assets_dir: str = "../import/assets"

    cors_allow_origins: str = "http://localhost:5173,http://localhost:3000"

    pg_dump_path: str = "pg_dump"
    backup_dir: str = "../backups"
    backup_daily_retention_days: int = 30
    backup_month_end_retention_days: int = 365

    batch_retry_count: int = 3
    batch_retry_delay_seconds: float = 5.0

    @property
    def cors_allow_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]

    @property
    def account_holder_names_list(self) -> list[str]:
        return [name.strip() for name in self.account_holder_names.split(",") if name.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
