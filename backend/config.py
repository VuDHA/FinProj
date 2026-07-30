import os
import sys

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB = f"sqlite:///{os.path.join(PROJECT_ROOT, 'data', 'wealth.db')}"


def _resolve_env_file() -> str:
    """Return the path to the .env file used by pydantic_settings.

    When running as a PyInstaller-frozen sidecar, the bundled .env is not
    writable and lives in a temp extraction dir. We instead use a user-writable
    .env in the data directory (WEALTH_DATA_DIR) so users can configure API
    keys and other settings without rebuilding the app.
    """
    if getattr(sys, "frozen", False):
        data_dir = os.environ.get("WEALTH_DATA_DIR") or os.path.join(
            os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
            "wealth-vn",
            "data",
        )
        return os.path.join(data_dir, ".env")
    return os.path.join(os.path.dirname(__file__), ".env")


class Settings(BaseSettings):
    DATABASE_URL: str = DEFAULT_DB
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["*"]
    SCHEDULER_HOUR: int = 15
    SCHEDULER_MINUTE: int = 35

    # When True, expose /docs, /redoc, and /openapi.json.  Disable in production.
    DEBUG: bool = False

    # News scheduler settings
    NEWS_SCHEDULER_ENABLED: bool = True
    NEWS_VN_MARKET_INTERVAL_MINUTES: int = 15
    NEWS_VN_OFF_HOURS_INTERVAL_MINUTES: int = 30
    NEWS_GLOBAL_INTERVAL_MINUTES: int = 30

    # AI provider: "gemini" | "ollama". Gemini is the primary provider;
    # Ollama is used as fallback when Gemini is unavailable or disabled.
    AI_PROVIDER: str = "ollama"
    AI_BATCH_SIZE: int = 5
    AI_TIMEOUT_SECONDS: int = 30

    # Google Gemini API (primary AI provider).
    GEMINI_API_KEY: str = ""
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com"
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    GEMINI_EMBEDDING_DIMENSION: int = 768

    # Local LLM for tag generation (Ollama). Lightweight: runs on CPU/RAM.
    OLLAMA_ENABLED: bool = False
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:1.5b"
    OLLAMA_TIMEOUT: int = 30
    OLLAMA_MAX_TAGS: int = 5

    # News relevance scoring
    NEWS_RELEVANCE_THRESHOLD: float = 0.6
    NEWS_LLM_BATCH_SIZE: int = 1

    # CPU tuning for the Ollama server. 0 means let Ollama auto-detect threads.
    OLLAMA_NUM_THREADS: int = 0
    OLLAMA_KEEP_ALIVE: str = "15m"
    OLLAMA_NUM_PARALLEL: int = 1
    OLLAMA_MAX_LOADED_MODELS: int = 1

    # Global AI queue: only one Ollama call (generate or embedding) at a time.
    OLLAMA_AI_QUEUE_TIMEOUT_SECONDS: int = 60
    OLLAMA_EMBEDDING_ENABLED: bool = False
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    OLLAMA_EMBEDDING_DIMENSION: int = 768

    # Provider-aware rate limits for the AI queue (Gemini free tier).
    GEMINI_GENERATION_RPM: int = 15
    GEMINI_GENERATION_CONCURRENT: int = 2
    GEMINI_EMBEDDING_RPM: int = 100
    GEMINI_EMBEDDING_CONCURRENT: int = 5
    OLLAMA_GENERATION_RPM: int = 60
    OLLAMA_GENERATION_CONCURRENT: int = 1
    OLLAMA_EMBEDDING_RPM: int = 60
    OLLAMA_EMBEDDING_CONCURRENT: int = 1

    model_config = SettingsConfigDict(
        env_file=_resolve_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
