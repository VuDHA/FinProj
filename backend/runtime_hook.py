"""Runtime hook executed by the PyInstaller-frozen backend before main.py.

When the backend is launched as a Tauri sidecar, the working directory and
module layout differ from a normal `python main.py` invocation. This hook:

1. Determines the correct data directory.
   - If the env var ``WEALTH_DATA_DIR`` is set (Tauri passes it), use that.
   - Otherwise fall back to ``<project_root>/data`` (dev mode).
2. Creates the data directory if it does not exist.
3. Sets ``DATABASE_URL`` so config.py picks up the right SQLite path.
4. Adjusts ``sys.path`` so bundled modules can be imported.
"""

import os
import sys


def _resolve_data_dir() -> str:
    """Return the absolute path to the directory holding wealth.db."""
    # Tauri sidecar: the launcher sets WEALTH_DATA_DIR to the app config dir.
    env_data_dir = os.environ.get("WEALTH_DATA_DIR")
    if env_data_dir:
        return os.path.abspath(env_data_dir)

    # Frozen but no env var (e.g. double-clicked): use a user-level dir.
    if getattr(sys, "frozen", False):
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(base, "wealth-vn", "data")

    # Dev mode: use the project-level data folder.
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, "data")


def main() -> None:
    data_dir = _resolve_data_dir()
    os.makedirs(data_dir, exist_ok=True)

    # Make the data directory discoverable by config.py via env var.
    db_path = os.path.join(data_dir, "wealth.db")
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")
    # Also expose the data dir for any module that reads it directly.
    os.environ.setdefault("WEALTH_DATA_DIR", data_dir)

    # When frozen, sys._MEIPASS is the temp extraction folder. Ensure it is
    # on sys.path so hidden imports / data files resolve correctly.
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass and meipass not in sys.path:
        sys.path.insert(0, meipass)

    # Change the working directory to the data folder so relative paths in
    # logs/backups land in the right place.
    try:
        os.chdir(data_dir)
    except OSError:
        pass


main()
