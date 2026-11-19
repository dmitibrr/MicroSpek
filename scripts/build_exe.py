"""Build standalone Windows EXEs and ready-to-share ZIPs.

Usage:
    python scripts/build_exe.py                     # full edition
    python scripts/build_exe.py --edition all       # all four archives
    python scripts/build_exe.py --edition cli
    python scripts/build_exe.py --edition snapshot
    python scripts/build_exe.py --edition gui

Editions:
    full      MicroSpek-GUI.exe + microspek.exe (CLI) + sensors + SNAPSHOT.cmd
    gui       MicroSpek.exe — only the redesigned windowed app
    cli       microspek.exe — console CLI for scripts and AI agents
    snapshot  microspek-snapshot.exe — minimal configurable snapshot writer

Every archive is written to dist/MicroSpek-<version>-<edition>-WIN64.zip and
gets a .sha256 file next to it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

EDITIONS = ("full", "gui", "cli", "snapshot")

COMMON_EXCLUDES = (
    "unittest",
    "pydoc",
    "doctest",
    "pdb",
    "numpy",
    "setuptools",
    "pip",
    "wheel",
)

LIGHT_EXCLUDES = COMMON_EXCLUDES + ("tkinter", "PIL", "Pillow")


def read_version() -> str:
    text = (SRC / "microspek" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    if not match:
        raise RuntimeError("Could not read __version__")
    return match.group(1)


def run_pyinstaller(
    work: Path,
    name: str,
    entry: str,
    *,
    windowed: bool,
    light: bool,
) -> Path:
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        name,
        "--paths",
        str(SRC),
        "--distpath",
        str(work / "dist"),
        "--workpath",
        str(work / "work" / name),
        "--specpath",
        str(work / "spec"),
    ]
    command.append("--windowed" if windowed else "--console")
    for module in LIGHT_EXCLUDES if light else COMMON_EXCLUDES:
        command += ["--exclude-module", module]
    command.append(str(ROOT / "scripts" / entry))
    print(f"\n>>> Building {name}.exe ({'GUI' if windowed else 'CLI'})")
    subprocess.run(command, cwd=ROOT, check=True)
    return work / "dist" / f"{name}.exe"


def ensure_sensors(skip: bool) -> Path | None:
    if skip:
        return None
    sensors_dir = ROOT / "build" / "sensors"
    if not (sensors_dir / "MicroSpekSensors.exe").exists():
        print(">>> Building MicroSpekSensors.exe")
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build_sensors.py")],
            cwd=ROOT,
            check=True,
        )
    return sensors_dir


SNAPSHOT_CMD = """@echo off
setlocal
"%~dp0microspek.exe" --output txt --redact --no-dxdiag --admin-sensors --file "%~dp0snapshot_SAFE.txt"
echo.
echo Done: %~dp0snapshot_SAFE.txt
echo Send this file back.
echo.
start "" notepad "%~dp0snapshot_SAFE.txt"
endlocal
"""

SNAPSHOT_ONLY_CMD = """@echo off
setlocal
"%~dp0microspek-snapshot.exe" --config "%~dp0microspek.json" --file "%~dp0snapshot.md" --redact --admin-sensors --open
echo.
echo Done: %~dp0snapshot.md
echo.
endlocal
"""


def howto(edition: str) -> str:
    common = (
        "MicroSpek — standalone build\n"
        "===========================\n\n"
        "No Python and no installation required. Unpack the whole folder and run\n"
        "the .exe. Keep the sensors folder next to the program: it contains the\n"
        "hardware sensor helper (temperatures, fans, SMART). Windows 10/11 x64.\n\n"
    )
    if edition == "full":
        body = (
            "MicroSpek-GUI.exe — the windowed app (double-click).\n"
            "  Refresh collects the data, Export saves TXT/JSON/Markdown,\n"
            "  Sensors (admin) re-collects with CPU temperatures and disk SMART.\n\n"
            "microspek.exe — console version:\n"
            "  microspek.exe --summary\n"
            "  microspek.exe --output md --file pc.md\n"
            "  microspek.exe --output json --redact --file pc.json\n"
            "  microspek.exe --admin-sensors --output txt --file full.txt\n"
            "  microspek.exe --lang en --summary\n\n"
            "SNAPSHOT.cmd — one double-click: a safe TXT snapshot without serials\n"
            "and MAC addresses, opened in Notepad.\n"
        )
    elif edition == "gui":
        body = (
            "MicroSpek.exe — the windowed app (double-click).\n"
            "  Refresh collects the data.\n"
            "  Export ▾ saves TXT / JSON / Markdown.\n"
            "  Sensors (admin) asks for UAC once: CPU temperatures, fans, SMART.\n"
            "  The RU/EN switch is in the top-right corner.\n\n"
            "This edition is GUI-only: for scripts use the cli edition.\n"
        )
    elif edition == "cli":
        body = (
            "microspek.exe — console version. Open a terminal in this folder:\n"
            "  microspek.exe --summary\n"
            "  microspek.exe --output md --file pc.md\n"
            "  microspek.exe --output json --redact --file pc.json\n"
            "  microspek.exe --snapshot --redact\n"
            "  microspek.exe --admin-sensors --output txt --file full.txt\n"
            "  microspek.exe --no-sensors --no-dxdiag --summary\n"
            "  microspek.exe --lang en --output md --file pc.md\n\n"
            "SNAPSHOT.cmd — one double-click: a safe TXT snapshot for sending back.\n"
            "microspek.json — optional defaults (redact, sections, language...).\n"
        )
    else:
        body = (
            "microspek-snapshot.exe — the lightweight snapshot writer.\n"
            "Settings live in microspek.json next to the exe:\n\n"
            '  "output":  "md"        txt, json or md\n'
            '  "file":    "snapshot.md"  relative to this folder\n'
            '  "redact":  true        hide serials/MAC/user\n'
            '  "sections": ["os","cpu","memory","storage","gpu"]\n'
            '  "sensors": true        set false to skip the helper\n'
            '  "dxdiag":  false       slow DirectX report\n'
            '  "admin_sensors": false ask UAC for CPU temps/SMART\n'
            '  "lang":    "ru"        ru or en\n'
            '  "open":    false       open the report afterwards\n'
            '  "quiet":   false       no progress output\n\n'
            "Pick only the sections you need: startup and collection time drop\n"
            "with every collector you remove. Available keys: os, motherboard,\n"
            "cpu, memory, storage, gpu, network, devices, dxdiag.\n\n"
            "Command line overrides the file: --output, --file, --redact,\n"
            "--sections, --no-sensors, --dxdiag, --admin-sensors, --lang,\n"
            "--stdout, --open, --quiet, --config PATH.\n\n"
            "SNAPSHOT.cmd — one double-click with the settings above.\n"
            "This edition is meant for embedding into other tools; it never\n"
            "opens a window and needs no GUI libraries.\n"
        )
    footer = (
        "\nSmartscreen may warn about an unsigned executable:\n"
        "More info -> Run anyway.\n\n"
        "License: Unlicense (public domain). Third-party notices: sensors/.\n"
        "Temperatures of CPU and fan speeds may need the PawnIO driver; GPU\n"
        "sensors and disk SMART temperatures work without it.\n"
    )
    return common + body + footer


def snapshot_config(version: str) -> dict:
    return {
        "output": "md",
        "file": "snapshot.md",
        "redact": True,
        "sections": ["os", "motherboard", "cpu", "memory", "storage", "gpu", "network", "devices"],
        "sensors": True,
        "dxdiag": False,
        "admin_sensors": False,
        "lang": "ru",
        "open": False,
        "quiet": False,
    }


def stage(
    folder: Path,
    edition: str,
    version: str,
    sensors_dir: Path | None,
    binaries: dict[str, Path],
) -> None:
    folder.mkdir(parents=True)
    for target_name, source in binaries.items():
        shutil.copy2(source, folder / target_name)

    shutil.copy2(ROOT / "LICENSE", folder / "LICENSE")
    (folder / "README.txt").write_text(howto(edition), encoding="utf-8")

    if edition in ("full", "cli"):
        (folder / "SNAPSHOT.cmd").write_text(SNAPSHOT_CMD, encoding="utf-8")
    elif edition == "snapshot":
        (folder / "SNAPSHOT.cmd").write_text(SNAPSHOT_ONLY_CMD, encoding="utf-8")
        (folder / "microspek.json").write_text(
            json.dumps(snapshot_config(version), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if edition == "cli":
        (folder / "microspek.json").write_text(
            json.dumps(
                {
                    "output": "txt",
                    "redact": True,
                    "sections": "all",
                    "sensors": True,
                    "dxdiag": False,
                    "admin_sensors": False,
                    "lang": "ru",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    if sensors_dir is not None:
        shutil.copytree(
            sensors_dir,
            folder / "sensors",
            ignore=shutil.ignore_patterns("*.xml", "*.pdb", "__pycache__"),
        )


def build_edition(edition: str, version: str, sensors_dir: Path | None, work: Path) -> Path:
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    archive = dist / f"MicroSpek-{version}-{edition}-WIN64.zip"
    binaries: dict[str, Path]

    if edition == "full":
        gui = run_pyinstaller(work, "MicroSpek-GUI", "gui_entry.py", windowed=True, light=False)
        cli = run_pyinstaller(work, "microspek", "cli_entry.py", windowed=False, light=True)
        binaries = {"MicroSpek-GUI.exe": gui, "microspek.exe": cli}
    elif edition == "gui":
        gui = run_pyinstaller(work, "MicroSpek", "gui_entry.py", windowed=True, light=False)
        binaries = {"MicroSpek.exe": gui}
    elif edition == "cli":
        cli = run_pyinstaller(work, "microspek", "cli_entry.py", windowed=False, light=True)
        binaries = {"microspek.exe": cli}
    else:
        snapshot = run_pyinstaller(
            work, "microspek-snapshot", "snapshot_entry.py", windowed=False, light=True
        )
        binaries = {"microspek-snapshot.exe": snapshot}

    folder = work / "release" / f"MicroSpek-{version}-{edition}-WIN64"
    stage(folder, edition, version, sensors_dir, binaries)

    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(folder.parent))

    sizes = ", ".join(f"{name}: {source.stat().st_size // 1024} KB" for name, source in binaries.items())
    print(f"\n{edition}: {sizes}")
    return archive


def build(editions: list[str], skip_sensors: bool = False) -> list[Path]:
    version = read_version()
    sensors_dir = ensure_sensors(skip_sensors)
    archives: list[Path] = []
    with tempfile.TemporaryDirectory() as tmp:
        work_root = Path(tmp)
        for edition in editions:
            # A separate PyInstaller workspace keeps per-edition caches apart.
            work = work_root / edition
            work.mkdir(parents=True, exist_ok=True)
            archive = build_edition(edition, version, sensors_dir, work)
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            (archive.parent / f"{archive.name}.sha256").write_text(
                f"{digest}  {archive.name}\n", encoding="utf-8"
            )
            print(f"Archive: {archive} ({archive.stat().st_size} bytes)")
            print(f"SHA256:  {digest}")
            archives.append(archive)
    return archives


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build MicroSpek Windows editions")
    parser.add_argument(
        "--edition",
        choices=(*EDITIONS, "all"),
        default="full",
        help="which edition to build (default: full)",
    )
    parser.add_argument(
        "--skip-sensors",
        action="store_true",
        help="do not include MicroSpekSensors.exe (smaller archive, no sensors)",
    )
    args = parser.parse_args(argv)
    editions = list(EDITIONS) if args.edition == "all" else [args.edition]
    build(editions, args.skip_sensors)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
