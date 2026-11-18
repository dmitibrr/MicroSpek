"""Physical disks, partitions, volumes, SMART and disk layouts."""

from __future__ import annotations

import re

from ..models import DiskLayout, Group, Item, PartitionSegment, Section
from ..util import first, format_bytes, format_duration, format_percent, format_temp, ps_json
from . import sensors as sensor_hub

SCRIPT = r"""
$ErrorActionPreference='SilentlyContinue'
$disks = @(Get-CimInstance Win32_DiskDrive | Select-Object DeviceID,Model,Manufacturer,SerialNumber,Size,MediaType,InterfaceType,FirmwareRevision,Partitions,Status)
$parts = @(Get-CimInstance Win32_DiskPartition | Select-Object DeviceID,DiskIndex,Size,Type,Bootable,PrimaryPartition,StartingOffset)
$logical = @(Get-CimInstance Win32_LogicalDisk | Select-Object DeviceID,VolumeName,Size,FreeSpace,FileSystem,DriveType,VolumeSerialNumber)
$maps = @(Get-CimInstance Win32_LogicalDiskToPartition | ForEach-Object {
    [pscustomobject]@{ letter=$_.Dependent.DeviceID; part=$_.Antecedent.DeviceID } })
$phys = @(Get-CimInstance -Namespace root/Microsoft/Windows/Storage -ClassName MSFT_PhysicalDisk |
    Select-Object FriendlyName,SerialNumber,FirmwareVersion,Size,BusType,MediaType,HealthStatus,OperationalStatus)
# Get-PhysicalDisk/Get-StorageReliabilityCounter import the Storage module (~1.5 s)
# and return no counters on most consumer drives; LibreHardwareMonitor covers SMART.
$rel = @()
[pscustomobject]@{ disks=$disks; parts=$parts; logical=$logical;
    maps=$maps; phys=$phys; rel=$rel } | ConvertTo-Json -Depth 5 -Compress
"""

DRIVE_TYPES = {
    0: "Неизвестно", 1: "Нет корня", 2: "Съёмный", 3: "Локальный",
    4: "Сетевой", 5: "CD/DVD", 6: "RAM-диск",
}

# MSFT_PhysicalDisk enum values (root/Microsoft/Windows/Storage).
MEDIA_TYPES = {0: "не указан", 3: "HDD", 4: "SSD", 5: "SCM"}
BUS_TYPES = {
    0: "Unknown", 1: "SCSI", 2: "ATAPI", 3: "ATA", 4: "IEEE 1394",
    5: "SSA", 6: "Fibre Channel", 7: "USB", 8: "RAID", 9: "iSCSI",
    10: "SAS", 11: "SATA", 12: "SD", 13: "MMC", 14: "Virtual",
    15: "File-backed Virtual", 16: "Storage Spaces", 17: "NVMe", 18: "SCM",
}
HEALTH_STATUS = {0: "исправен", 1: "предупреждение", 2: "неисправен", 5: "неизвестно"}


def _enum_text(value: object, table: dict[int, str], default: str = "—") -> str:
    if value is None or value == "":
        return default
    text = str(value).strip()
    if text.isdigit():
        return table.get(int(text), text)
    return text


def _as_int(value: object) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _serial(value: object) -> str:
    return re.sub(r"\s+", "", str(value or "")).upper()


def _disk_index(device_id: object) -> int | None:
    match = re.search(r"PHYSICALDRIVE(\d+)", str(device_id or ""), re.IGNORECASE)
    return int(match.group(1)) if match else None


def _partition_number(device_id: object) -> int:
    match = re.search(r"Partition\s*#(\d+)", str(device_id or ""), re.IGNORECASE)
    return int(match.group(1)) if match else 0


def _extra_for(disk: dict, rows: list[dict]) -> dict:
    serial = _serial(disk.get("SerialNumber"))
    model = str(disk.get("Model") or "").strip().lower()
    for row in rows:
        if serial and _serial(row.get("serial")) == serial:
            return row
    for row in rows:
        name = str(row.get("name") or row.get("FriendlyName") or "").strip().lower()
        if model and (name == model or name in model or model in name):
            return row
    return {}


