"""Rendering and export: TXT snapshot, JSON and PNG report."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .models import Item, Snapshot, format_bytes, redact_snapshot

SEGMENT_COLORS = {
    "data": "#2f7dd1",
    "efi": "#e0a020",
    "recovery": "#9b6bc9",
    "service": "#7a8a99",
    "ldm": "#4ba88a",
    "free": "#d6dae0",
}
SEGMENT_LABELS = {
    "data": "данные",
    "efi": "EFI",
    "recovery": "восстановление",
    "service": "служебный",
    "ldm": "LDM",
    "free": "не размечено",
}


def _target(snapshot: Snapshot, redacted: bool) -> Snapshot:
    return redact_snapshot(snapshot) if redacted else snapshot


def _item_text(item: Item, indent: str = "") -> str:
    line = f"{indent}{item.label}: {item.value}"
    if item.note:
        line += f"  ({item.note})"
    return line


# --------------------------------------------------------------------------- TXT

def render_txt(snapshot: Snapshot, redacted: bool = False) -> str:
    snap = _target(snapshot, redacted)
    lines: list[str] = []
    lines.append("=" * 76)
    lines.append("MicroSpek — слепок системы")
    lines.append("=" * 76)
    lines.append(f"Создан:    {snap.generated_at.strftime('%d.%m.%Y %H:%M:%S')}")
    lines.append(f"Хост:      {snap.hostname}")
    lines.append(f"Платформа: {snap.platform}")
    if redacted:
        lines.append("Чувствительные данные скрыты")
    for section in snap.sections:
        lines.append("")
        lines.append("-" * 76)
        lines.append(f"## {section.title}")
        if section.summary:
            lines.append("")
            lines.append("[Сводка]")
            lines.extend(_item_text(item, "  ") for item in section.summary)
        for group in section.groups:
            lines.append("")
            lines.append(f"[{group.title}]")
            lines.extend(_item_text(item, "  ") for item in group.items)
    if snap.layouts:
        lines.append("")
        lines.append("-" * 76)
        lines.append("## Разметка дисков")
        for layout in snap.layouts:
            lines.append("")
            lines.append(layout.title)
            allocated = sum(seg.size for seg in layout.segments if seg.kind != "free")
            for seg in layout.segments:
                percent = seg.size * 100 / layout.total_size if layout.total_size else 0
                bar = "#" * max(1, round(percent / 2.5))
                line = (
                    f"  {seg.label:<24} {format_bytes(seg.size):>12} "
                    f"{percent:5.1f}%  {bar}  [{seg.kind}]"
                )
                if seg.used is not None and seg.size:
                    used_percent = seg.used * 100 / seg.size
                    line += f"  занято {format_bytes(seg.used)} ({used_percent:.0f}%)"
                lines.append(line)
            lines.append(f"  {'ИТОГО':<24} {format_bytes(allocated):>12} размечено")
    if snap.warnings:
        lines.append("")
        lines.append("## Предупреждения")
        lines.extend(f"  - {warning}" for warning in snap.warnings)
    lines.append("")
    return "\n".join(lines)


# -------------------------------------------------------------------------- JSON

def snapshot_to_dict(snapshot: Snapshot, redacted: bool = False) -> dict:
    snap = _target(snapshot, redacted)
    return {
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


def render_json(snapshot: Snapshot, redacted: bool = False) -> str:
    return json.dumps(snapshot_to_dict(snapshot, redacted), ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------- PNG

def _font(size: int, bold: bool = False):
    from PIL import ImageFont

    candidates = (
        ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/consolab.ttf"]
        if bold
        else ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/consola.ttf"]
    )
    candidates.append("DejaVuSans.ttf")
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap(text: str, font, max_width: int) -> list[str]:
    words = str(text).split()
    if not words:
        return [""]
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if font.getlength(trial) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def render_png(snapshot: Snapshot, path: str | Path | None = None, redacted: bool = False) -> Path:
    """Render a PNG report with a visual disk-layout bar for each disk."""
    from PIL import Image, ImageDraw

    snap = _target(snapshot, redacted)
    width = 1120
    pad = 28
    content_width = width - 2 * pad
    font = _font(15)
    font_bold = _font(19, bold=True)
    font_section = _font(17, bold=True)
    font_small = _font(13)
    line_height = 22

    ops: list[dict] = []

    def text(value: str, f=font, color: str = "#1f2733", indent: int = 0, gap: int = 0) -> None:
        ops.append({"kind": "text", "value": value, "font": f, "color": color, "indent": indent, "gap": gap})

    def bar(layout) -> None:
        ops.append({"kind": "bar", "layout": layout})

    text("MicroSpek — слепок системы", font_bold, "#12395e", gap=4)
    text(f"Создан: {snap.generated_at.strftime('%d.%m.%Y %H:%M:%S')}    Хост: {snap.hostname}", font_small, "#546274")
    text(f"Платформа: {snap.platform}", font_small, "#546274", gap=10)
    if redacted:
        text("Чувствительные данные скрыты", font_small, "#a05020", gap=8)

    for section in snap.sections:
        text(section.title, font_section, "#12395e", gap=6)
        if section.summary:
            for item in section.summary:
                text(_item_text(item).replace(": ", ":  ", 1), font, "#22405e", indent=12)
        for group in section.groups:
            text(group.title, font_small, "#66778b", indent=12, gap=2)
            for item in group.items:
                text(_item_text(item, "  "), font_small, "#2b3440", indent=24)
        ops.append({"kind": "space", "gap": 12})

    if snap.layouts:
        text("Разметка дисков", font_section, "#12395e", gap=6)
        for layout in snap.layouts:
            bar(layout)
            ops.append({"kind": "space", "gap": 8})

    if snap.warnings:
        text("Предупреждения", font_section, "#a05020", gap=4)
        for warning in snap.warnings:
            text(f"- {warning}", font_small, "#a05020", indent=12)

    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    height = pad
    for op in ops:
        if op["kind"] == "text":
            for line in _wrap(op["value"], op["font"], content_width - op["indent"]):
                height += line_height
            height += op.get("gap", 0)
        elif op["kind"] == "bar":
            height += 30 + 26 + 20 + 8 * max(1, len(op["layout"].segments) // 3)
        else:
            height += op.get("gap", 0)
    height += pad

    image = Image.new("RGB", (width, height), "#f4f6f9")
    draw = ImageDraw.Draw(image)
    y = pad

    for op in ops:
        kind = op["kind"]
        if kind == "space":
            y += op.get("gap", 0)
            continue
        if kind == "text":
            for line in _wrap(op["value"], op["font"], content_width - op["indent"]):
                draw.text((pad + op["indent"], y), line, font=op["font"], fill=op["color"])
                y += line_height
            y += op.get("gap", 0)
            continue
        if kind == "bar":
            layout = op["layout"]
            draw.text((pad, y), layout.title, font=font, fill="#12395e")
            y += 30
            bar_y = y
            bar_h = 24
            total = layout.total_size or 1
            x = pad
            for seg in layout.segments:
                seg_w = max(2, round(content_width * seg.size / total))
                color = SEGMENT_COLORS.get(seg.kind, "#7a8a99")
                draw.rectangle([x, bar_y, x + seg_w, bar_y + bar_h], fill=color, outline="#ffffff")
                if seg_w > 58:
                    draw.text((x + 4, bar_y + 4), seg.label[:14], font=font_small, fill="#ffffff")
                x += seg_w
            draw.rectangle([pad, bar_y, pad + content_width, bar_y + bar_h], outline="#9aa7b5")
            y += bar_h + 8
            legend = "   ".join(
                f"{SEGMENT_LABELS.get(seg.kind, seg.kind)}: {seg.label} — {format_bytes(seg.size)}"
                + (f" (занято {format_bytes(seg.used)})" if seg.used is not None else "")
                for seg in layout.segments
            )
            for line in _wrap(legend, font_small, content_width):
                draw.text((pad, y), line, font=font_small, fill="#546274")
                y += 18
            y += 8

    if path is None:
        path = Path(f"microspek_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target)
    return target


def save_snapshot(
    snapshot: Snapshot,
    path: str | Path,
    fmt: str = "txt",
    redacted: bool = False,
) -> Path:
    """Save a snapshot to ``path`` in the requested format."""
    fmt = fmt.lower().lstrip(".")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "txt":
        target.write_text(render_txt(snapshot, redacted), encoding="utf-8")
    elif fmt == "json":
        target.write_text(render_json(snapshot, redacted), encoding="utf-8")
    elif fmt == "png":
        render_png(snapshot, target, redacted)
    else:
        raise ValueError(f"Неизвестный формат: {fmt}")
    return target
