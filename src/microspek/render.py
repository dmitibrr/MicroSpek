"""Rendering and export: TXT snapshot, JSON and Markdown.

All three formats share the same localized snapshot: the collectors always keep
Russian labels in memory, and ``lang`` decides what the report contains.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .i18n import get_language, localize_snapshot, s, t
from .models import Item, Snapshot, format_bytes, redact_snapshot

SEGMENT_COLORS = {
    "data": "#2f7dd1",
    "efi": "#e0a020",
    "recovery": "#9b6bc9",
    "service": "#7a8a99",
    "ldm": "#4ba88a",
    "free": "#d6dae0",
}


def _target(snapshot: Snapshot, redacted: bool, lang: str | None = None) -> Snapshot:
    snap = redact_snapshot(snapshot) if redacted else snapshot
    if lang is not None or get_language() != "ru":
        snap = localize_snapshot(snap, lang)
    return snap


def _item_text(item: Item, indent: str = "") -> str:
    line = f"{indent}{item.label}: {item.value}"
    if item.note:
        line += f"  ({item.note})"
    return line


# --------------------------------------------------------------------------- TXT

def render_txt(snapshot: Snapshot, redacted: bool = False, lang: str | None = None) -> str:
    snap = _target(snapshot, redacted, lang)
    lines: list[str] = []
    lines.append("=" * 76)
    lines.append(t("MicroSpek — слепок системы"))
    lines.append("=" * 76)
    lines.append(f"{t('Создан')}:    {snap.generated_at.strftime('%d.%m.%Y %H:%M:%S')}")
    lines.append(f"{t('Хост')}:      {snap.hostname}")
    lines.append(f"{t('Платформа')}: {snap.platform}")
    if redacted:
        lines.append(t("Чувствительные данные скрыты"))
    for section in snap.sections:
        lines.append("")
        lines.append("-" * 76)
        lines.append(f"## {section.title}")
        if section.summary:
            lines.append("")
            lines.append(f"[{t('Сводка')}]")
            lines.extend(_item_text(item, "  ") for item in section.summary)
        for group in section.groups:
            lines.append("")
            lines.append(f"[{group.title}]")
            lines.extend(_item_text(item, "  ") for item in group.items)
    if snap.layouts:
        lines.append("")
        lines.append("-" * 76)
        lines.append(f"## {t('Разметка дисков')}")
        for layout in snap.layouts:
            lines.append("")
            lines.append(layout.title)
            allocated = sum(seg.size for seg in layout.segments if seg.kind != "free")
            for seg in layout.segments:
                percent = seg.size * 100 / layout.total_size if layout.total_size else 0
                bar = "#" * max(1, round(percent / 2.5))
                line = (
                    f"  {seg.label:<24} {t(format_bytes(seg.size)):>12} "
                    f"{percent:5.1f}%  {bar}  [{seg.kind}]"
                )
                if seg.used is not None and seg.size:
                    used_percent = seg.used * 100 / seg.size
                    line += f"  {t('занято')} {t(format_bytes(seg.used))} ({used_percent:.0f}%)"
                lines.append(line)
            lines.append(
                f"  {t('ИТОГО'):<24} {t(format_bytes(allocated)):>12} {t('размечено')}"
            )
    if snap.warnings:
        lines.append("")
        lines.append(f"## {t('Предупреждения')}")
        lines.extend(f"  - {warning}" for warning in snap.warnings)
    lines.append("")
    return "\n".join(lines)


# -------------------------------------------------------------------------- JSON

def snapshot_to_dict(
    snapshot: Snapshot,
    redacted: bool = False,
    lang: str | None = None,
) -> dict:
    snap = _target(snapshot, redacted, lang)
    return {
        "schema": "microspek.snapshot/1",
        "language": get_language(),
        "generated_at": snap.generated_at.isoformat(timespec="seconds"),
        "hostname": snap.hostname,
        "platform": snap.platform,
        "warnings": list(snap.warnings),
        "sections": [
            {
                "key": section.key,
                "title": section.title,
                "summary": [
                    {"label": i.label, "value": i.value, "note": i.note, "sensitive": i.sensitive}
                    for i in section.summary
                ],
                "groups": [
                    {
                        "title": group.title,
                        "items": [
                            {"label": i.label, "value": i.value, "note": i.note, "sensitive": i.sensitive}
                            for i in group.items
                        ],
                    }
                    for group in section.groups
                ],
            }
            for section in snap.sections
        ],
        "layouts": [
            {
                "title": layout.title,
                "total_size": layout.total_size,
                "segments": [
                    {"label": seg.label, "size": seg.size, "kind": seg.kind, "used": seg.used}
                    for seg in layout.segments
                ],
            }
            for layout in snap.layouts
        ],
    }


def render_json(snapshot: Snapshot, redacted: bool = False, lang: str | None = None) -> str:
    return json.dumps(snapshot_to_dict(snapshot, redacted, lang), ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------- Markdown

def _md_cell(value: object) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\r", " ").replace("\n", "<br>")


def _md_items(items: list[Item]) -> list[str]:
    if not items:
        return []
    lines = [
        f"| {s('col_parameter')} | {s('col_value')} | {s('col_note')} |",
        "| --- | --- | --- |",
    ]
    for item in items:
        lines.append(
            f"| {_md_cell(item.label)} | {_md_cell(item.value)} | {_md_cell(item.note)} |"
        )
    return lines


def render_markdown(snapshot: Snapshot, redacted: bool = False, lang: str | None = None) -> str:
    """A clean Markdown snapshot for AI chats, Notion and Obsidian."""
    snap = _target(snapshot, redacted, lang)
    lines: list[str] = [f"# {t('MicroSpek — слепок системы')}", ""]
    lines.append("| | |")
    lines.append("| --- | --- |")
    lines.append(f"| {t('Создан')} | {snap.generated_at.strftime('%d.%m.%Y %H:%M:%S')} |")
    lines.append(f"| {t('Хост')} | {_md_cell(snap.hostname)} |")
    lines.append(f"| {t('Платформа')} | {_md_cell(snap.platform)} |")
    if redacted:
        lines.append(f"| | *{t('Чувствительные данные скрыты')}* |")
    lines.append("")

    for section in snap.sections:
        lines.append(f"## {section.title}")
        lines.append("")
        if section.summary:
            lines.append(f"### {t('Сводка')}")
            lines.append("")
            lines.extend(_md_items(section.summary))
            lines.append("")
        for group in section.groups:
            lines.append(f"### {group.title}")
            lines.append("")
            lines.extend(_md_items(group.items))
            lines.append("")

    if snap.layouts:
        lines.append(f"## {t('Разметка дисков')}")
        lines.append("")
        for layout in snap.layouts:
            lines.append(f"### {layout.title}")
            lines.append("")
            lines.append(
                f"| {s('md_segment')} | {s('md_size')} | {s('md_used')} | {s('md_kind')} |"
            )
            lines.append("| --- | ---: | ---: | --- |")
            for seg in layout.segments:
                used = ""
                if seg.used is not None and seg.size:
                    used = f"{t(format_bytes(seg.used))} ({seg.used * 100 / seg.size:.0f}%)"
                lines.append(
                    f"| {_md_cell(seg.label)} | {t(format_bytes(seg.size))} | {used} | {seg.kind} |"
                )
            lines.append("")

    if snap.warnings:
        lines.append(f"## {t('Предупреждения')}")
        lines.append("")
        lines.extend(f"- {_md_cell(warning)}" for warning in snap.warnings)
        lines.append("")

    return "\n".join(lines)


# ------------------------------------------------------------------------ saving

_FORMATS = {
    "txt": render_txt,
    "json": render_json,
    "md": render_markdown,
    "markdown": render_markdown,
}


def render(snapshot: Snapshot, fmt: str, redacted: bool = False, lang: str | None = None) -> str:
    fmt = fmt.lower().lstrip(".")
    try:
        renderer = _FORMATS[fmt]
    except KeyError:
        raise ValueError(f"unsupported format: {fmt}") from None
    return renderer(snapshot, redacted, lang)


def save_snapshot(
    snapshot: Snapshot,
    path: str | Path,
    fmt: str = "txt",
    redacted: bool = False,
    lang: str | None = None,
) -> Path:
    """Save a snapshot to ``path`` in the requested format."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(snapshot, fmt, redacted, lang), encoding="utf-8")
    return target


def default_name(fmt: str, stamp: datetime | None = None) -> str:
    stamp = stamp or datetime.now()
    fmt = fmt.lower().lstrip(".")
    return f"microspek_snapshot_{stamp.strftime('%Y%m%d_%H%M%S')}.{fmt}"
