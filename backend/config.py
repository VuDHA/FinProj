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

    # Local LLM for tag generation (Ollama). Lightweight: runs on CPU/RAM.
    OLLAMA_ENABLED: bool = False
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:1.5b"
    OLLAMA_TIMEOUT: int = 30
    OLLAMA_MAX_TAGS: int = 5

    # Global AI queue: only one Ollama call (generate or embedding) at a time.
    OLLAMA_AI_QUEUE_TIMEOUT_SECONDS: int = 60
    OLLAMA_EMBEDDING_ENABLED: bool = False
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    OLLAMA_EMBEDDING_DIMENSION: int = 768

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), ".env")
    )


settings = Settings()
