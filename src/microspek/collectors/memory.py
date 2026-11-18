"""Memory (RAM) collector."""

from __future__ import annotations

from ..models import Group, Item, Section
from ..util import first, format_bytes, format_percent, ps_json

SCRIPT = r"""
$ErrorActionPreference='SilentlyContinue'
$mods = Get-CimInstance Win32_PhysicalMemory | Sort-Object DeviceLocator
$arr = Get-CimInstance Win32_PhysicalMemoryArray | Select-Object -First 1
$os = Get-CimInstance Win32_OperatingSystem
$pf = Get-CimInstance Win32_PageFileUsage
[pscustomobject]@{
    total=$os.TotalVisibleMemorySize; free=$os.FreePhysicalMemory;
    virtual_total=$os.TotalVirtualMemorySize; virtual_free=$os.FreeVirtualMemory;
    slots=$arr.MemoryDevices;
    pagefile=@($pf | ForEach-Object { [pscustomobject]@{ name=$_.Name; size=$_.AllocatedBaseSize; used=$_.CurrentUsage; peak=$_.PeakUsage } })
    modules=@($mods | ForEach-Object {
        [pscustomobject]@{
            slot=$_.DeviceLocator; vendor=$_.Manufacturer; part=$_.PartNumber;
            serial=$_.SerialNumber; capacity=$_.Capacity; speed=$_.Speed;
            configured=$_.ConfiguredClockSpeed; form=$_.FormFactor;
            type=$_.SMBIOSMemoryType; rank=$_.Rank
        } })
} | ConvertTo-Json -Depth 4 -Compress
"""

FORM = {8: "DIMM", 12: "SODIMM", 13: "SRIMM", 23: "FB-DIMM"}
TYPES = {20: "DDR", 21: "DDR2", 22: "DDR2 FB-DIMM", 24: "DDR3", 26: "DDR4", 34: "DDR5"}


def _kb_to_bytes(value: object) -> object:
    try:
        return int(value) * 1024  # type: ignore[operator]
    except (TypeError, ValueError):
        return None


def collect_memory() -> Section:
    data = ps_json(SCRIPT) or {}
    modules = data.get("modules") or []
    total_bytes = _kb_to_bytes(data.get("total"))
    free_bytes = _kb_to_bytes(data.get("free"))
    groups: list[Group] = []
    summary: list[Item] = []
    summary.append(Item("Память всего", format_bytes(total_bytes)))
    if total_bytes and free_bytes:
        used = total_bytes - free_bytes
        summary.append(
            Item("Занято / свободно", f"{format_bytes(used)} / {format_bytes(free_bytes)} ({format_percent(used * 100 / total_bytes)})")
        )
    installed = sum(int(m.get("capacity") or 0) for m in modules)
    if installed:
        slots = data.get("slots")
        slot_note = f", занято слотов: {len(modules)} из {slots}" if slots else f", модулей: {len(modules)}"
        summary.append(Item("Модули", format_bytes(installed) + slot_note))
    groups.append(
        Group(
            "Объём",
            [
                Item("Установлено", format_bytes(installed if installed else total_bytes)),
                Item("Доступно ОС", format_bytes(total_bytes)),
                Item("Свободно", format_bytes(free_bytes)),
                Item("Слотов всего", first(data.get("slots"))),
                Item("Занято слотов", f"{len(modules)}"),
            ],
        )
    )
    if data.get("virtual_total"):
        groups.append(
            Group(
                "Виртуальная память",
                [
                    Item("Всего", format_bytes(_kb_to_bytes(data.get("virtual_total")))),
                    Item("Свободно", format_bytes(_kb_to_bytes(data.get("virtual_free")))),
                ],
            )
        )
    pagefile = data.get("pagefile") or []
    for entry in pagefile:
        groups.append(
            Group(
                f"Файл подкачки {entry.get('name', '')}",
                [
                    Item("Размер", format_bytes(int(entry.get("size") or 0) * 1024 * 1024)),
                    Item("Используется сейчас", format_bytes(int(entry.get("used") or 0) * 1024 * 1024)),
                    Item("Пик использования", format_bytes(int(entry.get("peak") or 0) * 1024 * 1024)),
                ],
            )
        )
    for index, module in enumerate(modules, start=1):
        memory_type = TYPES.get(module.get("type"), "—")
        try:
            spd = int(module.get("speed") or 0)
            configured = int(module.get("configured") or 0)
        except (TypeError, ValueError):
            spd = configured = 0
        profile = (
            "—" if not (spd and configured)
            else "XMP / разгон активен" if configured > spd
            else "JEDEC (без разгона)"
        )
        groups.append(
            Group(
                f"Модуль {index} — {module.get('slot', '?')}",
                [
                    Item("Слот", first(module.get("slot"))),
                    Item("Производитель", first(module.get("vendor"))),
                    Item("Part Number", first(module.get("part")), sensitive=True),
                    Item("Серийный номер", first(module.get("serial")), sensitive=True),
                    Item("Объём", format_bytes(module.get("capacity"))),
                    Item("Тип", memory_type),
                    Item("Частота ( SPD / работает )", f"{first(module.get('speed'))} / {first(module.get('configured'))} МТ/с"),
                    Item("Профиль памяти", profile),
                    Item("Форм-фактор", FORM.get(module.get("form"), "—")),
                    Item("Рангов", first(module.get("rank"))),
                ],
            )
        )
    return Section("memory", "Оперативная память", groups, summary)
