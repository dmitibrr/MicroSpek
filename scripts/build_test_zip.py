"""Build a single archive to send to a tester: python scripts/build_test_zip.py.

The result is the ``full`` edition: GUI + CLI + sensor helper + SNAPSHOT.cmd.
No Python is required on the tester's machine.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_exe import build  # noqa: E402


def main() -> int:
    archive = build(["full"])[0]
    print(f"\nSend this file: {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
