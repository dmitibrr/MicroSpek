"""Common helpers: value cleaning, formatting and safe PowerShell calls."""

from __future__ import annotations

import json
import locale
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

NA = "—"

# PowerShell 5.1 пишет в консоль в OEM-кодировке (на русской Windows — cp866),
# поэтому любой вывод нужно явно переводить в UTF-8 до декодирования в Python.
_PS_UTF8_PREFIX = "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "


def clean(value: Any, default: str = NA) -> str:
    """Convert any value to a compact human-readable string."""
    if value is None:
        return default
    if isinstance(value, bool):
        return "да" if value else "нет"
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.2f}".rstrip("0").rstrip(".").replace(".", ",")
    if isinstance(value, (list, tuple, set)):
        parts = [clean(item, "") for item in value]
        parts = [part for part in parts if part and part != default]
        return ", ".join(parts) if parts else default
    text = str(value).strip()
    if not text:
        return default
    return " ".join(text.split())


def first(*values: Any, default: str = NA) -> str:
    """First non-empty value."""
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return clean(value, default)
    return default


def format_bytes(value: Any, decimal: bool = False) -> str:
    """Format a byte count in binary units."""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return NA
    if amount < 0:
        return NA
    units = ("Б", "КиБ", "МиБ", "ГиБ", "ТиБ", "ПиБ")
    index = 0
    while amount >= 1024 and index < len(units) - 1:
        amount /= 1024
        index += 1
    if index == 0:
        return f"{int(amount)} {units[index]}"
    precision = 2 if amount < 10 else 1
    text = f"{amount:.{precision}f}".replace(".", ",")
    suffix = "Б" if decimal else units[index]
    return f"{text} {suffix}" if decimal else f"{text} {units[index]}"


def format_mhz(value: Any) -> str:
    try:
        mhz = float(value)
    except (TypeError, ValueError):
        return NA
    if mhz <= 0:
        return NA
    if mhz >= 1000:
        return f"{mhz / 1000:.2f} ГГц".replace(".", ",")
    return f"{mhz:.0f} МГц"


def format_temp(value: Any) -> str:
    try:
        temp = float(value)
    except (TypeError, ValueError):
        return NA
    return f"{temp:.0f} °C"


def format_fan(value: Any) -> str:
    try:
        rpm = float(value)
    except (TypeError, ValueError):
        return NA
    if rpm <= 0:
        return NA
    return f"{rpm:.0f} об/мин"


def format_watts(value: Any) -> str:
    try:
        watts = float(value)
    except (TypeError, ValueError):
        return NA
    if watts <= 0:
        return NA
    precision = 0 if watts >= 100 else 1
    return f"{watts:.{precision}f} Вт".replace(".", ",")


def format_volts(value: Any) -> str:
    try:
        volts = float(value)
    except (TypeError, ValueError):
        return NA
    if volts <= 0:
        return NA
    return f"{volts:.2f} В".replace(".", ",")


def is_admin() -> bool:
    """True when the current process runs elevated (Windows only)."""
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def format_percent(value: Any) -> str:
    try:
        percent = float(value)
    except (TypeError, ValueError):
        return NA
    return f"{percent:.0f}%"


def format_duration(seconds: Any) -> str:
    try:
        total = max(0, int(float(seconds)))
    except (TypeError, ValueError):
        return NA
    days, total = divmod(total, 86400)
    hours, total = divmod(total, 3600)
    minutes, _ = divmod(total, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days} д")
    if hours or days:
        parts.append(f"{hours} ч")
    parts.append(f"{minutes} мин")
    return " ".join(parts)


def _ps_arguments(script: str) -> list[str]:
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-NoLogo",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        _PS_UTF8_PREFIX + script,
    ]


def run_powershell(script: str, timeout: float = 45.0) -> subprocess.CompletedProcess[str] | None:
    """Run a PowerShell snippet, returning None if it fails or PS is missing."""
    try:
        return subprocess.run(
            _ps_arguments(script),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def ps_json(script: str, timeout: float = 45.0) -> Any:
    """Run a PowerShell snippet that prints JSON and parse the result."""
    completed = run_powershell(script, timeout)
    if completed is None or completed.returncode != 0 or not completed.stdout.strip():
        return None
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None


def ps_table(script: str, timeout: float = 45.0) -> list[dict[str, str]]:
    """Run a PowerShell snippet that prints `key: value` blocks.

    Blocks are separated by blank lines. Useful for mixed reports.
    """
    completed = run_powershell(script, timeout)
    if completed is None or not completed.stdout.strip():
        return []
    rows: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            if current:
                rows.append(current)
                current = {}
            continue
        if ":" in stripped:
            key, _, value = stripped.partition(":")
            current[key.strip()] = value.strip()
    if current:
        rows.append(current)
    return rows


def command_output(command: str, args: list[str], timeout: float = 15.0) -> str | None:
    """Run an external command, return stdout or None."""
    try:
        exe = _resolve(command)
        if exe is None:
            return None
        completed = subprocess.run(
            [exe, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if completed.returncode != 0 and not completed.stdout.strip():
            return None
        return completed.stdout
    except (OSError, subprocess.TimeoutExpired):
        return None


def _resolve(command: str) -> str | None:
    from shutil import which

    found = which(command)
    if found:
        return found
    system_root = Path(__import__("os").environ.get("SystemRoot", r"C:\Windows"))
    candidate = system_root / "System32" / f"{command}.exe"
    if candidate.exists():
        return str(candidate)
    return None


def temp_dir() -> Path:
    return Path(tempfile.gettempdir())


def console_encoding() -> str:
    try:
        return locale.getpreferredencoding(False) or "utf-8"
    except Exception:
        return "utf-8"


def parse_wmi_date(value: Any) -> datetime | None:
    """Parse CIM datetime values like ``/Date(1795002254769)/``."""
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    match = re.search(r"/Date\((-?\d+)", value)
    if match:
        try:
            return datetime.fromtimestamp(int(match.group(1)) / 1000.0)
        except (OSError, OverflowError, ValueError):
            return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def format_date(value: Any) -> str:
    parsed = parse_wmi_date(value)
    return parsed.strftime("%d.%m.%Y %H:%M") if parsed else NA
