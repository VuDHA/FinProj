import logging
from datetime import datetime
from pathlib import Path


def setup_logging(project_root: str) -> None:
    """Configure daily rotating logs under project_root/logs/YYYY-MM-DD/."""
    log_root = Path(project_root) / "logs"
    today = datetime.now().strftime("%Y-%m-%d")
    daily_dir = log_root / today
    daily_dir.mkdir(parents=True, exist_ok=True)

    log_file = daily_dir / "startup.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    logger = logging.getLogger(__name__)
    logger.info("Logging initialized; writing to %s", log_file)
