"""PyInstaller entry point for the console microspek.exe CLI."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from microspek.__main__ import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
