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
        env_file=os.path.join(os.path.dirname(__file__), ".env")
    )


settings = Settings()
