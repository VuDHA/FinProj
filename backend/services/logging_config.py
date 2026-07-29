import logging
from datetime import datetime
from pathlib import Path


def setup_logging(project_root: str, level: int = logging.INFO) -> None:
    """Configure daily rotating logs under project_root/logs/YYYY-MM-DD/.

    A file handler writes to a per-day log file, and a stream handler mirrors
    output to the console.  The root logger is configured once; subsequent
    calls update only the daily file path so that long-running processes
    (e.g. the scheduler) continue to log to the correct day's file.

    Parameters
    ----------
    project_root:
        Absolute path to the project root.  Logs are written under
        ``<project_root>/logs/YYYY-MM-DD/``.
    level:
        Logging level for the root logger (default ``INFO``).
    """
    log_root = Path(project_root) / "logs"
    today = datetime.now().strftime("%Y-%m-%d")
    daily_dir = log_root / today
    daily_dir.mkdir(parents=True, exist_ok=True)

    log_file = daily_dir / "startup.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove any previously installed handlers so re-initialisation does not
    # result in duplicate log lines (e.g. when the lifespan runs twice in
    # tests).
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    logger = logging.getLogger(__name__)
    logger.info("Logging initialized; writing to %s", log_file)
