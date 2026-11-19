"""Build every release archive for GitHub: python scripts/build_release.py.

Delegates to ``scripts/build_exe.py`` so there is a single source of truth for
the four editions (full / gui / cli / snapshot), their ZIP layouts and SHA256
sidecar files.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_exe import EDITIONS, build  # noqa: E402


def main() -> int:
    archives = build(list(EDITIONS))
    print("\nRelease archives:")
    for archive in archives:
        digest = archive.with_name(archive.name + ".sha256").read_text(encoding="utf-8")
        print(f"  {archive.name:44} {archive.stat().st_size:>12} bytes")
        print(f"  {digest.strip()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
