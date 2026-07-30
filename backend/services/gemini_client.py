import time
from typing import Any, Dict, List, Optional

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
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.base_url = (base_url if base_url is not None else settings.GEMINI_BASE_URL).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.AI_TIMEOUT_SECONDS
        self._client = self._build_client()

    def _build_client(self) -> Any:
        if not self.api_key:
            raise GeminiClientError("GEMINI_API_KEY is not configured")
        try:
            from google import genai
            from google.genai import types
        except ImportError as e:
            raise GeminiClientError(
                "google-genai SDK is not installed. Run: pip install google-genai"
            ) from e
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

    def generate(
        self,
        prompt: str,
        model: str = settings.GEMINI_MODEL,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        task_name: str = "gemini_generate",
    ) -> str:
        """Generate text from a single prompt."""
        from google.genai import types
        from services.ai_queue import AIQueue, AIQueueBusyError

        def _call() -> str:
            response = self._client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            return response.text or ""

        start = time.time()
        try:
            text = AIQueue().run_with_provider("gemini_generation", task_name, _call)
            self._log(task_name, time.time() - start, True)
            return text
        except AIQueueBusyError as e:
            self._log(task_name, time.time() - start, False, error=str(e))
            raise GeminiClientError(f"Gemini generation rate limited: {e}") from e
        except Exception as e:
            self._log(task_name, time.time() - start, False, error=str(e))
            raise GeminiClientError(f"Gemini generation failed: {e}") from e

    def generate_batch(
        self,
        prompt: str,
        model: str = settings.GEMINI_MODEL,
        temperature: float = 0.2,
        max_tokens: int = 8192,
        task_name: str = "gemini_generate_batch",
        response_mime_type: str = "application/json",
    ) -> str:
        """Generate text from a single prompt that contains multiple tasks.

        The caller is responsible for building the batched prompt and parsing
        the batched response.
        """
        from google.genai import types
        from services.ai_queue import AIQueue, AIQueueBusyError

        def _call() -> str:
            response = self._client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    response_mime_type=response_mime_type,
                ),
            )
            return response.text or ""

        start = time.time()
        try:
            text = AIQueue().run_with_provider("gemini_generation", task_name, _call)
            self._log(task_name, time.time() - start, True)
            return text
        except AIQueueBusyError as e:
            self._log(task_name, time.time() - start, False, error=str(e))
            raise GeminiClientError(f"Gemini generation rate limited: {e}") from e
        except Exception as e:
            self._log(task_name, time.time() - start, False, error=str(e))
            raise GeminiClientError(f"Gemini batch generation failed: {e}") from e

    def embed(
        self,
        text: str,
        model: str = settings.GEMINI_EMBEDDING_MODEL,
        task_name: str = "gemini_embed",
        dimension: int = settings.GEMINI_EMBEDDING_DIMENSION,
    ) -> List[float]:
        """Create an embedding vector for a single text."""
        from services.ai_queue import AIQueue, AIQueueBusyError

        def _call() -> List[float]:
            response = self._client.models.embed_content(
                model=model,
                contents=text,
                config=self._embed_config(dimension),
            )
            return self._extract_embedding(response)

        start = time.time()
        try:
            vector = AIQueue().run_with_provider("gemini_embedding", task_name, _call)
            self._log(task_name, time.time() - start, True)
            return vector
        except AIQueueBusyError as e:
            self._log(task_name, time.time() - start, False, error=str(e))
            raise GeminiClientError(f"Gemini embedding rate limited: {e}") from e
        except Exception as e:
            self._log(task_name, time.time() - start, False, error=str(e))
            raise GeminiClientError(f"Gemini embedding failed: {e}") from e

    def embed_batch(
        self,
        texts: List[str],
        model: str = settings.GEMINI_EMBEDDING_MODEL,
        task_name: str = "gemini_embed_batch",
        dimension: int = settings.GEMINI_EMBEDDING_DIMENSION,
    ) -> List[List[float]]:
        """Create embedding vectors for a list of texts."""
        if not texts:
            return []
        from services.ai_queue import AIQueue, AIQueueBusyError

        def _call() -> List[List[float]]:
            response = self._client.models.embed_content(
                model=model,
                contents=texts,
                config=self._embed_config(dimension),
            )
            return [self._extract_embedding(item) for item in response.embeddings]

        start = time.time()
        try:
            vectors = AIQueue().run_with_provider("gemini_embedding", task_name, _call)
            self._log(task_name, time.time() - start, True)
            return vectors
        except AIQueueBusyError as e:
            self._log(task_name, time.time() - start, False, error=str(e))
            raise GeminiClientError(f"Gemini embedding rate limited: {e}") from e
        except Exception as e:
            self._log(task_name, time.time() - start, False, error=str(e))
            raise GeminiClientError(f"Gemini batch embedding failed: {e}") from e

    def _embed_config(self, dimension: int) -> Optional[Any]:
        try:
            from google.genai import types

            return types.EmbedContentConfig(output_dimensionality=dimension)
        except Exception:
            return None

    @staticmethod
    def _extract_embedding(response: Any) -> List[float]:
        """Return the embedding vector from an EmbedContentResponse or embedding item."""
        # A full EmbedContentResponse contains a list of embeddings; pick the first one.
        if hasattr(response, "embeddings") and response.embeddings:
            response = response.embeddings[0]
        if hasattr(response, "values"):
            values = response.values
        elif hasattr(response, "embedding") and hasattr(response.embedding, "values"):
            values = response.embedding.values
        else:
            raise GeminiClientError("Gemini embedding response has no values")
        if not isinstance(values, list):
            raise GeminiClientError("Gemini embedding values are not a list")
        return [float(v) for v in values]

    def is_configured(self) -> bool:
        """Return True if the client has an API key and can be used."""
        return bool(self.api_key)
