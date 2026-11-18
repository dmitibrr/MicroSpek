"""CPU collector."""

from __future__ import annotations

from ..models import Group, Item, Section
from ..util import (
    first,
    format_bytes,
    format_fan,
    format_mhz,
    format_percent,
    format_temp,
    format_watts,
    ps_json,
)
from . import sensors as sensor_hub

SCRIPT = r"""
$ErrorActionPreference='SilentlyContinue'
$c = Get-CimInstance Win32_Processor | Select-Object -First 1
$perf = Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor
$total = ($perf | Where-Object { $_.Name -eq '_Total' }).PercentProcessorTime
$cores = @($perf | Where-Object { $_.Name -ne '_Total' } | ForEach-Object {
    [pscustomobject]@{ name=$_.Name; load=$_.PercentProcessorTime } })
$temp = (Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature |
    Select-Object -First 1).CurrentTemperature
[pscustomobject]@{
    name=$c.Name; vendor=$c.Manufacturer; desc=$c.Description;
    cores=$c.NumberOfCores; threads=$c.NumberOfLogicalProcessors;
    base=$c.MaxClockSpeed; cur=$c.CurrentClockSpeed;
    l2=$c.L2CacheSize; l3=$c.L3CacheSize; socket=$c.SocketDesignation;
    arch=$c.Architecture; width=$c.AddressWidth;
    virt=$c.VirtualizationFirmwareEnabled; voltage=$c.CurrentVoltage;
    family=$c.Caption; load=$total; temp=$temp; core_load=$cores
} | ConvertTo-Json -Depth 4 -Compress
"""

ARCH = {0: "x86", 5: "ARM", 6: "Itanium", 9: "x64", 12: "ARM64"}


def _kb_to_bytes(raw: object) -> object:
    """WMI reports L2/L3 cache sizes in kilobytes; 0 means 'not reported'."""
    try:
        value = int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    return value * 1024


def _voltage(raw: object) -> str:
    try:
        value = int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "—"
    if value <= 0:
        return "—"
    if value & 0x80:
        return f"{(value & 0x7F) / 10:.1f} В".replace(".", ",")
    return f"индекс {value}"


def collect_cpu() -> Section:
    data = ps_json(SCRIPT) or {}
    cores = data.get("core_load") or []
    groups: list[Group] = []
    summary: list[Item] = []

    hub = sensor_hub.data()
    sensor_cpu = hub.cpu() if hub else None
    temperatures = [
        (sensor_hub.ru_name(reading.name), reading.value)
        for reading in (sensor_cpu.readings("Temperature") if sensor_cpu else [])
    ]
    package = next((value for name, value in temperatures if name == "Пакет CPU"), None)
    if package is None and temperatures:
        package = max(value for _name, value in temperatures)

    name = first(data.get("name"))
    summary.append(Item("Процессор", name))
    summary.append(Item("Ядра / потоки", f"{data.get('cores', '—')} / {data.get('threads', '—')}"))
    summary.append(Item("Частота", format_mhz(data.get("cur") or data.get("base"))))
    load = format_percent(data.get("load"))
    acpi_temp = format_temp((data.get("temp") or 0) / 10.0) if data.get("temp") else "—"
    temp = format_temp(package) if package is not None else acpi_temp
    if load != "—":
        state = f"{load}" + (f", {temp}" if temp != "—" else "")
        summary.append(Item("Загрузка сейчас", state))
    if package is not None:
        summary.append(Item("Температура", temp))
    main = Group(
        "Основное",
        [
            Item("Модель", name),
            Item("Производитель", first(data.get("vendor"))),
            Item("Идентификатор", first(data.get("desc"))),
            Item("Физических ядер", first(data.get("cores"))),
            Item("Логических потоков", first(data.get("threads"))),
            Item("Базовая частота", format_mhz(data.get("base"))),
            Item("Текущая частота", format_mhz(data.get("cur"))),
            Item("Сокет", first(data.get("socket"))),
            Item("Архитектура", ARCH.get(data.get("arch"), first(data.get("arch")))),
            Item("Разрядность", first(data.get("width"), default="—") + " бит"),
            Item("Напряжение", _voltage(data.get("voltage"))),
            Item("Аппаратная виртуализация", first(data.get("virt"), default="—")),
            Item("Загрузка сейчас", format_percent(data.get("load"))),
            Item("Температура (термозона ACPI)", acpi_temp),
        ],
    )
    groups.append(main)
    sensor_items: list[Item] = [
        Item(label, format_temp(value)) for label, value in temperatures
    ]
    if sensor_cpu:
        for reading in sensor_cpu.readings("Fan"):
            sensor_items.append(Item(sensor_hub.ru_name(reading.name), format_fan(reading.value)))
        for reading in sensor_cpu.readings("Power"):
            if reading.value > 0:
                sensor_items.append(Item(sensor_hub.ru_name(reading.name), format_watts(reading.value)))
    if sensor_items:
        groups.append(Group("Датчики (LibreHardwareMonitor)", sensor_items))
    groups.append(
        Group(
            "Кэш",
            [
                Item("Кэш L2", format_bytes(_kb_to_bytes(data.get("l2")))),
                Item("Кэш L3", format_bytes(_kb_to_bytes(data.get("l3")))),
            ],
        )
    )
    if cores:
        core_items = [
            Item(
                str(core.get("name", "?")),
                format_percent(core.get("load")),
            )
            for core in cores
        ]
        groups.append(Group("Загрузка по ядрам", core_items))
    return Section("cpu", "Процессор", groups, summary)
