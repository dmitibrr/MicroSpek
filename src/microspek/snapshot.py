"""Snapshot assembly: runs every collector and gathers warnings."""

from __future__ import annotations

import platform
import socket
from datetime import datetime

from .collectors import cpu, devices, dxdiag, gpu, memory, motherboard, network, os_info, storage
from .models import DiskLayout, Section, Snapshot


def collect_snapshot(include_dxdiag: bool = True, dxdiag_timeout: float = 60.0) -> Snapshot:
    """Collect all available information into a single Snapshot."""
    sections: list[Section] = []
    layouts: list[DiskLayout] = []
    warnings: list[str] = []

    def add(title: str, func, *args, **kwargs) -> None:
        try:
            result = func(*args, **kwargs)
            if isinstance(result, tuple):
                section, extra = result
                sections.append(section)
                layouts.extend(extra)
            else:
                sections.append(result)
        except Exception as exc:  # one broken collector must not kill the report
            warnings.append(f"{title}: {type(exc).__name__}: {exc}")

    add("ОС", os_info.collect_os)
    add("Материнская плата", motherboard.collect_motherboard)
    add("Процессор", cpu.collect_cpu)
    add("Память", memory.collect_memory)
    add("Диски", storage.collect_storage)
    add("Видеокарта", gpu.collect_gpu)
    add("Сеть", network.collect_network)
    add("Устройства", devices.collect_devices)
    if include_dxdiag:
        add("DirectX", dxdiag.collect_dxdiag, dxdiag_timeout)

    return Snapshot(
        generated_at=datetime.now(),
        hostname=socket.gethostname(),
        platform=platform.platform(),
        sections=sections,
        warnings=warnings,
        layouts=layouts,
    )
