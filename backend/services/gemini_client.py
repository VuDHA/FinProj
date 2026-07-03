import time
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

from config import settings


class GeminiClientError(Exception):
    """Raised when a Gemini API call fails or returns an unexpected response."""

    pass


class GeminiClient:
    """Low-level Google Gemini client wrapping the official google-genai SDK.

    Supports single and batched text generation plus batched embeddings.
    All errors are normalized to GeminiClientError.
    """

    def __init__(
        self,
        api_key: str = settings.GEMINI_API_KEY,
        base_url: str = settings.GEMINI_BASE_URL,
        timeout: int = settings.AI_TIMEOUT_SECONDS,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = self._build_client()

    def _build_client(self) -> genai.Client:
        if not self.api_key:
            raise GeminiClientError("GEMINI_API_KEY is not configured")
        return genai.Client(
            api_key=self.api_key,
            http_options=types.HttpOptions(
                base_url=self.base_url,
                timeout=self.timeout * 1000,  # milliseconds
            ),
        )

    def _log(
        self,
        task_name: str,
        duration: float,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        status = "ok" if success else "error"
        msg = f"[gemini] task={task_name} status={status} total={duration:.2f}s"
        if error:
            msg += f" error={error}"
        print(msg)

    def generate(
        self,
        prompt: str,
        model: str = settings.GEMINI_MODEL,
        temperature: float = 0.2,
        max_tokens: int = 256,
        task_name: str = "gemini_generate",
    ) -> str:
        """Generate text from a single prompt."""
        start = time.time()
        try:
            response = self._client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            text = response.text or ""
            self._log(task_name, time.time() - start, True)
            return text
        except Exception as e:
            self._log(task_name, time.time() - start, False, error=str(e))
            raise GeminiClientError(f"Gemini generation failed: {e}") from e

    def generate_batch(
        self,
        prompt: str,
        model: str = settings.GEMINI_MODEL,
        temperature: float = 0.2,
        max_tokens: int = 512,
        task_name: str = "gemini_generate_batch",
    ) -> str:
        """Generate text from a single prompt that contains multiple tasks.

        The caller is responsible for building the batched prompt and parsing
        the batched response.
        """
        start = time.time()
        try:
            response = self._client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    response_mime_type="application/json",
                ),
            )
            text = response.text or ""
            self._log(task_name, time.time() - start, True)
            return text
        except Exception as e:
            self._log(task_name, time.time() - start, False, error=str(e))
            raise GeminiClientError(f"Gemini batch generation failed: {e}") from e

    def embed(
        self,
        text: str,
        model: str = settings.GEMINI_EMBEDDING_MODEL,
        task_name: str = "gemini_embed",
    ) -> List[float]:
        """Create an embedding vector for a single text."""
        start = time.time()
        try:
            response = self._client.models.embed_content(
                model=model,
                contents=text,
            )
            vector = self._extract_embedding(response)
            self._log(task_name, time.time() - start, True)
            return vector
        except Exception as e:
            self._log(task_name, time.time() - start, False, error=str(e))
            raise GeminiClientError(f"Gemini embedding failed: {e}") from e

    def embed_batch(
        self,
        texts: List[str],
        model: str = settings.GEMINI_EMBEDDING_MODEL,
        task_name: str = "gemini_embed_batch",
    ) -> List[List[float]]:
        """Create embedding vectors for a list of texts."""
        if not texts:
            return []
        start = time.time()
        try:
            response = self._client.models.embed_content(
                model=model,
                contents=texts,
            )
            vectors = [self._extract_embedding(item) for item in response.embeddings]
            self._log(task_name, time.time() - start, True)
            return vectors
        except Exception as e:
            self._log(task_name, time.time() - start, False, error=str(e))
            raise GeminiClientError(f"Gemini batch embedding failed: {e}") from e

    @staticmethod
    def _extract_embedding(response: Any) -> List[float]:
        """Return the embedding vector from an EmbedContentResponse or embedding item."""
        if hasattr(response, "values"):
            values = response.values
        elif hasattr(response, "embedding"):
            values = response.embedding.values
        else:
            raise GeminiClientError("Gemini embedding response has no values")
        if not isinstance(values, list):
            raise GeminiClientError("Gemini embedding values are not a list")
        return [float(v) for v in values]

    def is_configured(self) -> bool:
        """Return True if the client has an API key and can be used."""
        return bool(self.api_key)
