import datetime
import threading
import uuid
from typing import Callable, Dict, List, Optional


class RefreshProgress:
    """Mutable progress state for a single refresh job."""

    def __init__(self, source_code: Optional[str] = None):
        self.id = str(uuid.uuid4())
        self.source_code = source_code
        self.status = "running"  # running | completed | error | timeout
        self.total_sources = 0
        self.current_source_index = 0
        self.current_source = ""
        self.processed = 0
        self.new_articles = 0
        self.errors: List[str] = []
        self.results: Dict[str, int] = {}
        self.alerts_generated = 0
        self.message = ""
        self.created_at = datetime.datetime.utcnow()
        self.updated_at = datetime.datetime.utcnow()
        self._listeners: List[Callable[[], None]] = []
        self._lock = threading.Lock()

    def update(self, **kwargs) -> None:
        with self._lock:
            for key, value in kwargs.items():
                setattr(self, key, value)
            self.updated_at = datetime.datetime.utcnow()
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener()
            except Exception:
                pass

    def add_error(self, error: str) -> None:
        with self._lock:
            self.errors.append(error)
            self.updated_at = datetime.datetime.utcnow()

    def add_listener(self, listener: Callable[[], None]) -> None:
        with self._lock:
            self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[], None]) -> None:
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)

    def to_dict(self) -> Dict:
        with self._lock:
            return {
                "id": self.id,
                "source_code": self.source_code,
                "status": self.status,
                "total_sources": self.total_sources,
                "current_source_index": self.current_source_index,
                "current_source": self.current_source,
                "processed": self.processed,
                "new_articles": self.new_articles,
                "errors": list(self.errors),
                "results": dict(self.results),
                "alerts_generated": self.alerts_generated,
                "message": self.message,
            }


class RefreshTracker:
    """In-memory registry of refresh jobs."""

    _jobs: Dict[str, RefreshProgress] = {}
    _lock = threading.Lock()

    @classmethod
    def create(cls, source_code: Optional[str] = None) -> RefreshProgress:
        job = RefreshProgress(source_code=source_code)
        with cls._lock:
            cls._jobs[job.id] = job
        return job

    @classmethod
    def get(cls, job_id: str) -> Optional[RefreshProgress]:
        with cls._lock:
            return cls._jobs.get(job_id)

    @classmethod
    def cleanup_old(cls, max_age_seconds: int = 3600) -> None:
        with cls._lock:
            now = datetime.datetime.utcnow()
            stale = [
                job_id
                for job_id, job in cls._jobs.items()
                if (now - job.updated_at).total_seconds() > max_age_seconds
            ]
            for job_id in stale:
                del cls._jobs[job_id]
