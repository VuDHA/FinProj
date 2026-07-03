from typing import Optional, Union

from common.config import settings
from services.ai.gemini_client import GeminiClient, GeminiClientError
from services.ai.ollama_client import OllamaClient


class AIProviderError(Exception):
    """Raised when no AI provider is available."""

    pass


class AIProviderFactory:
    """Create the active AI provider based on settings.

    Primary provider is Gemini when AI_PROVIDER=gemini and GEMINI_API_KEY is set.
    Ollama is used when AI_PROVIDER=ollama or when Gemini is not configured.
    """

    @staticmethod
    def primary_provider() -> Optional[Union[GeminiClient, OllamaClient]]:
        if settings.AI_PROVIDER == "gemini":
            try:
                return GeminiClient()
            except GeminiClientError:
                return None
        return None

    @staticmethod
    def fallback_provider() -> Optional[OllamaClient]:
        if settings.OLLAMA_ENABLED:
            return OllamaClient()
        return None

    @staticmethod
    def generation_provider() -> Union[GeminiClient, OllamaClient]:
        provider = AIProviderFactory.primary_provider()
        if provider is not None:
            return provider
        fallback = AIProviderFactory.fallback_provider()
        if fallback is not None:
            return fallback
        raise AIProviderError("No AI provider configured. Set GEMINI_API_KEY or enable Ollama.")

    @staticmethod
    def embedding_provider() -> Union[GeminiClient, OllamaClient]:
        # Prefer Gemini for embeddings when the provider is active, unless the user
        # explicitly keeps Ollama embeddings enabled.
        if settings.AI_PROVIDER == "gemini" and not settings.OLLAMA_EMBEDDING_ENABLED:
            try:
                return GeminiClient()
            except GeminiClientError:
                pass
        if settings.OLLAMA_ENABLED:
            return OllamaClient()
        raise AIProviderError("No AI provider configured for embeddings.")
