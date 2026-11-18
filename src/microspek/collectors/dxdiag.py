"""Run dxdiag.exe and parse its text report for display and sound info."""

from __future__ import annotations

import re
import subprocess
import tempfile
import uuid
from pathlib import Path

from ..models import Group, Item, Section
from ..util import first

DISPLAY_KEYS = {
    "Manufacturer": "manufacturer",
    "Chip type": "chip",
    "DAC type": "dac",
    "Device Type": "device_type",
    "Device Key": "device_key",
    "Device Status": "status",
    "Display Memory": "display_memory",
    "Dedicated Memory": "dedicated_memory",
    "Shared Memory": "shared_memory",
    "Current Mode": "mode",
    "Native Mode": "native_mode",
    "Monitor Name": "monitor_name",
    "Monitor Model": "monitor_model",
    "Monitor Id": "monitor_id",
    "Output Type": "output_type",
    "Driver Version": "driver_version",
    "Driver Date/Size": "driver_date",
    "Driver Model": "driver_model",
    "Feature Levels": "feature_levels",
    "DDI Version": "ddi",
}

SOUND_KEYS = {
    "Device ID": "device_id",
    "Default Sound Playback": "default_playback",
    "Default Voice Playback": "default_voice",
}


def build_dxdiag_report(timeout: float = 60.0) -> dict | None:
    """Run dxdiag.exe, wait for its text report and parse it."""
    temp = Path(tempfile.gettempdir()) / f"ms-dxdiag-{uuid.uuid4().hex}.txt"
    try:
        try:
            subprocess.Popen(
                ["dxdiag", "/whql:off", "/t", str(temp)],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except OSError:
            return None
        import time

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if temp.exists() and temp.stat().st_size > 0:
                try:
                    if _looks_complete(temp.read_text(encoding="utf-8", errors="replace")):
                        break
                except OSError:
                    pass
            time.sleep(0.4)
        else:
            return None
        try:
            lines = temp.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return None
        if not _looks_complete("\n".join(lines)):
            return None
        return parse_dxdiag_text(lines)
    finally:
        try:
            temp.unlink()
        except OSError:
            pass


def _looks_complete(text: str) -> bool:
    return "DxDiag Notes" in text or "Display Devices" in text


def _split_value(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or ":" not in stripped:
        return None
    key, _, value = stripped.partition(":")
    key = key.strip()
    value = value.strip()
    if not key or len(key) > 40:
        return None
    return key, value


def parse_dxdiag_text(lines: list[str]) -> dict:
    result: dict = {"system": {}, "displays": [], "sound": []}
    display: dict | None = None
    sound: dict | None = None
    for raw in lines:
        pair = _split_value(raw)
        if pair is None:
            continue
        key, value = pair
        if key == "Card name":
            display = {"name": value}
            result["displays"].append(display)
            continue
        if key == "Description" and raw.lstrip().startswith("Description"):
            sound = {"name": value}
            result["sound"].append(sound)
            continue
        target = display if display is not None else None
        if target is not None and key in DISPLAY_KEYS:
            target[DISPLAY_KEYS[key]] = value
            continue
        if sound is not None and key in SOUND_KEYS:
            sound[SOUND_KEYS[key]] = value
            continue
        if key == "Operating System":
            result["system"]["os"] = value
        elif key == "System Manufacturer":
            result["system"]["manufacturer"] = value
        elif key == "System Model":
            result["system"]["model"] = value
        elif key == "BIOS":
            result["system"]["bios"] = value
        elif key == "Memory":
            result["system"]["memory"] = value
        elif key == "DirectX Version":
            result["system"]["directx"] = value
        elif key == "Page File":
            result["system"]["page_file"] = value
    return result


DISPLAY_LABELS = {
    "manufacturer": "Производитель",
    "chip": "Чип / GPU",
    "dac": "DAC",
    "device_type": "Тип устройства",
    "device_key": "Ключ устройства",
    "status": "Статус",
    "display_memory": "Память (всего)",
    "dedicated_memory": "Выделенная память",
    "shared_memory": "Общая память",
    "mode": "Текущий режим",
    "native_mode": "Родной режим",
    "monitor_name": "Монитор",
    "monitor_model": "Модель монитора",
    "monitor_id": "ID монитора",
    "output_type": "Тип выхода",
    "driver_version": "Версия драйвера",
    "driver_date": "Дата / размер драйвера",
    "driver_model": "Модель драйвера",
    "feature_levels": "Уровни функций",
    "ddi": "Версия DDI",
}

SOUND_LABELS = {
    "device_id": "ID устройства",
    "default_playback": "Воспроизведение по умолчанию",
    "default_voice": "Голос по умолчанию",
}

SYSTEM_LABELS = {
    "os": "Операционная система",
    "manufacturer": "Производитель",
    "model": "Модель",
    "bios": "BIOS",
    "memory": "Память",
    "directx": "Версия DirectX",
    "page_file": "Файл подкачки",
}


def collect_dxdiag(timeout: float = 60.0) -> Section:
    """Run dxdiag and turn its report into a Section (never raises)."""
    report = build_dxdiag_report(timeout)
    if report is None:
        return Section(
            "dxdiag",
            "DirectX (dxdiag)",
            [Group("Статус", [Item("Результат", "не удалось получить отчёт dxdiag")])],
            [],
        )
    groups: list[Group] = []
    summary: list[Item] = []
    system = report.get("system") or {}
    if system:
        items = [
            Item(SYSTEM_LABELS.get(key, key), value)
            for key, value in system.items()
            if value
        ]
        groups.append(Group("Система (по dxdiag)", items))
        summary.append(Item("DirectX", first(system.get("directx"))))
    for index, display in enumerate(report.get("displays") or [], start=1):
        items = [
            Item(DISPLAY_LABELS.get(key, key), value)
            for key, value in display.items()
            if value and key != "name"
        ]
        groups.append(Group(f"Дисплей {index} — {display.get('name', '?')}", items))
        if index == 1:
            summary.append(Item("Видеокарта (dxdiag)", first(display.get("name"))))
    for index, sound in enumerate(report.get("sound") or [], start=1):
        items = [
            Item(SOUND_LABELS.get(key, key), value)
            for key, value in sound.items()
            if value and key != "name"
        ]
        groups.append(Group(f"Звук {index} — {sound.get('name', '?')}", items))
    return Section("dxdiag", "DirectX (dxdiag)", groups, summary)
