"""Automatic SQLite database backup job.

Uses SQLite's ``VACUUM INTO`` command to create a safe, consistent snapshot
of the database without acquiring an exclusive write lock.  The resulting
backup file is compressed with gzip and kept under a rolling retention
policy (7 daily + 4 weekly backups).
"""

import datetime
import gzip
import logging
import os
import shutil
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

# Rolling retention policy
MAX_DAILY_BACKUPS = 7
MAX_WEEKLY_BACKUPS = 4


def _backup_dir(backup_dir: str | Path) -> Path:
    """Ensure the backup directory exists and return it as a Path."""
    path = Path(backup_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _vacuum_into(db_path: str | Path, dest_path: str | Path) -> bool:
    """Use SQLite VACUUM INTO to create a safe, lock-free backup.

    ``VACUUM INTO`` creates a new database file containing a consistent
    snapshot without requiring an exclusive lock on the source database,
    making it safe to run while the app is serving requests.
    """
    db_path = str(db_path).replace("\\", "/")
    dest_path = str(dest_path).replace("\\", "/")
    # SQLite expects a URI-style path for VACUUM INTO when the path contains
    # special characters; quoting with single quotes inside the SQL string
    # handles most cases.
    engine = create_engine(f"sqlite:///{db_path}")
    try:
        with engine.connect() as conn:
            conn.execute(text(f"VACUUM INTO '{dest_path}'"))
            conn.commit()
        return True
    except Exception as e:
        logger.error("VACUUM INTO failed for %s: %s", db_path, e)
        return False
    finally:
        engine.dispose()


def _gzip_file(src: Path, dest: Path) -> None:
    """Compress *src* into *dest* using gzip."""
    with open(src, "rb") as f_in:
        with gzip.open(dest, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)


def _apply_rolling_retention(backup_dir: Path) -> None:
    """Keep the most recent *MAX_DAILY_BACKUPS* daily backups and
    *MAX_WEEKLY_BACKUPS* weekly backups (one per ISO week).

    Older daily backups that fall outside the daily window are kept only if
    they are the most recent backup of their ISO week (up to
    *MAX_WEEKLY_BACKUPS* weeks).  All others are deleted.
    """
    backups = sorted(
        backup_dir.glob("wealth_backup_*.db.gz"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not backups:
        return

    now = datetime.datetime.now()
    kept: list[Path] = []
    weekly_kept: dict[int, Path] = {}  # iso_week_key -> path

    for backup in backups:
        mtime = datetime.datetime.fromtimestamp(backup.stat().st_mtime)
        age_days = (now - mtime).days

        if age_days < MAX_DAILY_BACKUPS:
            # Within the daily retention window — always keep.
            kept.append(backup)
            continue

        # Outside the daily window: keep only the most recent per ISO week.
        iso_week_key = mtime.isocalendar()[1] * 100 + mtime.year
        if iso_week_key not in weekly_kept and len(weekly_kept) < MAX_WEEKLY_BACKUPS:
            weekly_kept[iso_week_key] = backup
            kept.append(backup)

    # Delete backups that are not retained.
    for backup in backups:
        if backup not in kept:
            try:
                backup.unlink()
                logger.info("Removed old backup %s", backup.name)
            except OSError as e:
                logger.warning("Could not remove old backup %s: %s", backup.name, e)


def backup_database(db_path: str | Path, backup_dir: str | Path) -> Optional[Path]:
    """Create a timestamped, gzipped backup of the SQLite database.

    Parameters
    ----------
    db_path:
        Filesystem path to the source SQLite database file.
    backup_dir:
        Directory where backups are stored.  Created if it does not exist.

    Returns
    -------
    The path to the created ``.db.gz`` backup file, or ``None`` on failure.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        logger.warning("Database file %s does not exist; skipping backup", db_path)
        return None

    out_dir = _backup_dir(backup_dir)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_backup = out_dir / f"wealth_backup_{timestamp}.db"
    gz_backup = out_dir / f"wealth_backup_{timestamp}.db.gz"

    # Step 1: VACUUM INTO a raw .db file (safe, no exclusive lock).
    if not _vacuum_into(db_path, raw_backup):
        return None

    # Step 2: Compress with gzip.
    try:
        _gzip_file(raw_backup, gz_backup)
        raw_backup.unlink()
    except Exception as e:
        logger.error("Failed to compress backup %s: %s", raw_backup, e)
        raw_backup.unlink(missing_ok=True)
        return None

    size_mb = gz_backup.stat().st_size / (1024 * 1024)
    logger.info("Backup created: %s (%.2f MB)", gz_backup.name, size_mb)

    # Step 3: Apply rolling retention.
    _apply_rolling_retention(out_dir)

    return gz_backup


def add_backup_jobs(scheduler) -> None:
    """Register the daily backup job on the given APScheduler instance.

    The backup runs daily at 02:00 (low-traffic hour).  The scheduler must
    already be started (or about to be started).
    """
    from config import settings

    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    backup_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "..",
        "data",
        "backups",
    )
    backup_dir = os.path.normpath(backup_dir)

    scheduler.add_job(
        backup_database,
        "cron",
        hour=2,
        minute=0,
        id="daily_db_backup",
        replace_existing=True,
        max_instances=1,
        kwargs={"db_path": db_path, "backup_dir": backup_dir},
    )
    logger.info("Registered daily database backup job (02:00) -> %s", backup_dir)
