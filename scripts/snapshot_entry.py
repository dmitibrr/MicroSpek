"""PyInstaller entry point for the lightweight microspek-snapshot.exe."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from microspek.snapshot_cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