def _volume_used(letters: str, volumes: dict[str, dict]) -> int | None:
    """Used bytes inside the volumes carried by a partition (if known)."""
    total = 0
    found = False
    for letter in (part.strip().upper() for part in letters.split(",")):
        volume = volumes.get(letter)
        if not volume:
            continue
        size = _as_int(volume.get("Size"))
        free = _as_int(volume.get("FreeSpace"))
        if size:
            total += max(0, size - free)
            found = True
    return total if found else None


def _kind(part: dict, letters: str) -> str:
    type_name = str(part.get("Type") or "").strip().lower()
    # Не используем подстроку "system": тип "Installable File System" — это
    # обычные данные, а не EFI (такой баг проявился на Lenovo ThinkCentre M79).
    if type_name in ("gpt: system", "system", "efi system partition") or "efi system" in type_name:
        return "efi"
    if "recovery" in type_name:
        return "recovery"
    if "logical disk manager" in type_name:
        return "ldm"
    if not letters and _as_int(part.get("Size")) < 2 * 1024**3:
        return "service"
    return "data"


def _letter_for(part_id: str, maps: list[dict]) -> str:
    target = part_id.strip().lower()
    letters = [
        str(m.get("letter") or "").strip()
        for m in maps
        if str(m.get("part") or "").strip().lower() == target
    ]
    letters = [letter for letter in letters if letter]
    return ", ".join(sorted(set(letters)))


