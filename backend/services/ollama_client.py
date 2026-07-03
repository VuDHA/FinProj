import time
from typing import Any, Dict, List, Optional

import requests

from config import settings
from services.ai_queue import AIQueue, AIQueueBusyError


class OllamaClientError(Exception):
    """Raised when an Ollama call fails or returns an unexpected response."""

    pass


class OllamaClient:
    """Centralized Ollama HTTP client that respects the global AI queue.

    All Ollama calls (generate, embeddings) go through this client so the
    process-wide ``AIQueue`` can enforce the single-AI-call constraint.
    """

    def __init__(
        self,
        base_url: str = settings.OLLAMA_BASE_URL,
        timeout: int = settings.OLLAMA_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout as e:
            raise OllamaClientError(f"Ollama request timed out: {e}")
        except requests.exceptions.RequestException as e:
            raise OllamaClientError(f"Ollama request failed: {e}")
        except ValueError as e:
            raise OllamaClientError(f"Ollama returned invalid JSON: {e}")

    def _default_options(self, options: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Merge caller options with CPU tuning defaults from settings."""
        merged = dict(options) if options else {}
        if settings.OLLAMA_NUM_THREADS > 0 and "num_thread" not in merged:
            merged["num_thread"] = settings.OLLAMA_NUM_THREADS
        return merged if merged else None

    def _apply_keep_alive(self, payload: Dict[str, Any]) -> None:
        """Add per-request keep_alive if configured in settings."""
        if settings.OLLAMA_KEEP_ALIVE:
            payload["keep_alive"] = settings.OLLAMA_KEEP_ALIVE

    def generate(
        self,
        prompt: str,
        model: str = settings.OLLAMA_MODEL,
        options: Optional[Dict[str, Any]] = None,
        task_name: str = "ollama_generate",
    ) -> str:
        """Generate text via the Ollama /api/generate endpoint."""
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        merged_options = self._default_options(options)
        if merged_options:
            payload["options"] = merged_options
        self._apply_keep_alive(payload)

        start = time.time()

        def _call() -> str:
            data = self._post("/api/generate", payload)
            return data.get("response", "")

        try:
            result = AIQueue().run_with_provider("ollama_generation", task_name, _call)
            log_ai_call(
                task_name=task_name,
                start_time=start,
                queue_wait_seconds=0.0,
                success=True,
            )
            return result
        except AIQueueBusyError as e:
            log_ai_call(
                task_name=task_name,
                start_time=start,
                queue_wait_seconds=0.0,
                success=False,
                error=str(e),
            )
            raise OllamaClientError(str(e))
        except OllamaClientError as e:
            log_ai_call(
                task_name=task_name,
                start_time=start,
                queue_wait_seconds=0.0,
                success=False,
                error=str(e),
            )
            raise

    def embed(
        self,
        text: str,
        model: str = settings.OLLAMA_EMBEDDING_MODEL,
        task_name: str = "ollama_embedding",
    ) -> List[float]:
        """Create an embedding vector via the Ollama /api/embeddings endpoint."""
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": text,
        }
        merged_options = self._default_options(None)
        if merged_options:
            payload["options"] = merged_options
        self._apply_keep_alive(payload)

        start = time.time()

        def _call() -> List[float]:
            data = self._post("/api/embeddings", payload)
            embedding = data.get("embedding")
            if not isinstance(embedding, list):
                raise OllamaClientError("Ollama embeddings response missing 'embedding' list")
            return embedding

        try:
            result = AIQueue().run_with_provider("ollama_embedding", task_name, _call)
            log_ai_call(
                task_name=task_name,
                start_time=start,
                queue_wait_seconds=0.0,
                success=True,
            )
            return result
        except AIQueueBusyError as e:
            log_ai_call(
                task_name=task_name,
                start_time=start,
                queue_wait_seconds=0.0,
                success=False,
                error=str(e),
            )
            raise OllamaClientError(str(e))
        except OllamaClientError as e:
            log_ai_call(
                task_name=task_name,
                start_time=start,
                queue_wait_seconds=0.0,
                success=False,
                error=str(e),
            )
            raise


def log_ai_call(
    task_name: str,
    start_time: float,
    queue_wait_seconds: float,
    success: bool,
    error: Optional[str] = None,
) -> None:
    """Standardized stdout log for AI call observability."""
    duration = time.time() - start_time
    status = "ok" if success else "error"
    msg = (
        f"[ai] task={task_name} status={status} "
        f"queue_wait={queue_wait_seconds:.2f}s total={duration:.2f}s"
    )
    if error:
        msg += f" error={error}"
    print(msg)
