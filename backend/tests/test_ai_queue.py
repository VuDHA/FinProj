import threading
import time

import pytest

from services.ai.ai_queue import AIQueue, AIQueueBusyError


def test_ai_queue_runs_task():
    queue = AIQueue()
    result = queue.run_with_provider("ollama_generation", "test_task", lambda: "ok")
    assert result == "ok"

    # Legacy API still works and defaults to ollama_generation.
    result = queue.run("legacy_task", lambda: "ok")
    assert result == "ok"


def test_ai_queue_allows_concurrent_providers():
    queue = AIQueue()
    results = []
    lock = threading.Lock()

    def task(name: str, delay: float):
        time.sleep(delay)
        with lock:
            results.append(name)
        return name

    def make_runner(provider: str, i: int):
        def runner():
            queue.run_with_provider(provider, f"task_{i}", lambda: task(f"t{i}", 0.05))
        return runner

    # Different provider buckets can run concurrently.
    threads = [
        threading.Thread(target=make_runner("gemini_generation", 0)),
        threading.Thread(target=make_runner("ollama_generation", 1)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 2
    assert len(set(results)) == 2


def test_ai_queue_serializes_same_provider():
    queue = AIQueue()
    results = []
    lock = threading.Lock()

    def task(name: str, delay: float):
        time.sleep(delay)
        with lock:
            results.append(name)
        return name

    def make_runner(i: int):
        def runner():
            queue.run_with_provider("ollama_generation", f"task_{i}", lambda: task(f"t{i}", 0.05))
        return runner

    threads = [threading.Thread(target=make_runner(i)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # All tasks completed and only one ran at a time because Ollama allows 1 concurrent.
    assert len(results) == 3
    assert len(set(results)) == 3


def test_ai_queue_rate_limit_with_timeout():
    queue = AIQueue()
    original_timeout = queue._timeout_seconds
    queue._timeout_seconds = 0.1

    def slow_task():
        time.sleep(0.5)
        return "done"

    t1 = threading.Thread(target=lambda: queue.run_with_provider("ollama_generation", "slow", slow_task))
    t1.start()
    time.sleep(0.05)

    try:
        with pytest.raises(AIQueueBusyError) as exc_info:
            queue.run_with_provider("ollama_generation", "fast", lambda: "fast")
        assert exc_info.value.cooldown_seconds >= 0
    finally:
        queue._timeout_seconds = original_timeout
        t1.join()


def test_ai_queue_status():
    queue = AIQueue()
    status = queue.status()
    assert "busy" in status
    assert "queue_length" in status
    assert "current_task" in status
    assert "providers" in status
    assert "gemini_generation" in status["providers"]
    assert "ollama_generation" in status["providers"]
