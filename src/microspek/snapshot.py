"""Snapshot assembly: runs every collector and gathers warnings."""

from __future__ import annotations

import platform
import socket
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Callable, Iterable

from .collectors import cpu, devices, gpu, memory, motherboard, network, os_info, storage
from .collectors import sensors as sensor_hub
from .models import DiskLayout, Section, Snapshot

SECTION_KEYS = (
    "os",
    "motherboard",
    "cpu",
    "memory",
    "storage",
    "gpu",
    "network",
    "devices",
    "dxdiag",
)

#: Human titles used in warnings; the UI language is applied later.
SECTION_TITLES = {
    "os": "ОС",
    "motherboard": "Материнская плата",
    "cpu": "Процессор",
    "memory": "Память",
    "storage": "Диски",
    "gpu": "Видеокарта",
    "network": "Сеть",
    "devices": "Устройства",
    "dxdiag": "DirectX",
}


def normalize_sections(sections: Iterable[str] | str | None) -> list[str] | None:
    """Turn ``"cpu, memory"`` / ``["cpu", "memory"]`` into validated keys."""
    if sections is None:
        return None
    if isinstance(sections, str):
        if sections.strip().lower() in ("", "all", "everything", "*"):
            return None
        parts = sections.replace(";", ",").split(",")
    else:
        parts = list(sections)
    wanted: list[str] = []
    for part in parts:
        key = str(part).strip().lower()
        if key in SECTION_KEYS and key not in wanted:
            wanted.append(key)
    return wanted


def collect_snapshot(
    include_dxdiag: bool = True,
    dxdiag_timeout: float = 60.0,
    elevate_sensors: bool = False,
    sections: Iterable[str] | str | None = None,
    sensors: bool = True,
) -> Snapshot:
    """Collect all available information into a single Snapshot.

    Every collector starts its own PowerShell interpreter, so they used to run
    one after another and pay that startup cost nine times. They are independent,
    hence run concurrently: total time is the slowest section, not the sum.

    ``sections`` limits the work to the given keys (see :data:`SECTION_KEYS`) and
    ``sensors`` can disable the C# helper completely: both are used by the
    lightweight snapshot edition.
    """
    selected = normalize_sections(sections)
    wanted = set(selected) if selected is not None else set(SECTION_KEYS)

    sensor_hub.set_enabled(sensors)
    if sensors:
        sensor_hub.begin(elevate=elevate_sensors)

    jobs: list[tuple[str, Callable[[], object]]] = []
    if "os" in wanted:
        jobs.append(("os", os_info.collect_os))
    if "motherboard" in wanted:
        jobs.append(("motherboard", motherboard.collect_motherboard))
    if "cpu" in wanted:
        jobs.append(("cpu", cpu.collect_cpu))
    if "memory" in wanted:
        jobs.append(("memory", memory.collect_memory))
    if "storage" in wanted:
        jobs.append(("storage", storage.collect_storage))
    if "gpu" in wanted:
        jobs.append(("gpu", gpu.collect_gpu))
    if "network" in wanted:
        jobs.append(("network", network.collect_network))
    if "devices" in wanted:
        jobs.append(("devices", devices.collect_devices))
    if include_dxdiag and "dxdiag" in wanted:
        # Imported here so the lightweight edition does not pay for it at startup.
        def _dxdiag() -> object:
            from .collectors import dxdiag

            return dxdiag.collect_dxdiag(dxdiag_timeout)

        jobs.append(("dxdiag", _dxdiag))

    sections_out: list[Section] = []
    layouts: list[DiskLayout] = []
    warnings: list[str] = []

    if jobs:
        with ThreadPoolExecutor(max_workers=min(8, len(jobs)), thread_name_prefix="microspek") as pool:
            futures = [(key, pool.submit(job)) for key, job in jobs]
            for key, future in futures:  # keep the section order stable
                try:
                    result = future.result()
                except Exception as exc:  # one broken collector must not kill the report
                    warnings.append(f"{SECTION_TITLES.get(key, key)}: {type(exc).__name__}: {exc}")
                    continue
                if isinstance(result, tuple):
                    section, extra = result
                    sections_out.append(section)
                    layouts.extend(extra)
                else:
                    sections_out.append(result)  # type: ignore[arg-type]

    return Snapshot(
        generated_at=datetime.now(),
        hostname=socket.gethostname(),
        platform=platform.platform(),
        sections=sections_out,
        warnings=warnings,
        layouts=layouts,
    )
