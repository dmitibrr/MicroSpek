"""PyInstaller entry point for the windowed MicroSpek-GUI.exe."""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

# В onefile-сборке модули уже внутри бандла; путь нужен только при запуске
# этого файла прямо из исходников без установленного пакета.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


def _show_error(message: str) -> None:
    log = Path(sys.executable).parent / "microspek_error.txt"
    try:
        log.write_text(message, encoding="utf-8")
    except OSError:
        pass
    try:
        import tkinter.messagebox as messagebox

        messagebox.showerror(
            "MicroSpek — ошибка запуска",
            f"{message}\n\nПодробности в файле:\n{log}",
        )
    except Exception:
        pass


def main() -> None:
    try:
        from microspek.gui import run_gui

        run_gui()
    except Exception:
        _show_error(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
