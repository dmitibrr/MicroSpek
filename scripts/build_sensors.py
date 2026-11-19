"""Compile MicroSpekSensors.exe with the .NET Framework compiler built into Windows.

Usage: python scripts/build_sensors.py [--check-only]

Output: build/sensors/MicroSpekSensors.exe + LibreHardwareMonitor DLLs.
Requires vendor/lhm/win-x64 (see scripts/fetch_sensors_vendor.py).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

# GitHub Actions uses cp1252 on Windows runners; Russian log lines must not
# crash the release build before the helper is even produced.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "vendor" / "lhm" / "win-x64"SOURCE_DIR = ROOT / "tools" / "sensors"
SOURCE = SOURCE_DIR / "MicroSpekSensors.cs"
OUT_DIR = ROOT / "build" / "sensors"
EXE = OUT_DIR / "MicroSpekSensors.exe"

# Notices that must travel with the shipped DLLs.
NOTICES = ["THIRD_PARTY.md", "LICENSE-MPL-2.0.txt", "LICENSE-HidSharp.txt"]


def find_csc() -> Path:
    candidates = [
        Path(r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"),
        Path(r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("csc.exe (.NET Framework) не найден")


def build() -> Path:
    if not (VENDOR / "LibreHardwareMonitorLib.dll").exists():
        raise FileNotFoundError(
            f"Нет {VENDOR / 'LibreHardwareMonitorLib.dll'}. "
            "Сначала запустите python scripts/fetch_sensors_vendor.py"
        )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for dll in VENDOR.glob("*.dll"):
        shutil.copy2(dll, OUT_DIR / dll.name)
    for extra in VENDOR.glob("LICENSE-*.txt"):
        shutil.copy2(extra, OUT_DIR / extra.name)
    for notice in NOTICES:
        source = SOURCE_DIR / notice
        if not source.is_file():
            raise FileNotFoundError(f"Нет файла уведомлений {source}")
        shutil.copy2(source, OUT_DIR / notice)

    command = [
        str(find_csc()),
        "/nologo",
        "/target:exe",
        "/platform:x64",
        "/optimize+",
        "/warn:4",
        f"/out:{EXE}",
        f"/r:{VENDOR / 'LibreHardwareMonitorLib.dll'}",
        str(SOURCE),
    ]
    print(">>> " + " ".join(command))
    completed = subprocess.run(command, capture_output=True, text=True, errors="replace")
    if completed.stdout.strip():
        print(completed.stdout.strip())
    if completed.returncode != 0:
        print(completed.stderr.strip(), file=sys.stderr)
        raise SystemExit(f"csc завершился с кодом {completed.returncode}")
    if completed.stderr.strip():
        print(completed.stderr.strip())
    print(f"\nOK: {EXE} ({EXE.stat().st_size} байт)")
    return EXE


def check() -> dict:
    completed = subprocess.run(
        [str(EXE)],
        capture_output=True,
        timeout=90,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    text = completed.stdout.decode("utf-8", "replace").strip()
    if not text:
        raise SystemExit(f"Пустой вывод, код {completed.returncode}: {completed.stderr[:400]!r}")
    data = json.loads(text)
    if not data.get("ok"):
        raise SystemExit(f"Helper вернул ошибку: {data.get('error')}")
    print(f"\nНайдено железо: {len(data['hardware'])}")
    for hardware in data["hardware"]:
        print(f"  {hardware['type']:<14} {hardware['name']}  ({len(hardware['sensors'])} сенсоров)")
        for child in hardware.get("children", []):
            print(f"    └ {child['type']:<12} {child['name']}  ({len(child['sensors'])} сенсоров)")
    return data


if __name__ == "__main__":
    build()
    if "--check-only" not in sys.argv:
        check()
