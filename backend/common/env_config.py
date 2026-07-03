import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from common.config import settings


_ENV_PATH = Path(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))


# Metadata describing the env variables exposed to the frontend.
# Order matters: items are displayed in this order.
ENV_REGISTRY: List[Dict[str, Any]] = [
    {"key": "DATABASE_URL", "type": "str", "requires_restart": True, "description": "SQLite database URL"},
    {"key": "API_PREFIX", "type": "str", "requires_restart": True, "description": "REST API prefix"},
    {"key": "CORS_ORIGINS", "type": "list", "requires_restart": True, "description": "Allowed CORS origins (JSON array)"},
    {"key": "SCHEDULER_HOUR", "type": "int", "requires_restart": True, "description": "Hour to run scheduled price/news jobs (0-23)"},
    {"key": "SCHEDULER_MINUTE", "type": "int", "requires_restart": True, "description": "Minute to run scheduled jobs (0-59)"},
    {"key": "AI_PROVIDER", "type": "str", "requires_restart": False, "description": "AI provider: gemini or ollama"},
    {"key": "AI_BATCH_SIZE", "type": "int", "requires_restart": False, "description": "Number of tasks to send in one Gemini batch"},
    {"key": "AI_TIMEOUT_SECONDS", "type": "int", "requires_restart": False, "description": "Timeout per AI call (seconds)"},
    {"key": "GEMINI_API_KEY", "type": "str", "requires_restart": False, "description": "Google Gemini API key"},
    {"key": "GEMINI_BASE_URL", "type": "str", "requires_restart": False, "description": "Gemini API base URL"},
    {"key": "GEMINI_MODEL", "type": "str", "requires_restart": False, "description": "Gemini generation model name"},
    {"key": "GEMINI_EMBEDDING_MODEL", "type": "str", "requires_restart": False, "description": "Gemini embedding model name"},
    {"key": "GEMINI_EMBEDDING_DIMENSION", "type": "int", "requires_restart": False, "description": "Gemini embedding vector dimension"},
    {"key": "NEWS_RELEVANCE_THRESHOLD", "type": "float", "requires_restart": False, "description": "Minimum relevance score to save a news article"},
    {"key": "OLLAMA_ENABLED", "type": "bool", "requires_restart": False, "description": "Enable local Ollama LLM for AI features"},
    {"key": "OLLAMA_BASE_URL", "type": "str", "requires_restart": False, "description": "Ollama server URL"},
    {"key": "OLLAMA_MODEL", "type": "str", "requires_restart": False, "description": "Ollama model name for generation"},
    {"key": "OLLAMA_TIMEOUT", "type": "int", "requires_restart": False, "description": "Timeout per Ollama generation call (seconds)"},
    {"key": "OLLAMA_MAX_TAGS", "type": "int", "requires_restart": False, "description": "Max tags generated per article"},
    {"key": "OLLAMA_NUM_THREADS", "type": "int", "requires_restart": False, "description": "CPU threads for Ollama inference (0 = auto)"},
    {"key": "OLLAMA_KEEP_ALIVE", "type": "str", "requires_restart": False, "description": "How long Ollama keeps the model loaded (e.g. 15m, -1)"},
    {"key": "OLLAMA_NUM_PARALLEL", "type": "int", "requires_restart": False, "description": "Parallel requests per Ollama model (CPU tuning)"},
    {"key": "OLLAMA_MAX_LOADED_MODELS", "type": "int", "requires_restart": False, "description": "Max models loaded in Ollama at once (CPU tuning)"},
    {"key": "OLLAMA_AI_QUEUE_TIMEOUT_SECONDS", "type": "int", "requires_restart": False, "description": "Global AI queue timeout (seconds)"},
    {"key": "OLLAMA_EMBEDDING_ENABLED", "type": "bool", "requires_restart": False, "description": "Enable Ollama embeddings for RAG"},
    {"key": "OLLAMA_EMBEDDING_MODEL", "type": "str", "requires_restart": False, "description": "Ollama embedding model name"},
    {"key": "OLLAMA_EMBEDDING_DIMENSION", "type": "int", "requires_restart": False, "description": "Embedding vector dimension"},
]


