"""Data models and formatting helpers for MicroSpek."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable


NA = "не удалось определить"


def clean(value: Any, default: str = NA) -> str:
    """Convert a value to a compact, human-readable string."""
    if value is None:
        return default
    if isinstance(value, bool):
        return "да" if value else "нет"
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.2f}".rstrip("0").rstrip(".")
    if isinstance(value, (list, tuple, set)):
        values = [clean(item, "") for item in value]
        values = [item for item in values if item]
        return ", ".join(values) if values else default
    text = str(value).strip()
    if not text:
        return default
    return " ".join(text.split())


def first(*values: Any, default: str = NA) -> str:
    """Return the first non-empty value."""
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return clean(value, default)
    return default


def format_bytes(value: Any, decimal: bool = False) -> str:
    """Format a byte count using binary units (GiB/TiB)."""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return NA
    if amount < 0:
        return NA
    units = ("Б", "КиБ", "МиБ", "ГиБ", "ТиБ", "ПиБ")
    unit = units[0]
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            break
        amount /= 1024
    if unit == "Б":
        return f"{int(amount)} {unit}"
    precision = 2 if decimal else (1 if amount >= 100 else 2)
    return f"{amount:.{precision}f} {unit}".replace(".", ",")


def format_mhz(value: Any) -> str:
    try:
        mhz = float(value)
    except (TypeError, ValueError):
        return NA
    if mhz >= 1000:
        return f"{mhz / 1000:.2f} ГГц".replace(".", ",")
    return f"{mhz:.0f} МГц"


def format_temp(value: Any) -> str:
    try:
        temperature = float(value)
    except (TypeError, ValueError):
        return NA
    return f"{temperature:.0f} °C"


def format_percent(value: Any) -> str:
    try:
        percent = float(value)
    except (TypeError, ValueError):
        return NA
    return f"{percent:.0f}%"


def format_duration(seconds: Any) -> str:
    try:
        total = max(0, int(float(seconds)))
    except (TypeError, ValueError):
        return NA
    days, total = divmod(total, 86400)
    hours, total = divmod(total, 3600)
    minutes, seconds = divmod(total, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days} д")
    if hours or days:
        parts.append(f"{hours} ч")
    parts.append(f"{minutes} мин")
    return " ".join(parts)


@dataclass(slots=True)
class Item:
    """A single named value shown in a section."""

    label: str
    value: str
    note: str = ""
    sensitive: bool = False


@dataclass(slots=True)
class Group:
    """A named collection of related items."""

    title: str
    items: list[Item] = field(default_factory=list)


@dataclass(slots=True)
class Section:
    """A report section rendered identically in GUI, TXT and PNG outputs."""

    key: str
    title: str
    groups: list[Group] = field(default_factory=list)
    summary: list[Item] = field(default_factory=list)


@dataclass(slots=True)
class PartitionSegment:
    """A simplified partition segment used by the storage visual."""

    label: str
    size: int
    kind: str = "data"
    used: int | None = None  # занятое место внутри файловой системы, если известно


@dataclass(slots=True)
class DiskLayout:
    """Visual layout of one physical disk."""

    title: str
    total_size: int
    segments: list[PartitionSegment] = field(default_factory=list)


@dataclass(slots=True)
class Snapshot:
    """Complete point-in-time description of a computer."""

    generated_at: datetime
    hostname: str
    platform: str
    sections: list[Section] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    layouts: list[DiskLayout] = field(default_factory=list)

    def section(self, key: str) -> Section | None:
        return next((section for section in self.sections if section.key == key), None)

    def iter_items(self) -> Iterable[tuple[Section, Group, Item]]:
        for section in self.sections:
            for group in section.groups:
                for item in group.items:
                    yield section, group, item


def redact_snapshot(snapshot: Snapshot) -> Snapshot:
    """Return a copy with sensitive values hidden."""
    sections: list[Section] = []
    for section in snapshot.sections:
        groups: list[Group] = []
        for group in section.groups:
            items: list[Item] = []
            for item in group.items:
                if item.sensitive:
                    item = Item(item.label, "скрыто", item.note, item.sensitive)
                items.append(item)
            groups.append(Group(group.title, items))
        summary = [
            Item(item.label, "скрыто", item.note, item.sensitive)
            if item.sensitive
            else item
            for item in section.summary
        ]
        sections.append(Section(section.key, section.title, groups, summary))
    return Snapshot(
        generated_at=snapshot.generated_at,
        hostname=snapshot.hostname,
        platform=snapshot.platform,
        sections=sections,
        warnings=list(snapshot.warnings),
        layouts=list(snapshot.layouts),
    )
