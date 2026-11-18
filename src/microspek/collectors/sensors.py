"""Hardware sensors (temperatures, fans, voltages, power) via LibreHardwareMonitorLib.

The heavy lifting lives in ``MicroSpekSensors.exe`` (C#, .NET Framework 4.8),
which is built by ``scripts/build_sensors.py``. It runs once per snapshot and
prints a small JSON tree. Elevation is optional: disk SMART and GPU sensors work
without it, CPU MSR / SuperIO sensors need the PawnIO driver and admin rights.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from ..util import NA, is_admin

HELPER_NAME = "MicroSpekSensors.exe"
HELPER_TIMEOUT = 40.0
UAC_TIMEOUT = 30.0

# LibreHardwareMonitor sensor names -> Russian labels.
NAME_RU = {
    "CPU Package": "Пакет CPU",
    "CPU Cores": "Ядра CPU",
    "CPU Core Max": "Максимум по ядрам",
    "CPU Core": "Ядро CPU",
    "CPU Total": "Всего CPU",
    "CPU Core Voltage": "Напряжение ядра CPU",
    "GPU Core": "Ядро GPU",
    "GPU Hot Spot": "Горячая точка GPU",
    "GPU Memory": "Память GPU",
    "GPU Memory Junction": "Память GPU (junction)",
    "GPU Fan": "Вентилятор GPU",
    "GPU Package": "Пакет GPU",
    "GPU Board Power": "Плата GPU",
    "GPU Power": "Мощность GPU",
    "GPU Core Voltage": "Напряжение ядра GPU",
    "GPU Memory Total": "Память GPU всего",
    "GPU Memory Used": "Память GPU занято",
    "GPU Memory Free": "Память GPU свободно",
    "Temperature": "Температура",
    "Remaining Life": "Остаток ресурса",
    "Total Host Writes": "Записано всего",
    "Total Host Reads": "Прочитано всего",
    "Power On Hours": "Наработка",
    "Power Cycle Count": "Циклов включения",
    "Used Space": "Занято",
    "Free Space": "Свободно",
    "Life": "Ресурс",
}

_CPU_CORE = re.compile(r"^(?:CPU )?Core #(\d+)$")
_FAN = re.compile(r"^Fan #(\d+)$")

_lock = threading.Lock()
_started = False
_event = threading.Event()
_payload: dict[str, Any] | None = None
_error: str | None = None
_elevated = False


def helper_path() -> Path | None:
    """Locate MicroSpekSensors.exe next to the app or in the build folder."""
    override = os.environ.get("MICROSPEK_SENSORS")
    if override:
        candidate = Path(override)
        if candidate.is_file():
            return candidate
        if (candidate / HELPER_NAME).is_file():
            return candidate / HELPER_NAME

    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
        candidates.append(base / "sensors" / HELPER_NAME)
        bundle = getattr(sys, "_MEIPASS", None)
        if bundle:
            candidates.append(Path(bundle) / "sensors" / HELPER_NAME)

    root = Path(__file__).resolve().parents[3]
    candidates.append(root / "build" / "sensors" / HELPER_NAME)

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def available() -> bool:
    return helper_path() is not None


def ru_name(name: str) -> str:
    """Translate common LibreHardwareMonitor sensor names."""
    if name in NAME_RU:
        return NAME_RU[name]
    match = _CPU_CORE.match(name)
    if match:
        return f"Ядро {match.group(1)}"
    match = _FAN.match(name)
    if match:
        return f"Вентилятор {match.group(1)}"
    return name


@dataclass
class Reading:
    kind: str
    name: str
    value: float
    minimum: float | None = None
    maximum: float | None = None


@dataclass
class Device:
    name: str
    kind: str
    identifier: str = ""
    sensors: list[Reading] = field(default_factory=list)
    children: list["Device"] = field(default_factory=list)

    def walk(self) -> Iterable["Device"]:
        yield self
        for child in self.children:
            yield from child.walk()

    def readings(self, *kinds: str) -> list[Reading]:
        return [reading for reading in self.sensors if not kinds or reading.kind in kinds]

    def reading(self, name: str) -> Reading | None:
        for reading in self.sensors:
            if reading.name == name:
                return reading
        return None

    def find_reading(self, name: str) -> Reading | None:
        """Look for a named sensor in this device and its children."""
        for device in self.walk():
            for reading in device.sensors:
                if reading.name == name:
                    return reading
        return None


class Sensors:
    """Parsed sensor tree with lookups used by the collectors."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.devices: list[Device] = [
            _parse_device(item) for item in payload.get("hardware") or []
        ]
        self.error = payload.get("error")

    @property
    def ok(self) -> bool:
        return bool(self.payload.get("ok")) and bool(self.devices)

    def by_kind(self, *kinds: str) -> list[Device]:
        wanted = {kind.lower() for kind in kinds}
        result: list[Device] = []
        for device in self.devices:
            result.extend(item for item in device.walk() if item.kind.lower() in wanted)
        return result

    def cpu(self) -> Device | None:
        devices = self.by_kind("Cpu")
        return devices[0] if devices else None

    def gpu(self, name: str = "") -> Device | None:
        devices = self.by_kind("GpuNvidia", "GpuAmd", "GpuIntel", "Gpu")
        if not devices:
            return None
        if name:
            target = _normalize(name)
            for device in devices:
                current = _normalize(device.name)
                if current and (current == target or target in current or current in target):
                    return device
        # A single physical GPU may be reported under a slightly different name.
        return devices[0] if len(devices) == 1 else None

    def storage(self, model: str = "", serial: str = "") -> Device | None:
        devices = self.by_kind("Storage")
        if not devices:
            return None
        if model:
            target = _normalize(model)
            for device in devices:
                current = _normalize(device.name)
                if current and (current == target or target in current or current in target):
                    return device
        return None

    def motherboard(self) -> Device | None:
        devices = self.by_kind("Motherboard", "SuperIO")
        for device in devices:
            if any(reading.kind in ("Fan", "Voltage", "Temperature") for reading in device.sensors):
                return device
        return devices[0] if devices else None

    def all_readings(self, *kinds: str) -> list[Reading]:
        result: list[Reading] = []
        for device in self.devices:
            for item in device.walk():
                result.extend(item.readings(*kinds))
        return result

    @property
    def elevated(self) -> bool:
        return _elevated


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(text or "").lower())


