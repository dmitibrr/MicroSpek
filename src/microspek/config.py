"""Configuration file support (``microspek.json``).

The lightweight snapshot edition is meant to be embedded into other tools, so
every option can come from a small JSON file next to the executable instead of
command-line flags::

    {
      "output": "md",
      "file": "reports/pc.md",
      "redact": true,
      "sections": ["os", "cpu", "memory", "storage", "gpu"],
      "sensors": true,
      "dxdiag": false,
      "admin_sensors": false,
      "lang": "en",
      "open": false,
      "quiet": false
    }
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .snapshot import normalize_sections

OUTPUT_FORMATS = ("txt", "json", "md")
CONFIG_NAME = "microspek.json"


class ConfigError(RuntimeError):
    """Raised when the configuration file cannot be used."""


@dataclass(slots=True)
class Settings:
    output: str = "txt"
    file: str | None = None
    redact: bool = False
    sections: list[str] | None = None
    sensors: bool = True
    dxdiag: bool = False
    admin_sensors: bool = False
    lang: str | None = None
    open_file: bool = False
    quiet: bool = False
    stdout: bool = False
    values: dict[str, Any] = field(default_factory=dict)


def _as_bool(value: Any, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on", "да")
    if isinstance(value, (int, float)):
        return bool(value)
    return fallback


def _as_output(value: Any, fallback: str) -> str:
    text = str(value or "").strip().lower().lstrip(".")
    if text == "markdown":
        text = "md"
    return text if text in OUTPUT_FORMATS else fallback


def _as_sections(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        if value.strip().lower() in ("", "all", "everything", "*"):
            return None
        return normalize_sections(value)
    if isinstance(value, (list, tuple, set)):
        cleaned = [str(item) for item in value if str(item).strip()]
        return normalize_sections(cleaned) if cleaned else None
    return None


def find_config(explicit: str | Path | None = None) -> Path | None:
    """Locate the config: explicit path, current directory, then exe folder."""
    if explicit:
        path = Path(explicit)
        return path if path.is_file() else None
    candidates = [Path.cwd() / CONFIG_NAME]
    if getattr(sys, "frozen", False):
        candidates.insert(0, Path(sys.executable).resolve().parent / CONFIG_NAME)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def load_config(
    path: str | Path | None = None,
    defaults: Settings | None = None,
) -> Settings:
    """Read a JSON config, ignoring unknown keys and bad types."""
    settings = defaults or Settings()
    explicit = path
    found = find_config(explicit)
    if found is None:
        if explicit:
            raise ConfigError(f"config file not found: {explicit}")
        return settings

    try:
        raw = json.loads(found.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"{found}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"{found}: the top-level value must be an object")

    settings.values = {str(key): value for key, value in raw.items()}
    settings.output = _as_output(raw.get("output"), settings.output)
    file_value = raw.get("file")
    settings.file = str(file_value) if file_value else settings.file
    settings.redact = _as_bool(raw.get("redact"), settings.redact)
    if "sections" in raw:
        settings.sections = _as_sections(raw.get("sections"))
    settings.sensors = _as_bool(raw.get("sensors"), settings.sensors)
    settings.dxdiag = _as_bool(raw.get("dxdiag"), settings.dxdiag)
    settings.admin_sensors = _as_bool(
        raw.get("admin_sensors", raw.get("admin")), settings.admin_sensors
    )
    lang = raw.get("lang", raw.get("language"))
    if isinstance(lang, str) and lang.strip().lower() in ("ru", "en"):
        settings.lang = lang.strip().lower()
    settings.open_file = _as_bool(raw.get("open", raw.get("open_file")), settings.open_file)
    settings.quiet = _as_bool(raw.get("quiet"), settings.quiet)
    settings.stdout = _as_bool(raw.get("stdout"), settings.stdout)
    return settings


def config_dir(path: str | Path | None) -> Path:
    """Directory that relative ``file`` paths are resolved against."""
    found = find_config(path)
    if found is not None:
        return found.parent
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


EXAMPLE = {
    "output": "md",
    "file": "snapshot.md",
    "redact": True,
    "sections": ["os", "cpu", "memory", "storage", "gpu"],
    "sensors": True,
    "dxdiag": False,
    "admin_sensors": False,
    "lang": "en",
    "open": False,
    "quiet": False,
}


def write_example(path: str | Path, **overrides: Any) -> Path:
    data = dict(EXAMPLE)
    data.update(overrides)
    target = Path(path)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target