_REGISTRY_KEYS = {entry["key"] for entry in ENV_REGISTRY}


def _load_env_file() -> Dict[str, str]:
    """Parse the .env file into a key-value dictionary."""
    result: Dict[str, str] = {}
    if not _ENV_PATH.exists():
        return result
    for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        result[key.strip()] = value.strip()
    return result


def _serialize_value(value: Any, var_type: str) -> str:
    """Convert a runtime value into the .env string representation."""
    if var_type == "bool":
        return "true" if value else "false"
    if var_type == "list":
        if isinstance(value, list):
            return str(value).replace("'", '"')
        return str(value)
    return str(value)


def _parse_value(raw: str, var_type: str) -> Any:
    """Parse a string from the .env file into the correct Python type."""
    if var_type == "bool":
        return raw.lower() in ("true", "1", "yes", "on")
    if var_type == "int":
        try:
            return int(raw)
        except ValueError:
            return 0
    if var_type == "float":
        try:
            return float(raw)
        except ValueError:
            return 0.0
    if var_type == "list":
        import json

        try:
            return json.loads(raw)
        except Exception:
            return [item.strip() for item in raw.split(",") if item.strip()]
    return raw


def get_env_config() -> List[Dict[str, Any]]:
    """Return the current env configuration for all registered variables."""
    env_values = _load_env_file()
    result = []
    for meta in ENV_REGISTRY:
        key = meta["key"]
        raw = env_values.get(key)
        if raw is None:
            # Fallback to runtime setting default value.
            raw = _serialize_value(getattr(settings, key), meta["type"])
        result.append({
            "key": key,
            "value": raw,
            "type": meta["type"],
            "requires_restart": meta["requires_restart"],
            "description": meta["description"],
        })
    return result


def _validate_updates(updates: Dict[str, str]) -> Tuple[Dict[str, str], List[str]]:
    """Validate and normalize the incoming updates. Returns (valid, errors)."""
    import json

    errors: List[str] = []
    valid: Dict[str, str] = {}
    for meta in ENV_REGISTRY:
        key = meta["key"]
        if key not in updates:
            continue
        raw = str(updates[key]).strip()
        try:
            if meta["type"] == "int":
                int(raw)
            elif meta["type"] == "float":
                float(raw)
            elif meta["type"] == "list":
                json.loads(raw)
        except ValueError as exc:
            if meta["type"] == "list":
                errors.append(f"{key} must be a valid JSON array")
            elif meta["type"] == "float":
                errors.append(f"{key} must be a valid number")
            else:
                errors.append(f"{key} must be a valid integer")
        else:
            valid[key] = raw

    unknown = set(updates.keys()) - _REGISTRY_KEYS
    if unknown:
        errors.append(f"Unknown keys: {', '.join(sorted(unknown))}")
    return valid, errors


def update_env_config(updates: Dict[str, str]) -> Dict[str, Any]:
    """Apply validated updates to the .env file and the runtime settings object."""
    valid, errors = _validate_updates(updates)
    if errors:
        raise ValueError("; ".join(errors))

    env_values = _load_env_file()
    env_values.update(valid)

    # Preserve existing comments and order by rewriting the file.
    lines: List[str] = []
    if _ENV_PATH.exists():
        for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                lines.append(line)
                continue
            key = stripped.split("=", 1)[0].strip()
            if key in env_values:
                lines.append(f"{key}={env_values[key]}")
                del env_values[key]
            else:
                lines.append(line)
    # Append any remaining keys.
    for key, value in env_values.items():
        lines.append(f"{key}={value}")

    _ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Update runtime settings for values that can take effect immediately.
    changed = []
    for meta in ENV_REGISTRY:
        key = meta["key"]
        if key not in valid:
            continue
        parsed = _parse_value(valid[key], meta["type"])
        setattr(settings, key, parsed)
        changed.append({
            "key": key,
            "value": valid[key],
            "type": meta["type"],
            "requires_restart": meta["requires_restart"],
            "description": meta["description"],
        })

    return {"changed": changed, "requires_restart": any(c["requires_restart"] for c in changed)}