def _parse_device(raw: dict[str, Any]) -> Device:
    sensors = []
    for item in raw.get("sensors") or []:
        value = item.get("value")
        if value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        sensors.append(
            Reading(
                kind=str(item.get("type") or ""),
                name=str(item.get("name") or ""),
                value=number,
                minimum=_float(item.get("min")),
                maximum=_float(item.get("max")),
            )
        )
    return Device(
        name=str(raw.get("name") or ""),
        kind=str(raw.get("type") or ""),
        identifier=str(raw.get("identifier") or ""),
        sensors=sensors,
        children=[_parse_device(child) for child in raw.get("children") or []],
    )


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _ps_quote(text: str) -> str:
    return "'" + str(text).replace("'", "''") + "'"


def _run_direct(path: Path) -> dict[str, Any] | None:
    try:
        completed = subprocess.run(
            [str(path)],
            capture_output=True,
            timeout=HELPER_TIMEOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return _parse_output(completed.stdout)


def _run_elevated(path: Path) -> dict[str, Any] | None:
    """Run the helper through UAC; returns None if the user declines."""
    handle, name = tempfile.mkstemp(prefix="microspek-sensors-", suffix=".json")
    os.close(handle)
    target = Path(name)
    try:
        script = (
            f"$p = Start-Process -FilePath {_ps_quote(str(path))} "
            f"-ArgumentList @('--out', {_ps_quote(str(target))}) "
            "-Verb RunAs -PassThru -WindowStyle Hidden; "
            f"if (-not $p.WaitForExit({int(UAC_TIMEOUT * 1000)})) {{ exit 3 }}; "
            "exit $p.ExitCode"
        )
        try:
            subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-NoLogo",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    script,
                ],
                capture_output=True,
                timeout=UAC_TIMEOUT + 15,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        try:
            text = target.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
        return _parse_output(text.encode("utf-8"))
    finally:
        try:
            target.unlink()
        except OSError:
            pass


def _parse_output(raw: bytes) -> dict[str, Any] | None:
    text = raw.decode("utf-8", "replace").strip()
    if not text:
        return None
    start = text.find("{")
    if start < 0:
        return None
    try:
        data = json.loads(text[start:])
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def _worker(elevate: bool) -> None:
    global _payload, _error, _elevated
    path = helper_path()
    if path is None:
        _error = "helper не найден"
        _event.set()
        return
    data: dict[str, Any] | None = None
    if elevate and not is_admin():
        print(
            "Запрашиваю права администратора для температур и SMART…",
            file=sys.stderr,
            flush=True,
        )
        data = _run_elevated(path)
        if data is not None:
            _elevated = True
    if data is None:
        data = _run_direct(path)
    if data is None:
        _error = "не удалось запустить сбор датчиков"
    else:
        _error = data.get("error") if not data.get("ok") else None
    _payload = data
    _event.set()


def begin(elevate: bool = False) -> None:
    """Start sensor collection in the background (idempotent)."""
    global _started
    with _lock:
        if _started:
            return
        _started = True
        threading.Thread(
            target=_worker,
            args=(elevate,),
            name="microspek-sensors",
            daemon=True,
        ).start()


def reset() -> None:
    """Forget cached sensors so the next begin() collects them again."""
    global _started, _payload, _error, _elevated
    with _lock:
        _started = False
        _payload = None
        _error = None
        _elevated = False
        _event.clear()


def data(timeout: float = HELPER_TIMEOUT + UAC_TIMEOUT + 5) -> Sensors | None:
    """Wait for the background collection and return the parsed tree."""
    begin()
    _event.wait(timeout)
    if _payload is None:
        return None
    return Sensors(_payload)


def error() -> str | None:
    return _error


def status_note() -> str:
    """Short human-readable status for the GUI/CLI."""
    if helper_path() is None:
        return "Датчики недоступны: не найден MicroSpekSensors.exe"
    if not _event.is_set():
        return "Датчики собираются…"
    if _payload is None:
        return "Датчики недоступны: " + (_error or "ошибка запуска")
    sensors = Sensors(_payload)
    if not sensors.ok:
        return "Датчики недоступны: " + (sensors.error or "ошибка")
    temperatures = sensors.all_readings("Temperature")
    storage = len(sensors.by_kind("Storage"))
    cpu = sensors.cpu()
    cpu_temps = bool(cpu and cpu.readings("Temperature"))
    if not temperatures:
        suffix = "" if is_admin() else " (нужен запуск от администратора)"
        return f"Датчики: без температур{suffix}"
    text = f"Датчики: {len(temperatures)} температур, дисков SMART: {storage}"
    if not cpu_temps:
        text += ", CPU — нужен PawnIO"
    elif _elevated:
        text += ", с правами администратора"
    return text
