"""Snapshot assembly: runs every collector and gathers warnings."""

from __future__ import annotations

import platform
import socket
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Callable

from .collectors import cpu, devices, dxdiag, gpu, memory, motherboard, network, os_info, storage
from .collectors import sensors as sensor_hub
from .models import DiskLayout, Section, Snapshot


def collect_snapshot(
    include_dxdiag: bool = True,
    dxdiag_timeout: float = 60.0,
    elevate_sensors: bool = False,
) -> Snapshot:
    """Collect all available information into a single Snapshot.

    Every collector starts its own PowerShell interpreter, so they used to run
    one after another and pay that startup cost nine times. They are independent,
    hence run concurrently: total time is the slowest section, not the sum.
    """
    sensor_hub.begin(elevate=elevate_sensors)

    jobs: list[tuple[str, Callable[[], object]]] = [
        ("ОС", os_info.collect_os),
        ("Материнская плата", motherboard.collect_motherboard),
        ("Процессор", cpu.collect_cpu),
        ("Память", memory.collect_memory),
        ("Диски", storage.collect_storage),
        ("Видеокарта", gpu.collect_gpu),
        ("Сеть", network.collect_network),
        ("Устройства", devices.collect_devices),
    ]
    if include_dxdiag:
        jobs.append(("DirectX", lambda: dxdiag.collect_dxdiag(dxdiag_timeout)))

    sections: list[Section] = []
    layouts: list[DiskLayout] = []
    warnings: list[str] = []

    with ThreadPoolExecutor(max_workers=min(8, len(jobs)), thread_name_prefix="microspek") as pool:
        futures = [(title, pool.submit(job)) for title, job in jobs]
        for title, future in futures:  # keep the section order stable
            try:
                result = future.result()
            except Exception as exc:  # one broken collector must not kill the report
                warnings.append(f"{title}: {type(exc).__name__}: {exc}")
                continue
            if isinstance(result, tuple):
                section, extra = result
                sections.append(section)
                layouts.extend(extra)
            else:
                sections.append(result)

    return Snapshot(
        generated_at=datetime.now(),
        hostname=socket.gethostname(),
        platform=platform.platform(),
        sections=sections,
        warnings=warnings,
        layouts=layouts,
    )
