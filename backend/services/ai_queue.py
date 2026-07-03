import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from config import settings


class AIQueueBusyError(Exception):
    """Raised when an AI provider rate limit or concurrency cap is exceeded."""

    def __init__(self, message: str, cooldown_seconds: float = 0.0):
        super().__init__(message)
        self.cooldown_seconds = cooldown_seconds


@dataclass
class _ProviderBucket:
    """Rate limit bucket for a single AI provider."""

    max_rpm: int
    max_concurrent: int
    window_seconds: int = 60
    _requests: List[float] = field(default_factory=list)
    _concurrent: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def acquire(self, timeout: float = 0.0) -> Optional[float]:
        """Try to acquire a slot. Returns cooldown seconds if unavailable, or None on success."""
        deadline = time.time() + timeout
        while True:
            with self._lock:
                now = time.time()
                cutoff = now - self.window_seconds
                self._requests = [t for t in self._requests if t > cutoff]

                if self._concurrent < self.max_concurrent and len(self._requests) < self.max_rpm:
                    self._concurrent += 1
                    self._requests.append(now)
                    return None

                # Compute the soonest time a slot will be available.
                cooldown = 0.0
                if self._concurrent >= self.max_concurrent:
                    cooldown = max(cooldown, 0.1)
                if len(self._requests) >= self.max_rpm:
                    cooldown = max(cooldown, self._requests[0] + self.window_seconds - now, 0.0)

            if timeout <= 0:
                return cooldown

            wait_time = min(cooldown, deadline - time.time())
            if wait_time <= 0:
                return cooldown
            time.sleep(wait_time)

            if time.time() >= deadline:
                return cooldown

    def release(self) -> None:
        with self._lock:
            self._concurrent = max(0, self._concurrent - 1)

    def status(self) -> dict:
        with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds
            recent = [t for t in self._requests if t > cutoff]
            return {
                "max_rpm": self.max_rpm,
                "max_concurrent": self.max_concurrent,
                "recent_requests": len(recent),
                "current_concurrent": self._concurrent,
                "available_rpm": max(0, self.max_rpm - len(recent)),
                "available_concurrent": max(0, self.max_concurrent - self._concurrent),
            }


class AIQueue:
    """Process-global singleton that rate-limits AI calls per provider.

    Each provider has its own RPM and concurrency bucket. Requests block until
    a slot is available or the configured timeout is exceeded. When the limit
    is hit, ``AIQueueBusyError`` is raised with a ``cooldown_seconds`` hint.
    """

    _instance: Optional["AIQueue"] = None
    _instance_lock = threading.Lock()

    def __new__(cls) -> "AIQueue":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        self._state_lock = threading.Lock()
        self._pending_count = 0
        self._current_task: Optional[str] = None
        self._timeout_seconds = float(settings.OLLAMA_AI_QUEUE_TIMEOUT_SECONDS)
        self._buckets: Dict[str, _ProviderBucket] = {
            "gemini_generation": _ProviderBucket(
                max_rpm=settings.GEMINI_GENERATION_RPM,
                max_concurrent=settings.GEMINI_GENERATION_CONCURRENT,
            ),
            "gemini_embedding": _ProviderBucket(
                max_rpm=settings.GEMINI_EMBEDDING_RPM,
                max_concurrent=settings.GEMINI_EMBEDDING_CONCURRENT,
            ),
            "ollama_generation": _ProviderBucket(
                max_rpm=settings.OLLAMA_GENERATION_RPM,
                max_concurrent=settings.OLLAMA_GENERATION_CONCURRENT,
            ),
            "ollama_embedding": _ProviderBucket(
                max_rpm=settings.OLLAMA_EMBEDDING_RPM,
                max_concurrent=settings.OLLAMA_EMBEDDING_CONCURRENT,
            ),
        }

    def run(self, task_name: str, fn: Callable[[], Any]) -> Any:
        """Legacy single-slot API. Defaults to the Ollama generation bucket."""
        return self.run_with_provider("ollama_generation", task_name, fn)

    def run_with_provider(
        self, provider: str, task_name: str, fn: Callable[[], Any]
    ) -> Any:
        """Execute ``fn`` while holding a slot for the given provider.

        Args:
            provider: Provider bucket name (e.g., ``gemini_generation``).
            task_name: Human-readable task name for status reporting.
            fn: Callable that performs the actual AI call.

        Returns:
            The return value of ``fn``.

        Raises:
            AIQueueBusyError: If the provider limit is exceeded and the timeout
                expires. ``cooldown_seconds`` hints when the next slot opens.
        """
        bucket = self._buckets.get(provider)
        if bucket is None:
            raise AIQueueBusyError(f"Unknown AI provider: {provider}")

        with self._state_lock:
            self._pending_count += 1

        cooldown = bucket.acquire(timeout=self._timeout_seconds)
        if cooldown is not None:
            with self._state_lock:
                self._pending_count = max(0, self._pending_count - 1)
            raise AIQueueBusyError(
                f"AI đang bận (provider {provider}). Vui lòng đợi {int(cooldown) + 1}s.",
                cooldown_seconds=cooldown,
            )

        try:
            with self._state_lock:
                self._pending_count = max(0, self._pending_count - 1)
                self._current_task = f"{provider}:{task_name}"
            return fn()
        finally:
            with self._state_lock:
                self._current_task = None
            bucket.release()

    def status(self) -> dict:
        """Return the current queue state and per-provider bucket status."""
        with self._state_lock:
            return {
                "busy": self._current_task is not None,
                "queue_length": self._pending_count,
                "current_task": self._current_task,
                "providers": {
                    name: bucket.status() for name, bucket in self._buckets.items()
                },
            }

    def provider_status(self, provider: str) -> dict:
        """Return the rate-limit status for a specific provider."""
        bucket = self._buckets.get(provider)
        if bucket is None:
            return {"error": f"Unknown provider: {provider}"}
        return bucket.status()

    def is_busy(self) -> bool:
        """Return True if an AI task is currently running."""
        with self._state_lock:
            return self._current_task is not None
