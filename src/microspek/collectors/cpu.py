"""CPU collector."""

from __future__ import annotations

from ..models import Group, Item, Section
from ..util import first, format_mhz, format_percent, format_temp, format_bytes, ps_json

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
    name = first(data.get("name"))
    summary.append(Item("Процессор", name))
    summary.append(Item("Ядра / потоки", f"{data.get('cores', '—')} / {data.get('threads', '—')}"))
    summary.append(Item("Частота", format_mhz(data.get("cur") or data.get("base"))))
    load = format_percent(data.get("load"))
    temp = format_temp((data.get("temp") or 0) / 10.0) if data.get("temp") else "—"
    if load != "—":
        state = f"{load}" + (f", {temp}" if temp != "—" else "")
        summary.append(Item("Загрузка сейчас", state))
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
            Item("Температура (термозона)", temp),
        ],
    )
    groups.append(main)
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
