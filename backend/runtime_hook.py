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


def _seed_default_env(data_dir: str) -> None:
    """Create a default .env in the data dir on first run.

    The bundled sidecar has no .env, so without this the app would start with
    empty GEMINI_API_KEY and the news scheduler enabled but unable to tag
    articles. We seed a minimal .env that users can later edit via the
    Settings UI (env-config API).
    """
    env_path = os.path.join(data_dir, ".env")
    if os.path.exists(env_path):
        return
    defaults = {
        "AI_PROVIDER": "gemini",
        "GEMINI_API_KEY": "",
        "NEWS_SCHEDULER_ENABLED": "true",
        "OLLAMA_ENABLED": "false",
        "DEBUG": "false",
    }
    lines = ["# Wealth VN runtime configuration", ""]
    lines += [f"{k}={v}" for k, v in defaults.items()]
    lines.append("")
    try:
        with open(env_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
    except OSError:
        pass


def main() -> None:
    data_dir = _resolve_data_dir()
    os.makedirs(data_dir, exist_ok=True)

    # Make the data directory discoverable by config.py via env var.
    db_path = os.path.join(data_dir, "wealth.db")
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")
    # Also expose the data dir for any module that reads it directly.
    os.environ.setdefault("WEALTH_DATA_DIR", data_dir)

    # Seed a default writable .env so users can configure API keys via the
    # Settings UI without rebuilding the app.
    _seed_default_env(data_dir)

    # When frozen, sys._MEIPASS is the temp extraction folder. Ensure it is
    # on sys.path so hidden imports / data files resolve correctly.
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass and meipass not in sys.path:
        sys.path.insert(0, meipass)

    # Point SSL-related libraries to the bundled CA certificates so that
    # HTTPS requests via `requests` / `urllib3` work inside the frozen exe.
    # `certifi` ships cacert.pem which PyInstaller bundles into _MEIPASS.
    if meipass:
        import os as _os
        for _candidate in (
            _os.path.join(meipass, "certifi", "cacert.pem"),
            _os.path.join(meipass, "cacert.pem"),
        ):
            if _os.path.isfile(_candidate):
                _os.environ.setdefault("REQUESTS_CA_BUNDLE", _candidate)
                _os.environ.setdefault("SSL_CERT_FILE", _candidate)
                break

    # Change the working directory to the data folder so relative paths in
    # logs/backups land in the right place.
    try:
        os.chdir(data_dir)
    except OSError:
        pass


main()
