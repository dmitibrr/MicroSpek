"""Physical disks, partitions, volumes, SMART and disk layouts."""

from __future__ import annotations

import re

from ..models import DiskLayout, Group, Item, PartitionSegment, Section
from ..util import first, format_bytes, format_duration, format_percent, format_temp, ps_json

SCRIPT = r"""
$ErrorActionPreference='SilentlyContinue'
$disks = @(Get-CimInstance Win32_DiskDrive | Select-Object DeviceID,Model,Manufacturer,SerialNumber,Size,MediaType,InterfaceType,FirmwareRevision,Partitions,Status)
$parts = @(Get-CimInstance Win32_DiskPartition | Select-Object DeviceID,DiskIndex,Size,Type,Bootable,PrimaryPartition,StartingOffset)
$logical = @(Get-CimInstance Win32_LogicalDisk | Select-Object DeviceID,VolumeName,Size,FreeSpace,FileSystem,DriveType,VolumeSerialNumber)
$maps = @(Get-CimInstance Win32_LogicalDiskToPartition | ForEach-Object {
    [pscustomobject]@{ letter=$_.Dependent.DeviceID; part=$_.Antecedent.DeviceID } })
$phys = @(Get-PhysicalDisk | Select-Object FriendlyName,SerialNumber,MediaType,HealthStatus,OperationalStatus,FirmwareVersion,Size,BusType)
$rel = @(Get-PhysicalDisk | ForEach-Object {
    $d = $_
    $c = Get-StorageReliabilityCounter -PhysicalDisk $d -ErrorAction SilentlyContinue
    if ($c) { [pscustomobject]@{
        name=$d.FriendlyName; serial=$d.SerialNumber; temp=$c.Temperature;
        tempmax=$c.TemperatureMax; hours=$c.PowerOnHours; wear=$c.Wear;
        readerr=$c.ReadErrorsTotal; writeerr=$c.WriteErrorsTotal } }
})
[pscustomobject]@{ disks=$disks; parts=$parts; logical=$logical;
    maps=$maps; phys=$phys; rel=$rel } | ConvertTo-Json -Depth 5 -Compress
"""

DRIVE_TYPES = {
    0: "Неизвестно", 1: "Нет корня", 2: "Съёмный", 3: "Локальный",
    4: "Сетевой", 5: "CD/DVD", 6: "RAM-диск",
}


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
    disks = data.get("disks") or []
    parts = data.get("parts") or []
    logical = data.get("logical") or []
    maps = data.get("maps") or []
    phys = data.get("phys") or []
    rel = data.get("rel") or []

    total_size = sum(_as_int(d.get("Size")) for d in disks)
    ssd = sum(1 for d in _unique_phys(phys) if str(d.get("MediaType")).lower() == "ssd")
    hdd = sum(1 for d in _unique_phys(phys) if str(d.get("MediaType")).lower() == "hdd")
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
        temperature = health.get("temp")
        disk_items.extend([
            Item(f"{title} — модель", first(disk.get("Model"))),
            Item(f"{title} — объём", format_bytes(disk.get("Size"))),
            Item(f"{title} — тип", first(extra.get("MediaType"), default=first(disk.get("MediaType")))),
            Item(f"{title} — шина / интерфейс", first(extra.get("BusType")) or first(disk.get("InterfaceType"))),
            Item(f"{title} — интерфейс (WMI)", first(disk.get("InterfaceType"))),
            Item(f"{title} — прошивка", first(disk.get("FirmwareRevision")) or first(extra.get("FirmwareVersion"))),
            Item(f"{title} — серийный номер", first(disk.get("SerialNumber")), sensitive=True),
            Item(f"{title} — состояние", first(extra.get("HealthStatus")) or first(disk.get("Status"))),
            Item(f"{title} — температура", format_temp(temperature) if temperature not in (None, "", 0) else "—"),
            Item(f"{title} — наработка", format_duration(_as_int(health.get("hours")) * 3600) if health.get("hours") else "—"),
            Item(f"{title} — износ", format_percent(health.get("wear")) if health.get("wear") not in (None, "") else "—"),
        ])

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