def collect_storage() -> tuple[Section, list[DiskLayout]]:
    data = ps_json(SCRIPT) or {}
    hub = sensor_hub.data()
    disks = data.get("disks") or []
    parts = data.get("parts") or []
    logical = data.get("logical") or []
    maps = data.get("maps") or []
    phys = data.get("phys") or []
    rel = data.get("rel") or []

    total_size = sum(_as_int(d.get("Size")) for d in disks)
    ssd = sum(
        1 for d in _unique_phys(phys)
        if _enum_text(d.get("MediaType"), MEDIA_TYPES, "").lower() == "ssd"
    )
    hdd = sum(
        1 for d in _unique_phys(phys)
        if _enum_text(d.get("MediaType"), MEDIA_TYPES, "").lower() == "hdd"
    )
    summary = [
        Item("Физические диски", f"{len(disks)} шт., {format_bytes(total_size)}"),
        Item("Типы", f"SSD: {ssd}, HDD: {hdd}"),
        Item("Логические диски", ", ".join(str(d.get("DeviceID")) for d in logical) or "—"),
    ]

    disk_items: list[Item] = []
    for disk in disks:
        index = _disk_index(disk.get("DeviceID"))
        title = f"Диск {index if index is not None else '?'}: {first(disk.get('Model'))}"
        extra = _extra_for(disk, phys)
        health = _extra_for(disk, rel)
        smart = hub.storage(disk.get("Model") or "") if hub else None
        smart_temp = smart.find_reading("Temperature") if smart else None
        remaining = smart.find_reading("Remaining Life") if smart else None
        smart_hours = smart.find_reading("Power On Hours") if smart else None
        temperature = health.get("temp")
        if smart_temp is not None and smart_temp.value > 0:
            temperature = smart_temp.value
        hours = _as_int(health.get("hours"))
        if not hours and smart_hours is not None and smart_hours.value > 0:
            hours = int(smart_hours.value)
        disk_items.extend([
            Item(f"{title} — модель", first(disk.get("Model"))),
            Item(f"{title} — объём", format_bytes(disk.get("Size"))),
            Item(f"{title} — тип",
                 _enum_text(extra.get("MediaType"), MEDIA_TYPES, "") or first(disk.get("MediaType"))),
            Item(f"{title} — шина / интерфейс",
                 _enum_text(extra.get("BusType"), BUS_TYPES, "") or first(disk.get("InterfaceType"))),
            Item(f"{title} — интерфейс (WMI)", first(disk.get("InterfaceType"))),
            Item(f"{title} — прошивка", first(disk.get("FirmwareRevision")) or first(extra.get("FirmwareVersion"))),
            Item(f"{title} — серийный номер", first(disk.get("SerialNumber")), sensitive=True),
            Item(f"{title} — состояние",
                 _enum_text(extra.get("HealthStatus"), HEALTH_STATUS, "") or first(disk.get("Status"))),
            Item(f"{title} — температура", format_temp(temperature) if temperature not in (None, "", 0) else "—"),
            Item(f"{title} — наработка", format_duration(hours * 3600) if hours else "—"),
            Item(f"{title} — износ", format_percent(health.get("wear")) if health.get("wear") not in (None, "") else "—"),
        ])
        if remaining is not None:
            disk_items.append(Item(f"{title} — остаток ресурса", format_percent(remaining.value)))

    logical_items: list[Item] = []
    for volume in logical:
        size = _as_int(volume.get("Size"))
        free = _as_int(volume.get("FreeSpace"))
        used = size - free if size and free is not None else 0
        name = first(volume.get("VolumeName"), default="") or ""
        label = f"{volume.get('DeviceID')} ({name})" if name else str(volume.get("DeviceID"))
        logical_items.extend([
            Item(f"{label} — файловая система", first(volume.get("FileSystem"))),
            Item(f"{label} — тип", DRIVE_TYPES.get(_as_int(volume.get("DriveType"))), ),
            Item(f"{label} — объём", format_bytes(size)),
            Item(f"{label} — свободно", f"{format_bytes(free)} из {format_bytes(size)}"
                 if free is not None else "—"),
            Item(f"{label} — занято", f"{format_bytes(used)} ({format_percent(used * 100 / size)})" if size else "—"),
            Item(f"{label} — серийный номер тома", first(volume.get("VolumeSerialNumber")), sensitive=True),
        ])

    volumes_by_letter = {
        str(volume.get("DeviceID") or "").strip().upper(): volume
        for volume in logical
    }
    partition_items: list[Item] = []
    layouts: list[DiskLayout] = []
    for disk in disks:
        disk_index = _disk_index(disk.get("DeviceID"))
        disk_parts = sorted(
            [p for p in parts if _as_int(p.get("DiskIndex")) == disk_index],
            key=lambda p: _as_int(p.get("StartingOffset")),
        )
        segments: list[PartitionSegment] = []
        cursor = 0
        total = _as_int(disk.get("Size"))
        for part in disk_parts:
            start = _as_int(part.get("StartingOffset"))
            size = _as_int(part.get("Size"))
            if start > cursor:
                segments.append(PartitionSegment("не размечено", start - cursor, "free"))
            letters = _letter_for(str(part.get("DeviceID") or ""), maps)
            label = letters or str(part.get("Type") or "").split(":")[-1].strip() or f"#{_partition_number(part.get('DeviceID'))}"
            used = _volume_used(letters, volumes_by_letter)
            segments.append(PartitionSegment(label, size, _kind(part, letters), used))
            cursor = start + size
            partition_items.extend([
                Item(
                    f"Диск {disk_index} / раздел {_partition_number(part.get('DeviceID'))}",
                    f"{first(part.get('Type'))}, {format_bytes(size)}"
                    + (f", буквы: {letters}" if letters else ""),
                ),
            ])
        if total > cursor:
            segments.append(PartitionSegment("не размечено", total - cursor, "free"))
        layouts.append(
            DiskLayout(
                title=f"Диск {disk_index} — {first(disk.get('Model'))} ({format_bytes(total)})",
                total_size=total,
                segments=segments,
            )
        )

    # Занятое место внутри тома имеет смысл показывать только тогда, когда
    # том целиком лежит на одном сегменте. Иначе число дублируется на каждом
    # диске динамического массива и выглядит неверным.
    letter_counts: dict[str, int] = {}
    for layout in layouts:
        for segment in layout.segments:
            for letter in segment.label.split(","):
                letter = letter.strip().upper()
                if letter.endswith(":"):
                    letter_counts[letter] = letter_counts.get(letter, 0) + 1
    for layout in layouts:
        for segment in layout.segments:
            if segment.used is None:
                continue
            letters = [
                part.strip().upper()
                for part in segment.label.split(",")
                if part.strip().upper().endswith(":")
            ]
            if any(letter_counts.get(letter, 0) > 1 for letter in letters):
                segment.used = None

    groups = [
        Group("Физические диски", disk_items),
        Group("Логические диски", logical_items),
        Group("Разделы", partition_items),
    ]
    return Section("storage", "Диски", groups, summary), layouts


def _unique_phys(rows: list[dict]) -> list[dict]:
    seen: set[str] = set()
    result: list[dict] = []
    for row in rows:
        serial = _serial(row.get("SerialNumber"))
        key = serial or str(row.get("FriendlyName") or "")
        if key and key not in seen:
            seen.add(key)
            result.append(row)
    return result
