import threading
import time
from typing import Any, Callable, Optional

from config import settings


class AIQueueBusyError(Exception):
    """Raised when the global AI queue times out waiting for a free slot."""

    pass


class AIQueue:
    """Process-global singleton that serializes all Ollama calls.

    Only one AI task (generate, embedding, or any other Ollama endpoint) may
    run at a time. Concurrent requests wait for the active task to finish, up
    to ``OLLAMA_AI_QUEUE_TIMEOUT_SECONDS``. If the timeout is exceeded, a
    ``AIQueueBusyError`` is raised.
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
        self._task_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._pending_count = 0
        self._current_task: Optional[str] = None
        self._timeout_seconds = float(settings.OLLAMA_AI_QUEUE_TIMEOUT_SECONDS)

    def run(self, task_name: str, fn: Callable[[], Any]) -> Any:
        """Execute ``fn`` while holding the single AI slot.

        Args:
            task_name: Human-readable task name for status reporting.
            fn: Callable that performs the actual Ollama call.

        Returns:
            The return value of ``fn``.

        Raises:
            AIQueueBusyError: If the queue times out before the slot is free.
            Any exception raised by ``fn`` is propagated after releasing the slot.
        """
        with self._state_lock:
            self._pending_count += 1

        acquired = self._task_lock.acquire(timeout=self._timeout_seconds)
        if not acquired:
            with self._state_lock:
                self._pending_count = max(0, self._pending_count - 1)
            raise AIQueueBusyError(
                "AI is busy. Please wait for the current AI task to finish."
            )

        try:
            with self._state_lock:
                self._pending_count = max(0, self._pending_count - 1)
                self._current_task = task_name
            return fn()
        finally:
            with self._state_lock:
                self._current_task = None
            self._task_lock.release()

    def status(self) -> dict:
        """Return the current queue state."""
        with self._state_lock:
            return {
                "busy": self._current_task is not None,
                "queue_length": self._pending_count,
                "current_task": self._current_task,
            }

    def is_busy(self) -> bool:
        """Return True if an AI task is currently running."""
        with self._state_lock:
            return self._current_task is not None
