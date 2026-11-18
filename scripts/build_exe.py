"""Build standalone Windows EXEs and a ready-to-share ZIP.

Usage: python scripts/build_exe.py

Produces:
  dist/MicroSpek-<version>-WIN64.zip
    MicroSpek-GUI.exe — windowed GUI (double-click)
    microspek.exe     — console CLI (--summary, --snapshot, --output ...)
    SNAPSHOT.cmd    — one-click TXT snapshot via our CLI exe
    КАК_ПОЛЬЗОВАТЬСЯ.txt
"""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"


def read_version() -> str:
    text = (SRC / "microspek" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    if not match:
        raise RuntimeError("Не удалось определить версию")
    return match.group(1)


def run_pyinstaller(work: Path, name: str, entry: str, windowed: bool) -> Path:
    command = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onefile",
        "--name", name,
        "--paths", str(SRC),
        "--distpath", str(work / "dist"),
        "--workpath", str(work / "work" / name),
        "--specpath", str(work / "spec"),
    ]
    command.append("--windowed" if windowed else "--console")
    command.append(str(ROOT / "scripts" / entry))
    print(f"\n>>> Сборка {name}.exe ({'GUI' if windowed else 'CLI'})")
    subprocess.run(command, cwd=ROOT, check=True)
    return work / "dist" / f"{name}.exe"


SNAPSHOT_CMD = """@echo off
setlocal
"%~dp0microspek.exe" --output txt --redact --no-dxdiag --admin-sensors --file "%~dp0snapshot_SAFE.txt"
echo.
echo Готово: %~dp0snapshot_SAFE.txt
echo Отправьте этот файл обратно.
echo.
start "" notepad "%~dp0snapshot_SAFE.txt"
endlocal
"""

HOWTO = """MicroSpek — как пользоваться тестовой сборкой
===============================================

Это standalone-программа: Python и нужные библиотеки уже внутри .exe.
Ставить ничего не нужно. Распакуйте папку целиком (например, в Документы).
Папку sensors удалять нельзя — в ней сборщик датчиков (температуры и SMART).

1) Двойной клик по MicroSpek-GUI.exe
   Откроется окно программы. Через несколько секунд соберутся данные
   (вкладки: Сводка, ОС, Процессор, Память, Диски, Видеокарта, Сеть, Устройства).
   Нажмите кнопку «Слепок TXT» и сохраните файл — его можно прислать нам.

   Кнопка «Датчики (админ)» пересобирает данные с правами администратора:
   появляются температуры CPU, обороты вентиляторов и SMART дисков.

2) Или ещё проще: двойной клик по SNAPSHOT.cmd
   Сработает наша же консольная программа microspek.exe, создаст файл
   snapshot_SAFE.txt в этой папке и откроет его в Блокноте.
   Windows спросит разрешение администратора — это нужно для температур и SMART.
   Можно нажать «Нет»: слепок всё равно создастся, просто без этих датчиков.
   Пришлите snapshot_SAFE.txt обратно — по нему мы увидим, как собрались данные.

3) microspek.exe — это консольная версия. Если открыть её в cmd, доступны:
     microspek.exe --summary
     microspek.exe --snapshot --redact
     microspek.exe --output json --file report.json
     microspek.exe --output png --file report.png
     microspek.exe --output txt --file fast.txt
     microspek.exe --output txt --admin-sensors --file full.txt

ЧТО ПРОВЕРИТЬ
-------------
- правильно ли определены процессор, память, диски, разделы, монитор, сеть;
- видны ли температуры (Процессор, Видеокарта) и SMART-температуры дисков;
- есть ли данные о звуке/Bluetooth и режиме загрузки (UEFI/Secure Boot);
- не слишком ли много прочерков там, где на вашем ПК данные должны быть;
- не падает ли окно и не подвисает ли на сборе.

Температуры CPU и обороты вентиляторов требуют драйвера PawnIO (ставится
отдельно, один раз). Без него SMART дисков и датчики видеокарты всё равно
работают. DXDiag в слепке по умолчанию выключен, чтобы не ждать до минуты.
Программа работает только на Windows.
"""


def ensure_sensors() -> Path:
    """Build MicroSpekSensors.exe if it is not there yet."""
    sensors_dir = ROOT / "build" / "sensors"
    if not (sensors_dir / "MicroSpekSensors.exe").exists():
        print(">>> Сборка MicroSpekSensors.exe")
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build_sensors.py")],
            cwd=ROOT,
            check=True,
        )
    return sensors_dir

def build() -> Path:
    version = read_version()
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    archive = dist / f"MicroSpek-{version}-WIN64.zip"
    sensors_dir = ensure_sensors()

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        gui_exe = run_pyinstaller(work, "MicroSpekGUI", "gui_entry.py", windowed=True)
        cli_exe = run_pyinstaller(work, "microspek", "cli_entry.py", windowed=False)

        folder = work / "release" / f"MicroSpek-{version}-WIN64"
        folder.mkdir(parents=True)
        # Windows не различает регистр: MicroSpek.exe и microspek.exe слились бы.
        shutil.copy2(gui_exe, folder / "MicroSpek-GUI.exe")
        shutil.copy2(cli_exe, folder / "microspek.exe")
        (folder / "SNAPSHOT.cmd").write_text(SNAPSHOT_CMD, encoding="utf-8")
        (folder / "КАК_ПОЛЬЗОВАТЬСЯ.txt").write_text(HOWTO, encoding="utf-8")
        shutil.copytree(
            sensors_dir,
            folder / "sensors",
            ignore=shutil.ignore_patterns("*.xml", "*.pdb"),
        )

        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for path in sorted(folder.rglob("*")):
                if path.is_file():
                    zf.write(path, path.relative_to(folder.parent))

        print(f"\nGUI exe:  {gui_exe.stat().st_size} байт")
        print(f"CLI exe:  {cli_exe.stat().st_size} байт")

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (dist / f"{archive.name}.sha256").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    print(f"\nГотово: {archive} ({archive.stat().st_size} байт)")
    print(f"SHA256: {digest}")
    return archive


if __name__ == "__main__":
    build()
