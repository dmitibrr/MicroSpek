"""PyInstaller entry point for the windowed GUI edition."""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

# In onefile mode the extracted bundle is not the folder the user launched, so
# relative paths must come from the executable itself.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


def _show_error(message: str) -> None:
    from microspek.i18n import detect_language, set_language, s

    set_language(detect_language())
    log = Path(sys.executable).parent / "microspek_error.txt"
    try:
        log.write_text(message, encoding="utf-8")
    except OSError:
        pass
    try:
        import tkinter.messagebox as messagebox

        messagebox.showerror(s("start_error_title"), s("start_error_body", path=log))
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
