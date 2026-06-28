import os

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB = f"sqlite:///{os.path.join(PROJECT_ROOT, 'data', 'wealth.db')}"


class Settings(BaseSettings):
    DATABASE_URL: str = DEFAULT_DB
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    SCHEDULER_HOUR: int = 15
    SCHEDULER_MINUTE: int = 35

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
