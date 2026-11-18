"""MicroSpek installer: portable, fixed-location, PATH command and skill setup.

Examples
--------
python install.py --mode portable
python install.py --mode portable --target D:\\Apps\\MicroSpek
python install.py --mode system --shortcuts
python install.py --mode system --target "C:\\Program Files\\MicroSpek" --yes
python install.py --uninstall --target "%LOCALAPPDATA%\\Programs\\MicroSpek"
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from microspek.util import run_powershell  # noqa: E402

APP_NAME = "MicroSpek"
DEFAULT_PORTABLE = ROOT / "MicroSpek-portable"
DEFAULT_SYSTEM = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "Programs" / APP_NAME
INFO_NAME = "install_info.json"
SKILL_ID = "microspek"


# --------------------------------------------------------------------------- helpers

def _quote(text: object) -> str:
    return str(text).replace('"', '""')


def _psq(text: object) -> str:
    return "'" + str(text).replace("'", "''") + "'"


def _is_windows() -> bool:
    return os.name == "nt"


def _default_target(mode: str) -> Path:
    return DEFAULT_PORTABLE if mode == "portable" else DEFAULT_SYSTEM


def _python_command() -> str:
    if shutil.which("py"):
        return "py -3"
    return sys.executable


def broadcast_environment_change() -> None:
    """Let running applications know that the user PATH changed."""
    if not _is_windows():
        return
    try:
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.SendMessageTimeoutW.argtypes = [
            wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPCWSTR,
            wintypes.UINT, wintypes.UINT, ctypes.POINTER(wintypes.DWORD),
        ]
        result = wintypes.DWORD()
        user32.SendMessageTimeoutW(
            0xFFFF, 0x001A, 0, "Environment", 0x0002, 5000, ctypes.byref(result)
        )
    except Exception as exc:  # pragma: no cover - best effort
        print(f"  ! Не удалось обновить окружение сессии: {exc}")


def get_user_path() -> list[str]:
    if not _is_windows():
        return []
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, "Path")
            return [part for part in str(value).split(";") if part.strip()]
    except FileNotFoundError:
        return []


def set_user_path(parts: list[str]) -> None:
    if not _is_windows():
        return
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_WRITE) as key:
        winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, ";".join(parts))
    broadcast_environment_change()


def add_to_path(target: Path) -> bool:
    parts = get_user_path()
    target_str = str(target)
    normalized = target_str.rstrip("\\/").lower()
    parts = [p for p in parts if p.rstrip("\\/").lower() != normalized]
    parts.append(target_str)
    set_user_path(parts)
    return True


def remove_from_path(target: Path) -> bool:
    parts = get_user_path()
    normalized = str(target).rstrip("\\/").lower()
    kept = [p for p in parts if p.rstrip("\\/").lower() != normalized]
    if len(kept) == len(parts):
        return False
    set_user_path(kept)
    return True


def make_shortcut(lnk_path: Path, launcher: Path, working_dir: Path) -> bool:
    lnk_path.parent.mkdir(parents=True, exist_ok=True)
    ps = f"""
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut({_psq(lnk_path)})
$s.TargetPath = {_psq(launcher)}
$s.Arguments = '--gui'
$s.WorkingDirectory = {_psq(working_dir)}
$s.IconLocation = 'C:\\Windows\\System32\\shell32.dll,15'
$s.Description = 'MicroSpek — характеристики ПК'
$s.Save()
"""
    completed = run_powershell(ps)
    return completed is not None and completed.returncode == 0


# --------------------------------------------------------------------------- content

LAUNCHER = r"""@echo off
setlocal
set "MICROSPEK_HOME=%~dp0"
pushd "%MICROSPEK_HOME%" >nul
set "PYTHONPATH=%MICROSPEK_HOME%src"
where py >nul 2>&1
if errorlevel 1 goto USE_PYTHON
py -3 -m microspek %*
set "RC=%ERRORLEVEL%"
goto FINISH
:USE_PYTHON
python -m microspek %*
set "RC=%ERRORLEVEL%"
:FINISH
popd
endlocal & exit /b %RC%
"""

UNINSTALLER = r"""@echo off
setlocal
set "MICROSPEK_HOME=%~dp0"
where py >nul 2>&1
if errorlevel 1 goto USE_PYTHON
py -3 "%MICROSPEK_HOME%_microspek_installer.py" --uninstall --target "%MICROSPEK_HOME%" --yes
goto FINISH
:USE_PYTHON
python "%MICROSPEK_HOME%_microspek_installer.py" --uninstall --target "%MICROSPEK_HOME%" --yes
:FINISH
pause
"""


def copy_application(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        ROOT / "src", target / "src",
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    for name in ("README.md", "LICENSE", "CHANGELOG.md"):
        source = ROOT / name
        if source.exists():
            shutil.copy2(source, target / name)
    shutil.copy2(Path(__file__).resolve(), target / "_microspek_installer.py")
    (target / "microspek.cmd").write_text(LAUNCHER, encoding="utf-8")
    (target / "uninstall.cmd").write_text(UNINSTALLER, encoding="utf-8")


def global_skill_dir() -> Path:
    return Path.home() / ".config" / "opencode" / "skills" / SKILL_ID


def install_global_skill() -> bool:
    source = ROOT / ".opencode" / "skills" / SKILL_ID
    if not source.is_dir():
        print("  ! Скилл не найден в репозитории, пропускаю")
        return False
    destination = global_skill_dir()
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    print(f"  Скилл установлен: {destination}")
    return True


def remove_global_skill() -> None:
    destination = global_skill_dir()
    if destination.exists():
        shutil.rmtree(destination)
        print(f"  Скилл удалён: {destination}")


# --------------------------------------------------------------------------- actions

def do_install(args: argparse.Namespace) -> int:
    target = Path(args.target).expanduser().resolve() if args.target else _default_target(args.mode).resolve()
    print(f"Установка MicroSpek ({args.mode})")
    print(f"  Папка: {target}")

    if target.exists() and any(target.iterdir()) and not args.yes:
        answer = input("  Папка не пуста. Продолжить с перезаписью? [y/N]: ").strip().lower()
        if answer not in ("y", "yes", "д", "да"):
            print("Отменено.")
            return 1

    try:
        copy_application(target)
        print("  Файлы скопированы")
    except OSError as exc:
        print(f"  ОШИБКА копирования: {exc}")
        return 1

    path_added = False
    if args.add_path and not args.no_path:
        path_added = add_to_path(target)
        print("  Команда microspek добавлена в PATH пользователя")

    shortcut_paths: list[str] = []
    if args.shortcuts:
        launcher = target / "microspek.cmd"
        candidates = []
        if _is_windows():
            desktop = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
            start_menu = (
                Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" /
                "Start Menu" / "Programs"
            )
            candidates = [desktop / "MicroSpek.lnk", start_menu / "MicroSpek.lnk"]
        for candidate in candidates:
            if make_shortcut(candidate, launcher, target):
                shortcut_paths.append(str(candidate))
                print(f"  Ярлык: {candidate}")

    skill_installed = False
    if not args.no_skill:
        skill_installed = install_global_skill()

    info = {
        "app": APP_NAME,
        "mode": args.mode,
        "target": str(target),
        "path_added": path_added,
        "shortcuts": shortcut_paths,
        "skill_installed": skill_installed,
    }
    (target / INFO_NAME).write_text(
        json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\nГотово.")
    print(f"  Запуск GUI:  microspek" if path_added else f"  Запуск GUI:  {target / 'microspek.cmd'} --gui")
    print("  Сводка:      microspek --summary")
    print("  Слепок TXT:  microspek --snapshot --redact --file snapshot.txt")
    if path_added:
        print("\n  Для подхвата PATH откройте новый терминал (или перелогиньтесь).")
    return 0


def do_uninstall(args: argparse.Namespace) -> int:
    target = Path(args.target).expanduser().resolve() if args.target else _default_target(args.mode).resolve()
    info_path = target / INFO_NAME
    info: dict = {}
    if info_path.exists():
        try:
            info = json.loads(info_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    print(f"Удаление MicroSpek: {target}")
    if info.get("path_added") or args.add_path:
        if remove_from_path(target):
            print("  Удалено из PATH")
    for shortcut in info.get("shortcuts", []):
        path = Path(shortcut)
        if path.exists():
            path.unlink()
            print(f"  Удалён ярлык: {path}")
    if info.get("skill_installed") and not args.no_skill:
        remove_global_skill()

    if target.exists():
        if not args.yes:
            answer = input(f"  Удалить папку {target} полностью? [y/N]: ").strip().lower()
            if answer not in ("y", "yes", "д", "да"):
                print("Папка оставлена на месте.")
                return 0
        try:
            shutil.rmtree(target)
            print("  Папка удалена")
        except OSError as exc:
            print(f"  Не удалось удалить папку: {exc}")
            return 1
    return 0


# --------------------------------------------------------------------------- entry

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Установщик MicroSpek: portable / фиксированная установка / команда в PATH."
    )
    parser.add_argument("--mode", choices=("portable", "system"), default="portable",
                        help="portable — папка рядом с проектом; system — в LOCALAPPDATA")
    parser.add_argument("--target", help=" явный путь установки")
    parser.add_argument("--add-path", action="store_true", help="добавить папку в PATH пользователя")
    parser.add_argument("--no-path", action="store_true", help="не трогать PATH")
    parser.add_argument("--shortcuts", action="store_true", help="создать ярлыки на Рабочем столе и в меню Пуск")
    parser.add_argument("--no-skill", action="store_true", help="не устанавливать скилл глобально")
    parser.add_argument("--uninstall", action="store_true", help="удалить установку")
    parser.add_argument("--yes", action="store_true", help="не задавать вопросы")
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args()
    if args.mode == "system" and not args.target:
        args.add_path = True
        args.shortcuts = True
    return do_uninstall(args) if args.uninstall else do_install(args)


if __name__ == "__main__":
    raise SystemExit(main())
