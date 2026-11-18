"""Build a portable ZIP for a GitHub release: python scripts/build_release.py."""

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
    if not match:
        raise RuntimeError("Не удалось определить версию")
    return match.group(1)


def build() -> Path:
    version = read_version()
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    archive = dist / f"microspek-{version}-portable.zip"

    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp) / f"microspek-{version}-portable"
        staging.mkdir(parents=True)

        shutil.copytree(
            ROOT / "src", staging / "src",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        )
        for name in ("README.md", "LICENSE", "CHANGELOG.md", "requirements.txt", "install.py", "run_microspek.py"):
            source = ROOT / name
            if source.exists():
                shutil.copy2(source, staging / name)
        skill_source = ROOT / ".opencode" / "skills" / "microspek"
        if skill_source.exists():
            shutil.copytree(skill_source, staging / ".opencode" / "skills" / "microspek")
        (staging / "microspek.cmd").write_text(LAUNCHER, encoding="utf-8")

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
