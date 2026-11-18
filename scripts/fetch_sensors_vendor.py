"""Download LibreHardwareMonitorLib + its .NET Framework dependencies into vendor/lhm.

Run once (needs network), then the sensor helper can be built offline:

    python scripts/fetch_sensors_vendor.py

Output: vendor/lhm/win-x64/*.dll  (+ LICENSE files)
"""

from __future__ import annotations

import io
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "vendor" / "lhm" / "win-x64"
CACHE = Path.home() / "AppData" / "Local" / "Temp" / "opencode" / "nuget_cache"

ROOTS = {
    "LibreHardwareMonitorLib": "0.9.6",
    "DiskInfoToolkit": "1.1.2",
    "HidSharp": "2.6.4",
    "RAMSPDToolkit-NDD": "1.4.2",
    "System.Management": "10.0.2",
    "System.Memory": "4.6.3",
    "System.Threading.AccessControl": "10.0.3",
}

# Prefer the oldest supported .NET Framework build: it is what ships with Windows 10/11.
LIB_ORDER = [
    "net472", "net471", "net47", "net462", "net461", "net46", "net45", "net40",
    "netstandard2.0", "netstandard1.6", "netstandard1.3", "netstandard1.1",
]

FRAMEWORK_GROUP_ORDER = [
    ".NETFramework4.7.2", ".NETFramework4.7.1", ".NETFramework4.7",
    ".NETFramework4.6.2", ".NETFramework4.6.1", ".NETFramework4.6", ".NETFramework4.5",
    ".NETStandard2.0", ".NETStandard1.6", ".NETStandard1.3",
]


def download(package: str, version: str) -> zipfile.ZipFile | None:
    CACHE.mkdir(parents=True, exist_ok=True)
    target = CACHE / f"{package.lower()}.{version}.nupkg"
    if not target.exists():
        url = f"https://www.nuget.org/api/v2/package/{package}/{version}"
        print(f"  download {package} {version}")
        with urllib.request.urlopen(url, timeout=120) as response:
            target.write_bytes(response.read())
    return zipfile.ZipFile(io.BytesIO(target.read_bytes()))


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def pick_dll(names: list[str]) -> str | None:
    lowered = {name.lower(): name for name in names}
    for tfm in LIB_ORDER:
        for prefix in ("runtimes/win-x64/lib/", "lib/"):
            candidate = f"{prefix}{tfm}/".lower()
            for low, original in lowered.items():
                if low.startswith(candidate) and low.endswith(".dll") and "/ref/" not in low:
                    return original
    return None


def dependencies(nuspec: str) -> list[tuple[str, str]]:
    root = ET.fromstring(nuspec)
    groups = [node for node in root.iter() if local_name(node.tag) == "group"]
    chosen = None
    for wanted in FRAMEWORK_GROUP_ORDER:
        for group in groups:
            if str(group.attrib.get("targetFramework", "")).lower() == wanted.lower():
                chosen = group
                break
        if chosen is not None:
            break
    if chosen is None:
        return []
    result = []
    for dep in chosen:
        if local_name(dep.tag) != "dependency":
            continue
        name = dep.attrib.get("id")
        version = dep.attrib.get("version", "")
        version = re.sub(r"[\[\]()]", "", version).split(",")[0].strip()
        if name and version:
            result.append((name, version))
    return result


def version_key(version: str) -> tuple[int, ...]:
    parts = re.split(r"[.\-+]", version)
    numbers = []
    for part in parts:
        if part.isdigit():
            numbers.append(int(part))
        else:
            break
    return tuple(numbers) or (0,)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    # name -> best (highest) version seen so far. NuGet needs "nearest wins",
    # but these packages only ever need the newest transitive dependency.
    wanted: dict[str, str] = {}
    queue: list[tuple[str, str]] = list(ROOTS.items())
    processed: set[tuple[str, str]] = set()
    resolved: dict[str, str] = {}
    nuspecs: dict[tuple[str, str], str] = {}

    while queue:
        package, version = queue.pop()
        key = (package.lower(), version)
        if key in processed:
            continue
        processed.add(key)
        previous = wanted.get(package.lower())
        if previous and version_key(previous) > version_key(version):
            continue
        archive = download(package, version)
        nuspec_name = next((n for n in archive.namelist() if n.lower().endswith(".nuspec")), None)
        if not nuspec_name:
            print(f"FAIL {package}: no nuspec")
            return 1
        nuspec = archive.read(nuspec_name).decode("utf-8", "replace")
        nuspecs[key] = nuspec
        dll = pick_dll(archive.namelist())
        if dll:
            (OUT / Path(dll).name).write_bytes(archive.read(dll))
            resolved[package.lower()] = version
            wanted[package.lower()] = version
            print(f"OK   {package} {version} <- {dll}")
        else:
            print(f"SKIP {package} {version}: no managed dll")
        if package.lower().startswith("librehardwaremonitor"):
            license_entry = next(
                (n for n in archive.namelist() if "license" in n.lower() or "copying" in n.lower()),
                None,
            )
            if license_entry:
                (OUT / "LICENSE-LibreHardwareMonitorLib.txt").write_bytes(archive.read(license_entry))
        archive.close()
        for dep_name, dep_version in dependencies(nuspec):
            queue.append((dep_name, dep_version))

    print(f"\n{len(list(OUT.glob('*.dll')))} dll(s) in {OUT}")
    for path in sorted(OUT.iterdir()):
        print(f"  {path.name:48} {path.stat().st_size:>10}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
