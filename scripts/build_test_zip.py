"""Build a friend-friendly test ZIP: python scripts/build_test_zip.py."""

from __future__ import annotations

import hashlib
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from install import LAUNCHER  # noqa: E402


def read_version() -> str:
    source = (ROOT / "src" / "microspek" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', source)
    return match.group(1) if match else "0"


PY_CHECK = r"""
where py >nul 2>&1
if errorlevel 1 goto TRY_PYTHON
set "PY=py -3"
goto PY_READY
:TRY_PYTHON
where python >nul 2>&1
if errorlevel 1 goto NO_PYTHON
set "PY=python"
:PY_READY
"""

NO_PYTHON = r"""
:NO_PYTHON
echo.
echo [!] Python 3.10+ not found.
echo     Install from https://www.python.org/downloads/
echo     IMPORTANT: tick "Add Python to PATH" during installation.
echo.
pause
goto DONE
"""

RUN_CMD = """@echo off
setlocal
set "MS_HOME=%~dp0"
pushd "%MS_HOME%" >nul
set "PYTHONPATH=%MS_HOME%src"
""" + PY_CHECK + """
%PY% -m microspek --gui
goto DONE
""" + NO_PYTHON + """
:DONE
popd
endlocal
"""

SNAPSHOT_CMD = """@echo off
setlocal
set "MS_HOME=%~dp0"
pushd "%MS_HOME%" >nul
set "PYTHONPATH=%MS_HOME%src"
""" + PY_CHECK + """
echo Collecting snapshot (without slow dxdiag)...
%PY% -m microspek --output txt --no-dxdiag --file "%MS_HOME%snapshot_FULL.txt"
%PY% -m microspek --output txt --no-dxdiag --redact --file "%MS_HOME%snapshot_SAFE.txt"
echo.
echo FULL: %MS_HOME%snapshot_FULL.txt
echo SAFE: %MS_HOME%snapshot_SAFE.txt   ^<- send this one back
echo.
start "" notepad "%MS_HOME%snapshot_SAFE.txt"
goto DONE
""" + NO_PYTHON + """
:DONE
popd
endlocal
"""

REPORT_CMD = """@echo off
setlocal
set "MS_HOME=%~dp0"
pushd "%MS_HOME%" >nul
set "PYTHONPATH=%MS_HOME%src"
""" + PY_CHECK + """
echo Generating PNG report...
%PY% -m microspek --output png --no-dxdiag --file "%MS_HOME%report.png"
start "" "%MS_HOME%report.png"
goto DONE
""" + NO_PYTHON + """
:DONE
popd
endlocal
"""

DEPS_CMD = """@echo off
setlocal
set "MS_HOME=%~dp0"
""" + PY_CHECK + """
%PY% -m pip install -r "%MS_HOME%requirements.txt"
echo.
echo Done. Press any key to close.
pause >nul
goto DONE
""" + NO_PYTHON + """
:DONE
endlocal
"""

README_TEST = """MicroSpek — тестовая сборка
===========================

Что это
-------
Утилита собирает характеристики ПК и делает текстовый/PNG-отчёт.
Ничего не устанавливается и не меняется в системе — просто распакуйте
папку в любое место (например, в Документы) и запустите нужный файл.

Требование
----------
Нужен Python 3.10+ с галочкой "Add Python to PATH" при установке.
Если его нет: https://www.python.org/downloads/
Если при запуске ругается на отсутствующий Pillow — сначала запустите
install_deps.cmd (он поставит одну маленькую библиотеку для PNG).

Как тестировать
---------------
1) snapshot.cmd  — соберёт два файла в этой же папке:
     snapshot_FULL.txt — полный отчёт (серийные номера и MAC видны),
     snapshot_SAFE.txt — то же, но с скрытыми чувствительными данными.
     Откройте SAFE и пришлите его мне — по нему я увижу, что именно
     собралось на вашем ПК и где нужно что-то доделать.

2) run.cmd       — откроет графический интерфейс (вкладки, диаграмма
     разделов, кнопки "Слепок TXT", JSON, PNG, "Скриншот окна").
     Там можно нажать "Слепок TXT" и тоже сохранить отчёт.

3) report.cmd    — сделает report.png с визуальной разметкой дисков.

4) microspek.cmd — если хотите команду вручную, например:
     microspek.cmd --summary
     microspek.cmd --snapshot --redact

Что проверить особенно
----------------------
- правильно ли определились процессор, память (модули, частоты), диски и разделы;
- есть ли данные о мониторе, ОС, сети, звуке и Bluetooth;
- не показываются ли прочерки там, где на вашем ПК данные должны быть;
- открывается ли GUI и не подвисает ли на сборе.

Пришлите, пожалуйста: snapshot_SAFE.txt + скриншот GUI (если запускали),
и коротко: что не так или чего не хватает.

Авто-сборка данных идёт через PowerShell (CIM/WMI), поэтому утилита
работает только на Windows.
"""

def build() -> Path:
    version = read_version()
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    archive = dist / f"MicroSpek-{version}-TEST.zip"

    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp) / f"MicroSpek-{version}-TEST"
        staging.mkdir(parents=True)

        shutil.copytree(
            ROOT / "src", staging / "src",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        )
        shutil.copy2(ROOT / "README.md", staging / "README.md")
        shutil.copy2(ROOT / "requirements.txt", staging / "requirements.txt")
        shutil.copy2(ROOT / "LICENSE", staging / "LICENSE")

        (staging / "microspek.cmd").write_text(LAUNCHER, encoding="utf-8")
        (staging / "run.cmd").write_text(RUN_CMD, encoding="utf-8")
        (staging / "snapshot.cmd").write_text(SNAPSHOT_CMD, encoding="utf-8")
        (staging / "report.cmd").write_text(REPORT_CMD, encoding="utf-8")
        (staging / "install_deps.cmd").write_text(DEPS_CMD, encoding="utf-8")
        (staging / "README_TEST.txt").write_text(README_TEST, encoding="utf-8")

        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for path in sorted(staging.rglob("*")):
                if path.is_file():
                    zf.write(path, path.relative_to(staging.parent))

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (dist / f"{archive.name}.sha256").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    print(f"Готово: {archive} ({archive.stat().st_size} байт)")
    print(f"SHA256: {digest}")
    return archive


if __name__ == "__main__":
    build()
