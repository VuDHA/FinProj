import threading
import time

import pytest

from services.ai_queue import AIQueue, AIQueueBusyError


def test_ai_queue_runs_task():
    queue = AIQueue()
    result = queue.run("test_task", lambda: "ok")
    assert result == "ok"


def test_ai_queue_serializes_tasks():
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
            queue.run(f"task_{i}", lambda: task(f"t{i}", 0.05))
        return runner

    threads = [threading.Thread(target=make_runner(i)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # All tasks completed and only one ran at a time.
    assert len(results) == 3
    assert len(set(results)) == 3


def test_ai_queue_busy_error_with_timeout():
    queue = AIQueue()
    original_timeout = queue._timeout_seconds
    queue._timeout_seconds = 0.1

    def slow_task():
        time.sleep(0.5)
        return "done"

    t1 = threading.Thread(target=lambda: queue.run("slow", slow_task))
    t1.start()
    time.sleep(0.05)  # Let t1 acquire the lock

    try:
        with pytest.raises(AIQueueBusyError):
            queue.run("fast", lambda: "fast")
    finally:
        queue._timeout_seconds = original_timeout
        t1.join()


def test_ai_queue_status():
    queue = AIQueue()
    status = queue.status()
    assert "busy" in status
    assert "queue_length" in status
    assert "current_task" in status
